#!/usr/bin/env python3
"""Run a supplemental correctness check on explicit files without editing them."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
from difflib import SequenceMatcher
import importlib.util
import hashlib
import json
import os
import io
import re
import tempfile
import tokenize
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
profile = None


def load_profile():
    """Load the concrete sibling dependency after CLI argument handling."""
    global profile
    if profile is None:
        helper = ROOT / 'verify-work/scripts/check_profile.py'
        if not helper.is_file() or helper.is_symlink():
            raise ValueError('missing verify-work helper; reinstall code-review-and-quality with scripts/install.sh')
        spec = importlib.util.spec_from_file_location('profile', helper)
        if spec is None or spec.loader is None:
            raise ValueError('verify-work helper cannot be loaded')
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except (ImportError, OSError, SyntaxError) as exc:
            raise ValueError(f'verify-work helper unavailable: {exc}') from exc
        if any(not callable(getattr(module, name, None)) for name in ('source_identity', 'execute', 'bounded_path', 'digest')):
            raise ValueError('incompatible verify-work helper; reinstall the explicitly selected dependency')
        profile = module
    return profile


SUFFIXES = {"python": {".py", ".pyi"},
            "typescript": {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}}
EXCLUDED_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.mypy_cache',
                 '.ruff_cache', '.pytest_cache', 'dist', 'build', 'coverage', '.next'}


def runtime_helper():
    path = Path(__file__).with_name('setup_portable_lint.py')
    spec = importlib.util.spec_from_file_location('portable_lint_setup', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bounded_sources(workspace, suffixes, *, start=None):
    """Inventory regular source inputs without following excluded/symlink trees."""
    load_profile()
    result, excluded = [], []
    for directory, folders, names in os.walk(start or workspace, followlinks=False):
        base = Path(directory)
        keep = []
        for name in sorted(folders):
            path = base / name
            relative = path.relative_to(workspace)
            if name in EXCLUDED_DIRS or path.is_symlink() or profile.sensitive_path(relative):
                excluded.append({'file': str(relative), 'reason': 'excluded directory or unsafe context'})
            else:
                keep.append(name)
        folders[:] = keep
        for name in sorted(names):
            path = base / name
            if path.suffix not in suffixes:
                continue
            relative = str(path.relative_to(workspace))
            if path.is_symlink() or profile.sensitive_path(Path(relative)):
                excluded.append({'file': relative, 'reason': 'symlink or sensitive path'})
            elif path.is_file():
                result.append(relative)
        if len(result) > 4096:
            raise ValueError('bounded source context exceeds 4096 files; select a smaller source directory/workspace')
    return sorted(result), excluded


def without_type_suppressions(data):
    """Blank only suppression comments, retaining source lines and columns."""
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    lines = data.decode(encoding).splitlines(keepends=True)
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(data).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Preserve malformed source for the real parser's unavailable stage.
        return data
    for token in tokens:
        if token.type == tokenize.COMMENT and re.match(r'#\s*(?:type:\s*ignore\b|mypy:)', token.string):
            row, column = token.start
            end_row, end_column = token.end
            if row != end_row:
                raise ValueError('unsupported multiline suppression comment')
            line = lines[row - 1]
            lines[row - 1] = line[:column] + ' ' * (end_column - column) + line[end_column:]
    return ''.join(lines).encode(encoding)


def python_context(workspace, executable, tools_python):
    sources, excluded = bounded_sources(workspace, SUFFIXES['python'])
    before = profile.source_identity(workspace, sources)
    if sum((workspace / name).stat().st_size for name in sources) > 64 * 1024 * 1024:
        raise ValueError('bounded Python source context exceeds 64 MiB')
    facts = subprocess.run([str(executable), '-I', '-c',
        'import json,sys,sysconfig; print(json.dumps({"version":list(sys.version_info[:3]),"paths":{k:sysconfig.get_path(k) for k in ("purelib","platlib","stdlib")}}))'],
        capture_output=True, text=True, timeout=15, check=True)
    facts = json.loads(facts.stdout)
    # Match pinned Mypy's actual package search, including site/.pth additions.
    # Unknown roots are unavailable before their contents are read; silently
    # hashing only purelib/platlib would miss imports Mypy can actually consume.
    roots = {Path(facts['paths'][name]).resolve(strict=True) for name in ('purelib', 'platlib')}
    stdlib = Path(facts['paths']['stdlib'])
    standard_roots = {path.resolve(strict=True) for path in (stdlib, stdlib / 'lib-dynload') if path.is_dir()}
    package_root = subprocess.run([str(tools_python), '-I', '-c',
        'import mypy, pathlib; print(pathlib.Path(mypy.__file__).parent)'],
        capture_output=True, text=True, timeout=15, check=True)
    mypy_root = Path(package_root.stdout.strip())
    pyinfo = mypy_root / 'pyinfo.py'
    env = os.environ.copy()
    for name in ('MYPYPATH', 'MYPY_CONFIG_FILE_DIR', 'PYTHONPATH', 'PYTHONHOME'):
        env.pop(name, None)
    env['PYTHONSAFEPATH'] = '1'
    if str(executable) == str(tools_python.absolute()):
        argv = [str(executable), '-I', '-c',
                'import mypy.pyinfo; print(repr(mypy.pyinfo.getsearchdirs()))']
    else:
        argv = [str(executable), str(pyinfo), 'getsearchdirs']
    search = subprocess.run(argv, cwd=workspace, env=env, capture_output=True,
                            text=True, timeout=15, check=True)
    search_dirs = ast.literal_eval(search.stdout)
    if (not isinstance(search_dirs, tuple) or len(search_dirs) != 2
            or any(not isinstance(group, list) or any(not isinstance(path, str) for path in group)
                   for group in search_dirs)):
        raise ValueError('target Python search roots unavailable')
    facts['mypy_search_dirs'] = search_dirs
    for name in (*search_dirs[0], *search_dirs[1]):
        path = Path(name)
        if not path.is_absolute():
            raise ValueError('unsupported relative Python dependency root')
        if path.exists():
            resolved = path.resolve(strict=True)
            if resolved not in roots | standard_roots:
                raise ValueError('unsupported Python dependency root outside interpreter libraries (site/.pth context)')
            # Some relocated interpreters expose canonical stdlib paths that
            # pinned Mypy's lexical exclusion does not remove. Record those too.
            roots.add(resolved)
    roots.add(mypy_root / 'typeshed')
    dependencies = {}
    for root in sorted(roots):
        for directory, folders, names in os.walk(root, followlinks=False):
            base = Path(directory)
            permitted_folders = []
            for name in sorted(folders):
                if name in EXCLUDED_DIRS:
                    continue
                if (base / name).is_symlink() or profile.sensitive_path(Path(name)):
                    raise ValueError('unsupported symlink or sensitive dependency directory')
                permitted_folders.append(name)
            folders[:] = permitted_folders
            for name in sorted(names):
                path = base / name
                if path.suffix not in SUFFIXES['python'] | {'.pth'} and name not in ('METADATA', 'py.typed'):
                    continue
                if path.is_symlink():
                    raise ValueError(f'unsupported symlink dependency input: {path.name}')
                # These are source/stub files in an explicitly trusted Python
                # installation, including standard secrets.pyi and token.pyi.
                # Only these source/stub/metadata and regular .pth inputs are read.
                dependencies[str(path)] = profile.digest(path)
                if len(dependencies) > 20000:
                    raise ValueError('Python dependency context exceeds 20000 inputs; select a bounded target interpreter')
    dependencies[str(pyinfo)] = profile.digest(pyinfo)
    venv_config = executable.parent.parent / 'pyvenv.cfg'
    if venv_config.is_file():
        if venv_config.is_symlink():
            raise ValueError('unsupported symlink Python interpreter configuration')
        dependencies[str(venv_config)] = profile.digest(venv_config)
    dependencies[str(executable.resolve(strict=True))] = profile.digest(executable.resolve(strict=True))
    return before, dependencies, {'interpreter': str(executable), 'facts': facts, 'excluded': excluded}


def parse_ruff(check, workspace):
    value = json.loads(check.get('stdout', ''))
    if not isinstance(value, list):
        raise ValueError('Ruff diagnostics must be an array')
    return [{'file': str(Path(item['filename']).relative_to(workspace)), 'rule': item['code'],
             'message': item['message'], 'line': item['location']['row'], 'column': item['location']['column'],
             'end_line': item['end_location']['row'], 'end_column': item['end_location']['column']}
            for item in value]


def execute_lint(identifier, argv, workspace, *, mypypath=None):
    """Use the existing group/timeout helper with external raw-output files.

    The helper's 64KiB JSON envelope is intentionally retained. Diagnostics
    and consumed-input identities can exceed it, so only a bounded envelope
    travels through that channel; the private temporary artifact is read here.
    """
    wrapper = (
        'import json,os,subprocess,sys; '
        'env=os.environ.copy(); '
        '[env.pop(k,None) for k in ("MYPYPATH","MYPY_CONFIG_FILE_DIR","PYTHONPATH","PYTHONHOME")]; '
        'env.update({"MYPYPATH":sys.argv[3]} if sys.argv[3] else {}); '
        'out=open(sys.argv[1],"wb"); err=open(sys.argv[2],"wb"); '
        'p=subprocess.run(sys.argv[4:],stdout=out,stderr=err,env=env); '
        'out.close(); err.close(); '
        'print(json.dumps({"passed":p.returncode==0,"exit_code":p.returncode})); '
        'sys.exit(p.returncode)'
    )
    with tempfile.TemporaryDirectory(prefix='skills-lint-output-') as raw:
        stdout, stderr = Path(raw) / 'stdout', Path(raw) / 'stderr'
        record = profile.execute({'id': identifier, 'phase': 'drive', 'argv':
            [sys.executable, '-I', '-c', wrapper, str(stdout), str(stderr), mypypath or '', *argv],
            'timeout': 120, 'expect': {'/passed': True}}, workspace)
        record['argv'] = argv
        if stdout.exists():
            if stdout.stat().st_size > 16 * 1024 * 1024:
                record.update({'status': 'failed', 'reason': 'raw lint output exceeds 16 MiB', 'exit_code': None})
            else:
                record['stdout'] = stdout.read_text(errors='replace')
                record['stdout_sha256'] = profile.digest(stdout)
            record['stderr'] = stderr.read_bytes()[:65536].decode(errors='replace')
    return record


def full_check(workspace: Path, files: list[str], language: str, runtime: Path | None,
               *, project=None, python_executable=None) -> dict:
    load_profile()
    if not files or len(set(files)) != len(files):
        raise ValueError('provide a nonempty unique list of files')
    if any(Path(name).suffix not in SUFFIXES[language] or name.startswith('-') for name in files):
        raise ValueError('files must match the selected language and cannot be flags')
    selected_before = profile.source_identity(workspace, files)
    profile_inputs = [Path(__file__), Path(__file__).with_name('setup_portable_lint.py'),
                      ROOT / 'verify-work/scripts/check_profile.py',
                      ROOT / 'code-review-and-quality/assets/portable-lint/package.json',
                      ROOT / 'code-review-and-quality/assets/portable-lint/package-lock.json',
                      ROOT / 'code-review-and-quality/assets/portable-lint/requirements.lock']
    if language == 'typescript':
        profile_inputs.append(Path(__file__).with_name('lint_typescript.mjs'))
    profile_before = {str(path): profile.digest(path) for path in profile_inputs}
    if runtime is not None:
        runtime = runtime.resolve(strict=True)
        if runtime.is_relative_to(workspace):
            raise ValueError('runtime must be outside the target workspace')
    helper = runtime_helper()
    diagnostics, checks, stages = [], [], []
    context = {'configs': [], 'inputs': {str(workspace / name): digest for name, digest in selected_before.items()}}
    before = selected_before.copy()
    available = True
    identity = {}
    diagnostic_error = None
    if language == 'python':
        tools_python = runtime / 'python/bin/python' if runtime else Path(sys.executable)
        if runtime:
            identity = helper.inspect_runtime(runtime, 'python')['tools']
        else:
            for package, version in helper.PYTHON_TOOLS.items():
                observed = helper.command([str(tools_python), '-I', '-m', package, '--version'])
                helper.require_python_tool_version(package, observed)
                identity[package] = version
        # Preserve the venv interpreter locator: resolving its executable
        # symlink before invocation would discard pyvenv.cfg dependency context.
        executable = Path(python_executable or tools_python).absolute()
        if not executable.is_file():
            raise ValueError('target Python interpreter must be an existing trusted executable')
        before, dependencies, facts = python_context(workspace, executable, tools_python)
        context.update({'python': facts, 'inputs': {**{str(workspace / name): value for name, value in before.items()}, **dependencies}})
        ruff = execute_lint('ruff',
            [str(tools_python), '-I', '-m', 'ruff', 'check', '--isolated', '--no-cache', '--ignore-noqa',
             '--output-format', 'json', '--select', 'F,B012,B018', '--', *files],
            workspace)
        checks.append(ruff)
        try:
            parsed = parse_ruff(ruff, workspace)
            if ruff.get('exit_code') not in (0, 1) or (ruff.get('exit_code') == 0) != (not parsed):
                raise ValueError('Ruff diagnostics disagree with exit status')
            diagnostics.extend(parsed)
            stages.append({'id': 'ruff', 'status': 'failed' if parsed else 'accepted'})
        except (ValueError, KeyError, TypeError) as error:
            available, diagnostic_error = False, str(error)
            stages.append({'id': 'ruff', 'status': 'unavailable', 'reason': str(error)})
        # Native Mypy configuration/plugins are never loaded. The snapshot has
        # the real module layout and unchanged line locations, with ignores blanked.
        with tempfile.TemporaryDirectory(prefix='skills-python-context-') as raw:
            snapshot = Path(raw)
            for name in before:
                target = snapshot / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(without_type_suppressions((workspace / name).read_bytes()))
            config = snapshot / '.skills-mypy.ini'
            config.write_text('[mypy]\n')
            argv = [str(tools_python), '-I', '-m', 'mypy', '--strict', '--config-file', str(config),
                    '--no-incremental', '--cache-dir', '/dev/null', '--output', 'json',
                    '--python-executable', str(executable), '--python-version',
                    '.'.join(str(part) for part in facts['facts']['version'][:2]),
                    '--explicit-package-bases', *files]
            # execute's env schema cannot be broadened; scope this environment
            # to the subprocess directly, without inherited Python/Mypy config.
            mypypath = os.pathsep.join(str(path) for path in (snapshot, snapshot / 'src') if path.is_dir())
            mypy = execute_lint('mypy', argv, snapshot, mypypath=mypypath)
            checks.append(mypy)
            try:
                parsed = []
                for line in mypy.get('stdout', '').splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    if item.get('severity') != 'error':
                        continue
                    name = str(Path(item['file']))
                    if name not in before:
                        raise ValueError('Mypy diagnostic outside bounded source context')
                    parsed.append({'file': name, 'rule': 'mypy/' + (item.get('code') or 'unknown'),
                        'message': item['message'], 'line': max(item['line'], 1), 'column': max(item['column'] + 1, 1),
                        'end_line': max(item.get('end_line') or item['line'], 1),
                        'end_column': max((item.get('end_column') or item['column']) + 1, 1)})
                if mypy.get('exit_code') not in (0, 1) or (mypy.get('exit_code') == 0) != (not parsed):
                    raise ValueError('Mypy diagnostics disagree with exit status')
                if any(item['rule'] in ('mypy/import-not-found', 'mypy/import-untyped', 'mypy/syntax') for item in parsed):
                    raise ValueError('Mypy import/parser context unavailable; raw diagnostics retained')
                diagnostics.extend(parsed)
                stages.append({'id': 'mypy', 'status': 'failed' if parsed else 'accepted'})
            except (ValueError, KeyError, TypeError) as error:
                available, diagnostic_error = False, str(error)
                stages.append({'id': 'mypy', 'status': 'unavailable', 'reason': str(error)})
    else:
        if runtime is None:
            raise ValueError('TypeScript requires --runtime with separately installed locked dependencies')
        identity = helper.inspect_runtime(runtime, 'typescript')['tools']
        argv = ['node', str(Path(__file__).with_name('lint_typescript.mjs')), str(runtime), str(workspace)]
        if project:
            argv.extend(['--project', project])
        argv.extend(files)
        check = execute_lint('typescript', argv, workspace)
        checks.append(check)
        try:
            value = json.loads(check.get('stdout', ''))
            if not isinstance(value, dict) or set(value.get('files', [])) != set(files):
                raise ValueError('TypeScript selected-file coverage unavailable')
            diagnostics = value['diagnostics']
            stages = value['stages']
            context = value['context']
            if value.get('unavailable') or value.get('unchanged_inputs') is not True:
                raise ValueError(value.get('unavailable') or 'TypeScript context changed')
            if check.get('exit_code') not in (0, 1) or (check.get('exit_code') == 0) != (not diagnostics):
                raise ValueError('TypeScript diagnostics disagree with exit status')
        except (ValueError, KeyError, TypeError) as error:
            available, diagnostic_error = False, str(error)
            if not stages:
                stages = [{'id': 'typescript', 'status': 'unavailable', 'reason': str(error)}]
    after = profile.source_identity(workspace, list(before))
    unchanged = before == after and all(profile.digest(Path(name)) == value for name, value in context['inputs'].items())
    if language == 'python':
        final_sources, final_dependencies, final_facts = python_context(workspace, executable, tools_python)
        unchanged = unchanged and final_sources == before and final_dependencies == dependencies and final_facts == facts
    profile_after = {str(path): profile.digest(path) for path in profile_inputs}
    unchanged = unchanged and profile_before == profile_after
    available = available and unchanged and all(stage['status'] != 'unavailable' for stage in stages)
    if any(item.get('rule') is None or item.get('rule') in ('invalid-syntax', 'mypy/syntax') for item in diagnostics):
        available = False
        diagnostic_error = 'parser/tooling diagnostics are not comparable debt'
    profile_sha256 = hashlib.sha256(json.dumps({path.name: profile_before[str(path)] for path in profile_inputs}, sort_keys=True).encode()).hexdigest()
    return {'version': 2, 'language': language, 'tools': identity, 'profile_sha256': profile_sha256,
            'files': files, 'source_before': before, 'source_after': after, 'context': context,
            'check': checks[0], 'checks': checks, 'stages': stages, 'unchanged_inputs': unchanged,
            'diagnostics': diagnostics, 'diagnostics_available': available,
            **({'diagnostic_error': diagnostic_error} if diagnostic_error else {}),
            'passed': available and all(stage['status'] == 'accepted' for stage in stages)}


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


def context_contract(result, workspace, selected):
    """Compare nonselected source/config/dependency identity across snapshots."""
    contract = {}
    for raw, digest in result['context']['inputs'].items():
        path = Path(raw)
        if path.is_relative_to(workspace):
            name = str(path.relative_to(workspace))
            if name not in selected:
                contract['source/' + name] = digest
        else:
            contract['external/' + raw] = digest
    return contract


def run(workspace: Path, files: list[str], language: str, runtime: Path | None,
        *, baseline_workspace: Path | None = None, project=None, python_executable=None) -> dict:
    def check(root, selected):
        if project or python_executable:
            return full_check(root, selected, language, runtime, project=project, python_executable=python_executable)
        return full_check(root, selected, language, runtime)
    current = check(workspace, files)
    current['mode'] = 'compare' if baseline_workspace is not None else 'full'
    if baseline_workspace is None:
        return current
    current['full_passed'] = current['passed']
    current['passed'] = False
    try:
        baseline_workspace = baseline_workspace.resolve(strict=True)
        if baseline_workspace == workspace or baseline_workspace.is_relative_to(workspace) or workspace.is_relative_to(baseline_workspace):
            raise ValueError('baseline must be an independently selected separate workspace')
        common = [name for name in files if profile.bounded_path(baseline_workspace, name).is_file()]
        added = [name for name in files if name not in common]
        baseline = check(baseline_workspace, common) if common else None
        current['baseline'] = baseline
        if not current['diagnostics_available'] or baseline is not None and not baseline['diagnostics_available']:
            raise ValueError('current/baseline diagnostics unavailable or incompatible; inspect raw checks')
        if baseline is not None:
            if current['tools'] != baseline['tools'] or current['profile_sha256'] != baseline['profile_sha256']:
                raise ValueError('baseline toolchain/profile differs from current')
            if context_contract(current, workspace, files) != context_contract(baseline, baseline_workspace, common):
                raise ValueError('baseline import/config/dependency context differs; full-check the changed context')
        names = set(files) | {item['file'] for item in current['diagnostics']}
        current_sources = {name: profile.bounded_path(workspace, name).read_bytes().decode() for name in names}
        baseline_sources = {name: profile.bounded_path(baseline_workspace, name).read_bytes().decode()
                            for name in names if profile.bounded_path(baseline_workspace, name).is_file()}
        # New files never inherit debt; retain their full diagnostics.
        shared = [item for item in current['diagnostics'] if item['file'] in baseline_sources]
        new = [item for item in current['diagnostics'] if item['file'] not in baseline_sources]
        comparison = compare_diagnostics(shared, baseline['diagnostics'] if baseline else [],
            {name: source for name, source in current_sources.items() if name in baseline_sources}, baseline_sources)
        comparison['new_or_changed'].extend(new)
        comparison['passed'] = not comparison['new_or_changed']
        comparison['new_files_full_checked'] = added
        for root, result in ((workspace, current), (baseline_workspace, baseline)):
            if result is not None and (profile.source_identity(root, list(result['source_after'])) != result['source_after']
                    or any(profile.digest(Path(name)) != digest for name, digest in result['context']['inputs'].items())):
                raise ValueError('inputs changed during baseline comparison')
        current['comparison'] = {'status': 'accepted' if comparison['passed'] else 'failed', **comparison}
        current['baseline_workspace'] = str(baseline_workspace)
        current['passed'] = comparison['passed']
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        current['comparison'] = {'status': 'unavailable', 'reason': str(exc)}
    return current


def discover(workspace, files, language='auto', *, scope='explicit', base=None, source_dir=None):
    load_profile()
    report = {'scope': scope, 'selected': [], 'excluded': [], 'deleted': [], 'unmatched': [],
              'context_failures': [], 'language_mapping': {}}
    if scope == 'explicit':
        if not files or base or source_dir:
            raise ValueError('explicit scope requires files and does not accept --base/--source-dir')
        candidates = files
    elif scope == 'directory':
        if files or base or not source_dir:
            raise ValueError('directory scope requires only --source-dir')
        start = profile.bounded_path(workspace, source_dir)
        if not start.is_dir():
            raise ValueError('source directory does not exist')
        candidates, report['excluded'] = bounded_sources(workspace, set().union(*SUFFIXES.values()), start=start)
    else:
        if files or source_dir or scope == 'changed' and not base or scope == 'tracked' and base:
            raise ValueError('changed requires --base; tracked requires no --base; neither accepts explicit files/source-dir')
        env = profile._workspace_git_environment()
        def git(*argv):
            result = subprocess.run(['git', '--no-optional-locks', '-C', str(workspace), *argv],
                                    capture_output=True, timeout=30, env=env)
            if result.returncode:
                raise ValueError('Git discovery unavailable: ' + result.stderr.decode(errors='replace')[:300])
            return result.stdout
        if Path(os.fsdecode(git('rev-parse', '--show-toplevel')).strip()).resolve() != workspace:
            raise ValueError('Git discovery requires the repository root')
        if scope == 'tracked':
            candidates = [os.fsdecode(name) for name in git('ls-files', '-z').split(b'\0') if name]
        else:
            if base.startswith('-'):
                raise ValueError('base cannot be an option')
            revision = os.fsdecode(git('rev-parse', '--verify', base + '^{commit}')).strip()
            report['base'] = revision
            entries = git('diff', '--no-ext-diff', '--no-textconv', '--name-status', '--no-renames', '-z', revision, '--').split(b'\0')
            candidates = []
            for index in range(0, len(entries) - 1, 2):
                status, name = os.fsdecode(entries[index]), os.fsdecode(entries[index + 1])
                (report['deleted'] if status == 'D' else candidates).append(name)
            candidates.extend(os.fsdecode(name) for name in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if name)
    if scope == 'explicit' and len(set(candidates)) != len(candidates):
        raise ValueError('provide a unique list of files')
    for name in sorted(set(candidates)):
        path = Path(name)
        detected = next((key for key, suffixes in SUFFIXES.items() if path.suffix in suffixes), None)
        if detected is None or language != 'auto' and detected != language:
            report['unmatched'].append(name)
            continue
        if scope != 'explicit' and any(part in EXCLUDED_DIRS for part in path.parts):
            report['excluded'].append({'file': name, 'reason': 'generated/tool directory'})
            continue
        try:
            profile.source_identity(workspace, [name])
        except (OSError, ValueError) as error:
            if not (workspace / name).exists() and not (workspace / name).is_symlink() and scope == 'tracked':
                report['deleted'].append(name)
            else:
                report['context_failures'].append({'file': name, 'reason': str(error)})
            continue
        report['selected'].append(name)
        report['language_mapping'][name] = detected
    if scope == 'explicit' and report['unmatched']:
        report['context_failures'].append({'reason': 'explicit files do not match the supported selected language', 'files': report['unmatched']})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--language', choices=['auto', 'python', 'typescript'], default='auto')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--mode', choices=['full', 'compare'], default='full')
    parser.add_argument('--baseline-workspace', type=Path)
    parser.add_argument('--scope', choices=['explicit', 'changed', 'tracked', 'directory'], default='explicit')
    parser.add_argument('--base')
    parser.add_argument('--source-dir')
    parser.add_argument('--project', help='existing relative TypeScript config; no config is created')
    parser.add_argument('--python-executable', type=Path, help='trusted target interpreter for Python imports')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()
    if (args.mode == 'compare') != (args.baseline_workspace is not None):
        raise ValueError('compare requires --baseline-workspace; full does not accept a baseline')
    workspace = args.workspace.resolve(strict=True)
    if (args.receipt.resolve().is_relative_to(workspace) or (args.baseline_workspace is not None
            and args.receipt.resolve().is_relative_to(args.baseline_workspace.resolve()))):
        raise ValueError('receipt must be outside both current and baseline checkouts')
    if args.runtime and args.baseline_workspace and args.runtime.resolve().is_relative_to(args.baseline_workspace.resolve()):
        raise ValueError('runtime must be outside the baseline workspace')
    with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        try:
            discovery = discover(workspace, args.files, args.language, scope=args.scope, base=args.base, source_dir=args.source_dir)
            grouped = {language: [name for name in discovery['selected'] if discovery['language_mapping'][name] == language]
                       for language in SUFFIXES}
            results = [run(workspace, selected, language, args.runtime, baseline_workspace=args.baseline_workspace,
                           project=args.project, python_executable=args.python_executable)
                       for language, selected in grouped.items() if selected]
            if len(results) == 1:
                result = results[0]
            else:
                result = {'version': 2, 'language': 'auto', 'results': results,
                          'passed': bool(results) and all(item['passed'] for item in results)}
            result['discovery'] = discovery
            result['passed'] = result['passed'] and not discovery['context_failures']
            if not discovery['selected']:
                result['unavailable'] = 'no supported files selected; discovery is reported but no check passed'
        except (OSError, ValueError, KeyError, subprocess.SubprocessError, tokenize.TokenError) as error:
            result = {'version': 2, 'passed': False, 'unavailable': str(error)}
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
