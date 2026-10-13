#!/usr/bin/env python3
"""Freeze and run the bounded accepted-work calibration on the existing harness.

Run with uv run python scripts/accepted-work-eval.py OUTPUT --model MODEL
--effort low --runtime /absolute/owned/lint-runtime. OUTPUT must be a new ignored
results directory. Each launch is recorded before execution; failures stop the
batch and are never overwritten. Finalist/holdout expansion requires review of
calibration and retained gate adjudication, rather than automatic tuning. Use
--stage finalists --finalist conditional --prior-run CALIBRATION to repeat the
paired development cases, then --stage holdout against the unchanged holdouts.
Prior-run ancestors, including invalidated attempts, consume the original cap.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths) if p.is_file()}


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def infrastructure_failure(row):
    if row['error'] or row['behavioral_gate'] not in (0, 1) or row['scope_gate'] not in (0, 1):
        return True
    for metadata in row['score_metadata'].values():
        if metadata and (metadata.get('acceptance_blocked') or metadata.get('instrumentation_blocker')):
            return True
    if any("can't create temp file for here document" in c.get('aggregated_output', '')
           for c in (row['observations'].get('tool_evidence') or {}).get('completed_commands', [])):
        return True
    return any(receipt.get('exit_code') is None or receipt.get('execution_error')
               for receipt in row['observations'].get('acceptance_groups', {}).values())


def prior_run_records(paths):
    """Count each retained ancestor once, including invalidated and interrupted runs."""
    pending = [path.resolve() for path in paths]
    records = {}
    while pending:
        directory = pending.pop()
        if directory in records:
            continue
        if not directory.is_relative_to(ROOT / 'evals/results'):
            raise ValueError('prior runs must be retained local results')
        ledger = directory / 'launches.json'
        attempts = json.loads(ledger.read_text())
        if not isinstance(attempts, list):
            raise TypeError('prior run ledger must be an array of attempted launches')
        protocol = json.loads((directory / 'protocol.json').read_text())
        records[directory] = {'directory': str(directory), 'attempted_sessions': len(attempts),
                              'ledger_sha256': hashlib.sha256(ledger.read_bytes()).hexdigest()}
        pending.extend(Path(parent['directory']).resolve() for parent in protocol.get('prior_runs', []))
    return list(records.values())


def require_adjudication(directory):
    """Supplemental gates require retained review, never command-count proxies."""
    path = directory / 'adjudication.json'
    record = json.loads(path.read_text())
    digest = hashlib.sha256((directory / 'samples.json').read_bytes()).hexdigest()
    gates = ('scope_preserved', 'no_added_security_regression',
             'accepted_artifacts_maintainable', 'claims_truthful', 'no_accepted_task_regression')
    if record.get('samples_sha256') != digest or not record.get('reviewer') or not record.get('evidence'):
        raise ValueError('adjudication must identify reviewed samples, reviewer and evidence')
    if any(record.get('gates', {}).get(gate) is not True for gate in gates):
        raise ValueError('unknown or failed supplemental quality gate prevents expansion')
    return path


def launch_blocks(protocol, stage, finalist):
    if stage == 'calibration':
        cases = protocol['cases']['development']
        return [(case, protocol['orders'][index % len(protocol['orders'])])
                for index, case in enumerate(cases)], 'development', 'calibration_calls'
    if finalist not in ('available', 'conditional'):
        raise ValueError('finalist or holdout stage needs an explicit available/conditional finalist')
    split = 'holdout' if stage == 'holdout' else 'development'
    cases = protocol['cases'][split]
    arms = ['baseline', finalist]
    return [(case, arms if index % 2 == 0 else arms[::-1]) for index, case in enumerate(cases)], split, ('conditional_holdout_calls' if stage == 'holdout' else 'conditional_finalist_calls')


def summarize(directory, protocol):
    from inspect_ai.log import read_eval_log
    rows = []
    for launch in json.loads((directory / 'launches.json').read_text()):
        for path in sorted((directory / launch['label']).glob('*.eval')):
            log = read_eval_log(path)
            for sample in log.samples or []:
                scores = sample.scores or {}
                obs = scores.get('engineering_observations')
                obs = obs.metadata if obs else {}
                tool = obs.get('tool_evidence') or {}
                commands = tool.get('completed_commands', [])
                invocations = [c for c in commands if re.search(r'portable_lint\.py[^;\n]*--workspace', c.get('command', ''))]
                rows.append({
                    'case': sample.id, 'family': protocol['families'][sample.id],
                    'arm': launch['arm'], 'log': str(path),
                    'scores': {k: v.value for k, v in scores.items()},
                    'score_metadata': {k: v.metadata for k, v in scores.items()},
                    'behavioral_gate': scores.get('workflow_effects').value if scores.get('workflow_effects') else None,
                    'scope_gate': scores.get('workspace_policy').value if scores.get('workspace_policy') else None,
                    'observations': obs, 'invocations': invocations,
                    'direct_checker_commands': [c for c in commands if re.search(r'(-m\s+(ruff|mypy)\b|/(ruff|mypy)\s)', c.get('command', ''))],
                    'sample_elapsed_seconds': sample.total_time,
                    'error': sample.error.model_dump() if sample.error else None,
                    'human_acceptance': None, 'human_active_minutes': None,
                    'human_interventions': None, 'request_to_acceptance_seconds': None,
                    'billed_currency_cost': None,
                    'mechanism_adjudication': None,
                    'mechanism_note': 'Diagnostic -> decision -> artifact -> outcome needs trace/artifact adjudication; invocation is not benefit.',
                })
    (directory / 'samples.json').write_text(json.dumps(json_safe(rows), indent=2, allow_nan=False) + '\n')
    aggregate = {}
    for arm in protocol['arms']:
        selected = [r for r in rows if r['arm'] == arm]
        aggregate[arm] = {
            'samples': len(selected),
            'behavior_and_scope_passes': sum(r['behavioral_gate'] == 1 and r['scope_gate'] == 1 and not r['error'] for r in selected),
            'sample_elapsed_sum_seconds': sum(r['sample_elapsed_seconds'] for r in selected),
            'invocations': sum(len(r['invocations']) for r in selected),
            'direct_checker_commands': sum(len(r['direct_checker_commands']) for r in selected),
            'families': {family: [r['case'] for r in selected if r['family'] == family]
                         for family in sorted({r['family'] for r in selected})},
        }
    (directory / 'aggregate.json').write_text(json.dumps(aggregate, indent=2) + '\n')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh'])
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--stage', choices=['calibration', 'finalists', 'holdout'], default='calibration')
    parser.add_argument('--finalist', choices=['available', 'conditional'])
    parser.add_argument('--prior-run', type=Path, action='append', default=[],
                        help='Earlier run directories whose attempted sessions count against the overall cap')
    args = parser.parse_args()
    directory = args.output.resolve()
    if not directory.is_relative_to(ROOT / 'evals/results') or directory.exists():
        parser.error('output must be a new directory inside ignored evals/results')
    from evals.skills import (
        _native_codex_binary,
        _skills_identity,
        _validate_tool_runtime,
    )
    runtime = _validate_tool_runtime(args.runtime)
    protocol = json.loads((ROOT / 'evals/accepted-work-plan.json').read_text())
    blocks, split, budget_key = launch_blocks(protocol, args.stage, args.finalist)
    calls = sum(len(arms) for _, arms in blocks)
    if calls > protocol['budget'][budget_key]:
        parser.error('declared stage exceeds frozen call budget')
    prior_runs = prior_run_records(args.prior_run)
    prior_attempts = sum(run['attempted_sessions'] for run in prior_runs)
    remaining = protocol['budget']['maximum_calls'] - prior_attempts - calls
    if remaining < 0:
        parser.error('cumulative attempted sessions exceed original maximum budget')
    if args.stage != 'calibration':
        if not args.prior_run:
            parser.error('expansion needs a completed preceding stage')
        preceding = args.prior_run[-1].resolve()
        earlier = json.loads((preceding / 'protocol.json').read_text())
        expected = 'calibration' if args.stage == 'finalists' else 'finalists'
        if not earlier.get('stage', '').startswith(expected) or not earlier.get('status', '').startswith(expected + '-complete'):
            parser.error('preceding stage is not complete and eligible')
        for key, value in [('model', args.model), ('effort', args.effort), ('runtime', str(runtime)),
                           ('candidate_binary', str(_native_codex_binary()))]:
            if earlier.get(key) != value:
                parser.error('expansion must retain frozen model, effort and runtime')
        source_inputs = {name: value for name, value in earlier['hashes'].items()
                         if not Path(name).is_relative_to(ROOT / 'evals/results')}
        if hashes(Path(name) for name in source_inputs) != source_inputs:
            parser.error('frozen runner, graders, executable or dependencies changed since preceding stage')
        if _skills_identity(preceding / 'snapshot/skills') != _skills_identity(ROOT / 'skills'):
            parser.error('catalog changed since preceding stage')
        if (preceding / 'snapshot/AGENTS.md').read_bytes() != (ROOT / 'global-instructions/AGENTS.md').read_bytes():
            parser.error('globals changed since preceding stage')
        adjudication = require_adjudication(preceding)
        aggregate = json.loads((preceding / 'aggregate.json').read_text())
        baseline = aggregate['baseline']
        candidate = aggregate[args.finalist]
        if expected == 'finalists' and earlier.get('finalist') != args.finalist:
            parser.error('holdout must retain the repeated finalist')
        if baseline['samples'] != len(protocol['cases']['development']) or candidate['samples'] != baseline['samples']:
            parser.error('preceding comparison is incomplete')
        if expected == 'calibration' and baseline['behavior_and_scope_passes'] == baseline['samples']:
            parser.error('baseline saturated; stop rather than expand')
        gain = candidate['behavior_and_scope_passes'] > baseline['behavior_and_scope_passes']
        faster = (candidate['behavior_and_scope_passes'] > 0
                  and candidate['behavior_and_scope_passes'] >= baseline['behavior_and_scope_passes']
                  and candidate['sample_elapsed_sum_seconds'] <= .8 * baseline['sample_elapsed_sum_seconds'])
        if not gain and not faster:
            parser.error('no predeclared useful signal; stop rather than expand')
    protocol.update(prior_runs=prior_runs, prior_attempted_sessions=prior_attempts,
                    cumulative_calibration_sessions=prior_attempts + calls,
                    expansion_sessions_remaining=remaining,
                    expansion='Original finalist allocations are unavailable when prior attempts consume them; separately freeze a plan within the remaining cap.')
    directory.mkdir(parents=True, mode=0o700)
    with (directory / 'calibration.txt').open('w') as output:
        calibrated = subprocess.run(['uv', 'run', 'python', '-m', 'unittest',
            'evals.tests.test_accepted_work', 'evals.tests.test_engineering_cases',
            'evals.tests.test_review_cases', 'evals.tests.test_accepted_work_runner'],
            cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=False)
    if calibrated.returncode:
        raise RuntimeError('grader calibration failed; no candidate calls launched')
    snapshot = directory / 'snapshot'
    shutil.copytree(ROOT / 'skills', snapshot / 'skills')
    shutil.copyfile(ROOT / 'global-instructions/AGENTS.md', snapshot / 'AGENTS.md')
    frozen_paths = [*snapshot.rglob('*'), * (ROOT / 'evals').glob('*.py'),
                    * (ROOT / 'evals/cases').glob('*.json'),
                    * (ROOT / 'evals').glob('*.json'), * (ROOT / 'evals/tests').glob('*.py'),
                    ROOT / 'evals/accepted-work-plan.json', Path(__file__).resolve(),
                    ROOT / 'uv.lock', ROOT / 'pyproject.toml', runtime / 'skills-portable-lint.json', _native_codex_binary()]
    if args.stage != 'calibration':
        frozen_paths.append(adjudication)
    protocol.update(model=args.model, effort=args.effort, runtime=str(runtime), hashes=hashes(frozen_paths),
                    source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    candidate_binary=str(_native_codex_binary()),
                    stage=args.stage, finalist=args.finalist, started_at=time.time())
    (directory / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    launches = []
    for index, (case, order) in enumerate(blocks):
        for arm in order:
            if hashes(Path(p) for p in protocol['hashes']) != protocol['hashes']:
                raise RuntimeError('frozen inputs changed; stop and retain attempts')
            label = f'{index + 1:02d}-{arm}'
            command = ['uv', 'run', 'inspect', 'eval', 'evals/skills.py@accepted_workflows',
                '--model', 'mockllm/model', '--epochs', '1', '--max-samples', '1', '--max-tasks', '1',
                '--time-limit', str(protocol['budget']['per_sample_seconds']), '--log-dir', str(directory / label),
                '-T', 'native_model=' + args.model, '-T', 'native_effort=' + args.effort,
                '-T', 'tool_mode=' + arm, '-T', 'tool_runtime=' + str(runtime),
                '-T', 'skills_root=' + str(snapshot / 'skills'), '-T', 'global_instructions=' + str(snapshot / 'AGENTS.md'),
                '-T', 'split=' + split, '-T', 'case_ids=' + json.dumps([case])]
            launches.append({'label': label, 'case': case, 'arm': arm, 'command': command, 'status': 'started', 'started_at': time.time()})
            (directory / 'launches.json').write_text(json.dumps(launches, indent=2) + '\n')
            print(f'Start {label} {case}', flush=True)
            with (directory / (label + '.txt')).open('w') as output:
                result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=False)
            launches[-1].update(status='completed', exit_code=result.returncode, completed_at=time.time())
            (directory / 'launches.json').write_text(json.dumps(launches, indent=2) + '\n')
            rows = summarize(directory, protocol)
            print(f'Finish {label}: exit {result.returncode}', flush=True)
            if result.returncode or any(infrastructure_failure(r) for r in rows):
                raise RuntimeError('infrastructure/candidate error; retain failures and inspect before further calls')
    protocol.update(completed_at=time.time(), status=args.stage + '-complete-no-automatic-promotion')
    (directory / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')


if __name__ == '__main__':
    # Direct script execution normally places scripts/, not the repository, on sys.path.
    import sys
    sys.path.insert(0, str(ROOT))
    main()
