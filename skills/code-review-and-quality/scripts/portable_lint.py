#!/usr/bin/env python3
"""Run a supplemental correctness check on explicit files without editing them."""
from __future__ import annotations
import argparse
from collections import Counter
from difflib import SequenceMatcher
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('profile', ROOT / 'verify-work/scripts/check_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def full_check(workspace: Path, files: list[str], language: str, runtime: Path | None) -> dict:
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
        identity = {'node': node.stdout.strip()}
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
    # Raw nonzero lint results remain failures in full mode. Comparison can
    # consume exit 1 diagnostics, but tool/parser/membership failures cannot
    # be reclassified as ordinary debt.
    diagnostics = []
    available = check.get('exit_code') in (0, 1) and before == after
    try:
        value = json.loads(check.get('stdout', ''))
        if language == 'python':
            if not isinstance(value, list):
                raise ValueError('Ruff diagnostics must be an array')
            for item in value:
                diagnostics.append({'file': str(Path(item['filename']).relative_to(workspace)),
                    'rule': item['code'], 'message': item['message'],
                    'line': item['location']['row'], 'column': item['location']['column'],
                    'end_line': item['end_location']['row'], 'end_column': item['end_location']['column']})
        else:
            if not isinstance(value, dict) or value.get('unavailable') or set(value.get('files', [])) != set(files):
                raise ValueError('TypeScript tooling or selected-file coverage unavailable')
            diagnostics = value['diagnostics']
        if any(d.get('rule') is None or d.get('rule') == 'invalid-syntax' for d in diagnostics):
            raise ValueError('parser/tooling diagnostics are not comparable debt')
        if (check.get('exit_code') == 0) != (not diagnostics):
            raise ValueError('diagnostics disagree with tool exit status')
    except (ValueError, KeyError, TypeError) as exc:
        available = False
        diagnostic_error = str(exc)
    return {'version': 1, 'language': language, 'tools': identity,
            'source_before': before, 'source_after': after, 'check': check,
            'diagnostics': diagnostics, 'diagnostics_available': available,
            **({'diagnostic_error': diagnostic_error} if not available and 'diagnostic_error' in locals() else {}),
            'passed': available and check['status'] == 'accepted' and before == after}


def compare_diagnostics(current: list[dict], baseline: list[dict],
                        current_sources: dict[str, str], baseline_sources: dict[str, str]) -> dict:
    """Consume occurrences with unchanged source spans, using location mapping.

    Exact unchanged moves are recognized only for a unique line in both files.
    Edited/ambiguous spans stay new-or-changed: this is conservative attribution,
    not a claim about the historical author of a diagnostic.
    """
    remaining = list(baseline)
    existing = []
    introduced = []
    mappings = {}
    for name, source in current_sources.items():
        old = baseline_sources[name].splitlines(keepends=True)
        new = source.splitlines(keepends=True)
        mapped = {}
        for block in SequenceMatcher(None, old, new, autojunk=False).get_matching_blocks():
            mapped.update({block.b + i + 1: block.a + i + 1 for i in range(block.size)})
        mappings[name] = (old, new, mapped, Counter(old), Counter(new))
    def same_occurrence(now, prior):
        if any(now.get(k) != prior.get(k) for k in ('file', 'rule', 'message', 'column', 'end_column')):
            return False
        old, new, mapped, old_counts, new_counts = mappings[now['file']]
        start, end = now['line'], now.get('end_line') or now['line']
        pstart, pend = prior['line'], prior.get('end_line') or prior['line']
        if new[start - 1:end] != old[pstart - 1:pend]:
            return False
        if all(mapped.get(line) == pstart + line - start for line in range(start, end + 1)):
            return True
        return (start == end and pstart == pend and old_counts[old[pstart - 1]] == 1
                and new_counts[new[start - 1]] == 1)
    for diagnostic in current:
        match = next((i for i, old in enumerate(remaining) if same_occurrence(diagnostic, old)), None)
        if match is None:
            introduced.append(diagnostic)
        else:
            existing.append({'current': diagnostic, 'baseline': remaining.pop(match)})
    return {'existing': existing, 'new_or_changed': introduced, 'resolved': remaining,
            'passed': not introduced, 'attribution': 'one-to-one unchanged spans; ambiguous/edited spans conservatively new-or-changed'}


def run(workspace: Path, files: list[str], language: str, runtime: Path | None,
        *, baseline_workspace: Path | None = None) -> dict:
    current = full_check(workspace, files, language, runtime)
    current['mode'] = 'compare' if baseline_workspace is not None else 'full'
    if baseline_workspace is None:
        return current
    current['full_passed'] = current['passed']
    current['passed'] = False
    try:
        baseline_workspace = baseline_workspace.resolve(strict=True)
        if baseline_workspace == workspace:
            raise ValueError('baseline must be an independently selected separate workspace')
        current_sources = {name: profile.bounded_path(workspace, name).read_bytes().decode() for name in files}
        baseline_sources = {name: profile.bounded_path(baseline_workspace, name).read_bytes().decode() for name in files}
        baseline = full_check(baseline_workspace, files, language, runtime)
        current['baseline'] = baseline
        if not current['diagnostics_available'] or not baseline['diagnostics_available']:
            raise ValueError('current/baseline diagnostics unavailable or incompatible; inspect raw checks')
        if current['tools'] != baseline['tools']:
            raise ValueError('baseline toolchain differs from current')
        # The source text used for attribution must still match both executions.
        if (profile.source_identity(workspace, list(current['source_after'])) != current['source_after']
                or profile.source_identity(baseline_workspace, list(baseline['source_after'])) != baseline['source_after']
                or any(profile.digest(workspace / name) != hashlib.sha256(text.encode()).hexdigest()
                       for name, text in current_sources.items())
                or any(profile.digest(baseline_workspace / name) != hashlib.sha256(text.encode()).hexdigest()
                       for name, text in baseline_sources.items())):
            raise ValueError('inputs changed during baseline comparison')
        comparison = compare_diagnostics(current['diagnostics'], baseline['diagnostics'], current_sources, baseline_sources)
        current['comparison'] = {'status': 'accepted' if comparison['passed'] else 'failed', **comparison}
        current['baseline_workspace'] = str(baseline_workspace)
        current['passed'] = comparison['passed']
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        current['comparison'] = {'status': 'unavailable', 'reason': str(exc)}
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--language', choices=['python', 'typescript'], required=True)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--mode', choices=['full', 'compare'], default='full')
    parser.add_argument('--baseline-workspace', type=Path)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    if (args.mode == 'compare') != (args.baseline_workspace is not None):
        raise ValueError('compare requires --baseline-workspace; full does not accept a baseline')
    workspace = args.workspace.resolve(strict=True)
    if (args.receipt.resolve().is_relative_to(workspace) or (args.baseline_workspace is not None
            and args.receipt.resolve().is_relative_to(args.baseline_workspace.resolve()))):
        raise ValueError('receipt must be outside both current and baseline checkouts')
    with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        try:
            result = run(workspace, args.files, args.language, args.runtime, baseline_workspace=args.baseline_workspace)
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
