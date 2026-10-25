#!/usr/bin/env python3
"""Resync explicit local installs from a committed Skills revision."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

REPO = Path(__file__).resolve().parent.parent
BEGIN = '<!-- skills-sync:begin -->'
END = '<!-- skills-sync:end -->'


def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args])


def identity(path):
    if path.is_symlink():
        return ('link', os.readlink(path))
    if path.is_dir():
        return [(str(p.relative_to(path)), identity(p)) for p in sorted(path.rglob('*'))]
    if path.is_file():
        return (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode & 0o777)
    return None


def instructions(existing, source):
    if existing.count(BEGIN) != existing.count(END) or existing.count(BEGIN) > 1:
        raise ValueError('Malformed or repeated skills-sync instruction markers')
    block = BEGIN + '\n' + source.rstrip() + '\n' + END
    if BEGIN in existing:
        start, stop = existing.index(BEGIN), existing.index(END)
        if stop < start:
            raise ValueError('Reversed skills-sync instruction markers')
        return existing[:start] + block + existing[stop + len(END):]
    return existing.rstrip() + ('\n\n' if existing.strip() else '') + block + '\n'


def settings(existing, example, snapshot):
    result = json.loads(json.dumps(existing))
    result.setdefault('env', {})['SKILLS_DIR'] = str(snapshot)
    hooks = result.setdefault('hooks', {})
    for event, groups in example['hooks'].items():
        current = hooks.setdefault(event, [])
        for group in groups:
            if group not in current:
                current.append(group)
    return result


def apply(changes, backup_root):
    backup = Path(tempfile.mkdtemp(prefix='sync-', dir=backup_root))
    done = []
    try:
        for index, (source, target) in enumerate(changes):
            target.parent.mkdir(parents=True, exist_ok=True)
            saved = backup / str(index)
            existed = target.exists() or target.is_symlink()
            if existed:
                shutil.move(str(target), saved)
            done.append((target, saved, existed))
            if source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)
            if identity(source) != identity(target):
                raise RuntimeError(f'Readback failed: {target}')
        (backup / 'receipt.json').write_text(json.dumps([
            {'target': str(t), 'backup': str(s) if existed else None}
            for t, s, existed in done
        ], indent=2) + '\n')
    except BaseException:
        for target, saved, existed in reversed(done):
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            elif target.exists() or target.is_symlink():
                target.unlink()
            if existed:
                shutil.move(str(saved), target)
        raise
    return backup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD', help='Committed revision; uncommitted edits are never installed')
    parser.add_argument('--target', type=Path, action='append', default=[], help='Existing skill root; update only catalog packages already installed here (repeatable)')
    parser.add_argument('--claude-settings', type=Path, help='Merge hooks into this Claude settings.json, preserving other settings and hooks')
    parser.add_argument('--instructions', nargs=2, action='append', default=[], metavar=('SOURCE', 'TARGET'), help='Sync explicit instruction text into a managed block; preserve text outside it')
    parser.add_argument('--apply', action='store_true', help='Apply the printed plan; default is read-only')
    args = parser.parse_args(argv)
    if not (args.target or args.claude_settings or args.instructions):
        parser.error('Select --target, --claude-settings, or --instructions')
    revision = git('rev-parse', '--verify', args.ref + '^{commit}').decode().strip()
    with tempfile.TemporaryDirectory(prefix='skills-sync-') as raw:
        stage = Path(raw)
        archive = git('-c', 'tar.umask=0022', 'archive', revision, 'skills', 'global-instructions/hooks')
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(stage, filter='data')
        changes = []
        def add(source, target):
            target = target.expanduser().absolute()
            if target.is_symlink():
                raise ValueError(f'Refusing symlink target: {target}')
            resolved = target.resolve()
            if resolved == REPO or REPO in resolved.parents or resolved in REPO.parents:
                raise ValueError(f'Refusing source checkout overlap: {target}')
            if any(resolved == t.resolve() or resolved in t.resolve().parents or t.resolve() in resolved.parents for _, t in changes):
                raise ValueError(f'Overlapping targets: {target}')
            if identity(source) != identity(target):
                changes.append((source, target))
        for root in args.target:
            root = root.expanduser().resolve()
            if not root.is_dir():
                raise ValueError(f'Skill root must already exist; use install.sh for first installation: {root}')
            for skill in sorted((stage / 'skills').iterdir()):
                target = root / skill.name
                if target.exists() or target.is_symlink():
                    add(skill, target)
        if args.claude_settings:
            target = args.claude_settings.expanduser()
            old = json.loads(target.read_text()) if target.exists() else {}
            # Versioned snapshots keep settings tied to immutable hook bytes.
            snapshot = Path.home() / '.local/share/skills/hooks' / revision
            add(stage / 'global-instructions/hooks', snapshot / 'global-instructions/hooks')
            example = json.loads((stage / 'global-instructions/hooks/claude-settings.example.json').read_text())
            updated = settings(old, example, snapshot)
            output = stage / 'settings.json'
            output.write_text(json.dumps(updated, indent=2) + '\n')
            output.chmod(target.stat().st_mode & 0o777 if target.exists() else 0o600)
            add(output, target)
        for index, (source_name, target_name) in enumerate(args.instructions):
            source, target = Path(source_name).expanduser(), Path(target_name).expanduser()
            body = source.read_text()
            if BEGIN in body or END in body:
                raise ValueError('Instruction source must not contain skills-sync markers')
            output = stage / f'instructions-{index}.md'
            output.write_text(instructions(target.read_text() if target.exists() else '', body))
            output.chmod(target.stat().st_mode & 0o777 if target.exists() else 0o600)
            add(output, target)
        print(f'Revision: {revision}')
        for _, target in changes:
            print(f'UPDATE {target}')
        print(f'{len(changes)} changes; ' + ('applying' if args.apply else 'preview only (use --apply)'))
        if args.apply and changes:
            backup_root = Path.home() / '.local/state/skills-sync/backups'
            backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            backup = apply(changes, backup_root)
            print(f'Backups and receipt: {backup}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
