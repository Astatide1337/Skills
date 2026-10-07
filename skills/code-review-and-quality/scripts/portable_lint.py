#!/usr/bin/env python3
"""Run a supplemental correctness check on explicit files without editing them."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('profile', ROOT / 'verify-work/scripts/check_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def run(workspace: Path, files: list[str], language: str, runtime: Path | None) -> dict:
    suffixes = {"python": {".py", ".pyi"}, "typescript": {".ts", ".tsx", ".mts", ".cts"}}
    if not files or len(set(files)) != len(files):
        raise ValueError('provide a nonempty unique list of files')
    if any(Path(f).suffix not in suffixes[language] or f.startswith('-') for f in files):
        raise ValueError('files must match the selected language and cannot be flags')
    before = profile.source_identity(workspace, files)
    if language == 'python':
        # The frozen Skills environment owns this dependency, not the app.
        version = subprocess.run([sys.executable, '-I', '-m', 'ruff', '--version'],
                                 capture_output=True, text=True, timeout=10)
        if version.returncode or version.stdout.strip() != 'ruff 0.16.10':
            raise ValueError('requires Ruff 0.16.10 in this Python environment; use uv sync --frozen in Skills')
        argv = [sys.executable, '-I', '-m', 'ruff', 'check', '--isolated', '--no-cache',
                '--ignore-noqa', '--output-format', 'json', '--select', 'F,B012,B018', '--', *files]
        identity = {'ruff': '0.16.10'}
    else:
        if runtime is None:
            raise ValueError('TypeScript requires --runtime with the separately installed locked npm dependencies')
        node = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10)
        parts = tuple(int(p) for p in node.stdout.strip().removeprefix('v').split('.'))
        if node.returncode or len(parts) != 3 or not (parts[0] >= 24 or (parts[0] == 22 and parts[1] >= 13)):
            raise ValueError('requires Node 22.13+ on the 22 line or Node 24+')
        runtime = runtime.resolve(strict=True)
        expected = json.loads((ROOT / 'code-review-and-quality/assets/portable-lint/package.json').read_text())['dependencies']
        identity = {}
        for package, version in expected.items():
            actual = json.loads((runtime / 'node_modules' / package / 'package.json').read_text())['version']
            if actual != version:
                raise ValueError(f'requires {package} {version}; observed {actual}')
            identity[package] = actual
        # Required project inputs are hashed too; dependent files remain a native-check concern.
        before.update(profile.source_identity(workspace, ['tsconfig.json']))
        argv = ['node', str(Path(__file__).with_name('lint_typescript.mjs')),
                str(runtime), str(workspace), *files]
    check = profile.execute({'id': language, 'phase': 'drive', 'argv': argv,
                             'timeout': 120, 'expect': {'/passed': True} if language == 'typescript' else {'': []}}, workspace)
    after = profile.source_identity(workspace, list(before))
    return {'version': 1, 'language': language, 'tools': identity,
            'source_before': before, 'source_after': after, 'check': check,
            'passed': check['status'] == 'accepted' and before == after}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--language', choices=['python', 'typescript'], required=True)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if args.receipt.resolve().is_relative_to(workspace):
        raise ValueError('receipt must be outside the checkout')
    with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        try:
            result = run(workspace, args.files, args.language, args.runtime)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            result = {'passed': False, 'unavailable': str(error)}
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'passed': result['passed'], 'receipt': str(args.receipt)}))
    return 0 if result['passed'] else 3


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
