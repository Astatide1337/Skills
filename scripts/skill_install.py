"""Transactional local skill copies. No network or implicit harness selection."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = '.skills-install.json'
IGNORED = {'__pycache__', '.pytest_cache', '.DS_Store'}


def files(path):
    result = {}
    for item in sorted(path.rglob('*')):
        if any(part in IGNORED for part in item.relative_to(path).parts):
            continue
        if item.is_symlink():
            raise ValueError(f'Symlink in package: {item}')
        if item.is_file():
            result[str(item.relative_to(path))] = {
                'sha256': hashlib.sha256(item.read_bytes()).hexdigest(),
                'mode': item.stat().st_mode & 0o777,
            }
    return result


def identity(path):
    listing = files(path)
    return {'files': listing, 'revision': hashlib.sha256(json.dumps(listing, sort_keys=True).encode()).hexdigest()}


def safe_target(value):
    path = Path(value).expanduser().absolute()
    resolved = path.resolve()
    source = (ROOT / 'skills').resolve()
    if resolved == source or source in resolved.parents or resolved in source.parents:
        raise ValueError('Refusing target in or above source skill tree.')
    if resolved in (Path('/'), Path.home().resolve()):
        raise ValueError(f'Refusing unsafe target: {resolved}')
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f'Refusing symlink target component: {part}')
    if path.exists() and not path.is_dir():
        raise ValueError('Target must be a directory.')
    return path


def load_receipt(target):
    path = target / RECEIPT
    if path.is_symlink():
        raise ValueError('Refusing symlink receipt.')
    if not path.exists():
        return {'schema': 1, 'packages': {}}
    receipt = json.loads(path.read_text())
    if type(receipt.get('schema')) is not int or receipt['schema'] != 1 or not isinstance(receipt.get('packages'), dict):
        raise ValueError('Invalid installer receipt.')
    for name in receipt['packages']:
        valid_name(name)
    return receipt


def valid_name(name):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise ValueError(f'Invalid skill name: {name}')


def replace_receipt(target, receipt):
    temporary = target / (RECEIPT + '.tmp')
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('Receipt temporary path already exists.')
    try:
        with temporary.open('x') as output:
            output.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        temporary.replace(target / RECEIPT)
    finally:
        if temporary.exists():
            temporary.unlink()


def transaction(target, changes, receipt, preserve):
    # All validation and source staging precede this function.
    previous = load_receipt(target)
    for name in changes:
        destination = target / name
        if destination.is_symlink():
            raise ValueError(f'Refusing symlink destination: {destination}')
        if destination.exists():
            owned = previous['packages'].get(name)
            if not preserve and (not owned or identity(destination) != owned):
                raise ValueError(f'Existing {name} is unowned or divergent; use --preserve-existing to back it up.')
    target.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f'.{target.name}-backup-{uuid.uuid4().hex}'
    backup.mkdir()
    (backup / 'receipt.json').write_text(json.dumps(previous))
    moved, installed = [], []
    try:
        for name, staged in changes.items():
            destination = target / name
            if destination.exists():
                destination.rename(backup / name)
                moved.append(name)
            if staged is not None:
                installed.append(name)
                shutil.copytree(staged, destination)
        receipt['last_transaction'] = {'backup': str(backup), 'changed': list(changes), 'installed': installed}
        replace_receipt(target, receipt)
    except Exception:
        for name in installed:
            shutil.rmtree(target / name, ignore_errors=True)
        for name in moved:
            (backup / name).rename(target / name)
        raise
    print(f'Recovery backup: {backup}')


def rollback(target, preserve):
    current = load_receipt(target)
    last = current.get('last_transaction')
    if last is None:
        raise ValueError('No transaction to roll back.')
    if not isinstance(last, dict):
        raise TypeError('Invalid transaction receipt.')
    backup = Path(last['backup'])
    if backup.parent != target.parent or not backup.name.startswith(f'.{target.name}-backup-') or backup.is_symlink():
        raise ValueError('Invalid recovery backup.')
    previous = json.loads((backup / 'receipt.json').read_text())
    changes = {}
    for name in last['changed']:
        valid_name(name)
        changes[name] = backup / name if (backup / name).exists() else None
        if changes[name] is not None:
            files(changes[name])
    transaction(target, changes, previous, preserve)


def dependency_graph(packages, folder):
    graph = {'code-review-and-quality': ['verify-work'],
             'teach': ['how', 'why'], 'why': ['how']}
    # Shared coordinator references are required; its domain route table is optional.
    for name in packages:
        if name != 'follow-instructions' and any(
                '../follow-instructions/' in item.read_text(errors='replace')
                for item in (folder / name).rglob('*.md')):
            graph.setdefault(name, []).append('follow-instructions')
    return {name: sorted(set(graph.get(name, []))) for name in packages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', help='Explicit directory containing skill folders (required for mutations).')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--skill', action='append', default=[])
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--preserve-existing', action='store_true', help='Back up unowned/divergent packages before replacement or removal.')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--agent-clis-source', help='Explicit opt-in to the separate pinned application CLI installer.')
    args = parser.parse_args()
    source = ROOT / 'skills'
    available = sorted(item.name for item in source.iterdir() if item.is_dir() and (item / 'SKILL.md').is_file())
    if args.list:
        print('\n'.join(available)); return
    if not args.target:
        raise ValueError('Pass --target explicitly; no harness is selected implicitly.')
    target = safe_target(args.target)
    if args.rollback:
        if args.all or args.skill or args.uninstall or args.agent_clis_source:
            raise ValueError('--rollback cannot be combined with selection or installation options.')
        rollback(target, args.preserve_existing); return
    if args.all and args.skill:
        raise ValueError('Use --all or --skill, not both.')
    previous = load_receipt(target)
    selected = sorted(previous['packages']) if args.all and args.uninstall else available if args.all else sorted(set(args.skill))
    if not selected:
        raise ValueError('Select --all or at least one --skill.')
    for name in selected:
        valid_name(name)
        if name not in (previous['packages'] if args.uninstall else available):
            raise ValueError(f'Unknown or unowned skill: {name}')
    receipt = json.loads(json.dumps(previous))
    if args.uninstall:
        if args.agent_clis_source:
            raise ValueError('--uninstall cannot install application CLIs.')
        installed_dependencies = dependency_graph(previous['packages'], target)
        for caller in sorted(set(previous['packages']) - set(selected)):
            required = set(installed_dependencies.get(caller, [])) | set(previous.get('dependencies', {}).get(caller, []))
            removed = required & set(selected)
            if removed:
                raise ValueError(f'Cannot remove {sorted(removed)}: installed {caller} requires them; select callers too.')
        for name in selected:
            receipt['packages'].pop(name)
            receipt.get('dependencies', {}).pop(name, None)
        transaction(target, dict.fromkeys(selected), receipt, args.preserve_existing)
        return
    dependencies = dependency_graph(available, source)
    pending = list(selected)
    while pending:
        name = pending.pop(0)
        for dependency in dependencies.get(name, []):
            valid_name(dependency)
            if dependency not in available:
                raise ValueError(f'Missing declared dependency: {dependency}')
            if dependency in selected:
                continue
            # Preserve compatible pre-receipt runtime helper installations.
            if name == 'code-review-and-quality' and dependency == 'verify-work' and (target / dependency).exists():
                helper = target / dependency / 'scripts/check_profile.py'
                files(target / dependency)
                if not helper.is_file() or helper.read_bytes() != (source / dependency / 'scripts/check_profile.py').read_bytes():
                    raise ValueError('Existing verify-work helper is incompatible; explicitly select --skill verify-work and --preserve-existing to replace it.')
                print('reusing compatible verify-work helper')
                continue
            selected.append(dependency); pending.append(dependency)
            print(f'including required dependency: {dependency}')
    with tempfile.TemporaryDirectory(prefix='skills-stage-') as stage_dir:
        changes = {}
        for name in sorted(selected):
            origin = source / name
            if origin.is_symlink():
                raise ValueError(f'Symlink source package: {name}')
            files(origin)
            text = (origin / 'SKILL.md').read_text()
            if not text.strip():
                raise ValueError(f'Empty SKILL.md: {name}')
            staged = Path(stage_dir) / name
            shutil.copytree(origin, staged, ignore=shutil.ignore_patterns(*IGNORED))
            package = identity(staged)
            receipt['packages'][name] = package
            receipt.setdefault('dependencies', {})[name] = dependencies.get(name, [])
            destination = target / name
            if destination.exists() and not destination.is_symlink() and identity(destination) == package:
                print(f'unchanged {name}'); continue
            changes[name] = staged
        if changes:
            transaction(target, changes, receipt, args.preserve_existing)
            for name in changes:
                print(f'installed {name} -> {target / name}')
        elif receipt != previous:
            target.mkdir(parents=True, exist_ok=True)
            replace_receipt(target, receipt)
        if args.agent_clis_source:
            # Separate opt-in operation; its own receipt/recovery is independent.
            subprocess.run([sys.executable, str(ROOT / 'scripts/install-agent-clis.py'), '--source', args.agent_clis_source], check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
