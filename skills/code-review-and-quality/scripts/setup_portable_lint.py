#!/usr/bin/env python3
"""Explicitly provision or inspect locked lint tooling outside application trees."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ASSETS = Path(__file__).resolve().parents[1] / 'assets/portable-lint'
PYTHON_TOOLS = {'ruff': '0.16.10', 'mypy': '2.4.0'}


def command(argv, *, cwd=None, timeout=30):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f'{Path(argv[0]).name} failed (exit {result.returncode}): {result.stderr[-2000:]}')
    return result.stdout.strip()


def digest(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'expected regular tooling input: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node_version():
    value = command(['node', '--version'])
    parts = tuple(int(part) for part in value.removeprefix('v').split('.'))
    if len(parts) != 3 or not (parts[0] >= 24 or parts[0] == 22 and parts[1] >= 13):
        raise ValueError('requires Node 22.13+ on the 22 line or Node 24+')
    return value


def require_python_tool_version(package, observed):
    version = PYTHON_TOOLS[package]
    if observed.split()[:2] != [package, version]:
        raise ValueError(f'requires {package} {version}; observed {observed}')


def inspect_runtime(runtime: Path, language='auto'):
    """Read installed versions and frozen manifests; never repair or install."""
    runtime = runtime.resolve(strict=True)
    tools = {}
    locks = {}
    if language in ('auto', 'typescript'):
        tools['node'] = node_version()
        expected = json.loads((ASSETS / 'package.json').read_text())['dependencies']
        for package, version in expected.items():
            manifest = runtime / 'node_modules' / package / 'package.json'
            if manifest.is_symlink():
                raise ValueError(f'symlink package manifest unsupported: {package}')
            actual = json.loads(manifest.read_text())['version']
            if actual != version:
                raise ValueError(f'requires {package} {version}; observed {actual}')
            tools[package] = actual
        for name in ('package.json', 'package-lock.json'):
            locks[name] = digest(ASSETS / name)
            if digest(runtime / name) != locks[name]:
                raise ValueError(f'runtime {name} differs from the locked profile')
    if language in ('auto', 'python'):
        python = runtime / 'python/bin/python'
        for package, version in PYTHON_TOOLS.items():
            observed = command([str(python), '-I', '-m', package, '--version'])
            require_python_tool_version(package, observed)
            tools[package] = version
        tools['python'] = command([str(python), '-I', '-c', 'import platform; print(platform.python_version())'])
        locks['requirements.lock'] = digest(ASSETS / 'requirements.lock')
        if digest(runtime / 'requirements.lock') != locks['requirements.lock']:
            raise ValueError('runtime Python lock differs from the locked profile')
    return {'tools': tools, 'locks': locks, 'runtime': str(runtime)}


def prerequisites(language):
    # Reuse the runner's concrete sibling contract before any installation.
    # Importing this standard-library-only module does not invoke lint/setup.
    runner = Path(__file__).with_name('portable_lint.py')
    if not runner.is_file() or runner.is_symlink():
        raise ValueError('missing regular portable_lint.py runner')
    spec = importlib.util.spec_from_file_location('portable_lint_preflight', runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_profile()
    found = {'python': sys.version.split()[0]}
    if sys.version_info < (3, 10):
        raise ValueError('setup requires Python 3.10+')
    if language in ('auto', 'typescript'):
        found['node'] = node_version()
        found['npm'] = command(['npm', '--version'])
    if language in ('auto', 'python'):
        found['uv'] = command(['uv', '--version'])
    return found


def setup(runtime, language):
    # Provisioning an existing path is intentionally not an update operation.
    if runtime.exists() or runtime.is_symlink():
        raise ValueError('runtime already exists; use --doctor or choose a fresh external directory')
    prerequisites(language)
    runtime.mkdir(mode=0o700, parents=False)
    marker = runtime / 'skills-portable-lint.json'
    marker.write_text(json.dumps({'version': 1, 'owner': 'skills-portable-lint', 'complete': False}) + '\n')
    os.chmod(marker, 0o600)
    if language in ('auto', 'typescript'):
        for name in ('package.json', 'package-lock.json'):
            shutil.copyfile(ASSETS / name, runtime / name)
        command(['npm', 'ci', '--prefix', str(runtime), '--ignore-scripts', '--no-audit', '--no-fund'], timeout=300)
    if language in ('auto', 'python'):
        shutil.copyfile(ASSETS / 'requirements.lock', runtime / 'requirements.lock')
        command(['uv', 'venv', '--no-python-downloads', '--python', sys.executable, str(runtime / 'python')])
        command(['uv', 'pip', 'sync', '--python', str(runtime / 'python/bin/python'),
                 '--require-hashes', '--only-binary', ':all:', str(runtime / 'requirements.lock')], timeout=300)
    result = {'version': 1, 'owner': 'skills-portable-lint', 'complete': True,
              'language': language, **inspect_runtime(runtime, language)}
    marker.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--language', choices=['auto', 'python', 'typescript'], default='auto')
    parser.add_argument('--doctor', action='store_true', help='read-only prerequisite/runtime inspection')
    args = parser.parse_args()
    if not args.doctor and args.runtime is None:
        parser.error('setup requires --runtime with a fresh external directory')
    try:
        result = ({'passed': True, 'prerequisites': prerequisites(args.language),
                   **(inspect_runtime(args.runtime, args.language) if args.runtime else {})}
                  if args.doctor else {'passed': True, **setup(args.runtime.absolute(), args.language)})
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        result = {'passed': False, 'unavailable': str(error)}
    print(json.dumps(result))
    return 0 if result['passed'] else 3


if __name__ == '__main__':
    sys.exit(main())
