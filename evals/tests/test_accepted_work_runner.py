"""A completed process does not establish available acceptance instrumentation."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/accepted-work-eval.py'


class AcceptedRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('accepted_runner', SCRIPT)
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def row(self, behavior=1, scope=1):
        return {'behavioral_gate': behavior, 'scope_gate': scope,
                'score_metadata': {}, 'observations': {}, 'error': None}

    def test_unavailable_gates_stop_and_behavioral_failures_continue(self):
        self.assertFalse(self.runner.infrastructure_failure(self.row(behavior=0)))
        self.assertFalse(self.runner.infrastructure_failure(self.row(scope=0)))
        self.assertTrue(self.runner.infrastructure_failure(self.row(behavior=None)))
        self.assertTrue(self.runner.infrastructure_failure(self.row(scope=float('nan'))))

    def test_blocker_metadata_and_unavailable_receipts_stop(self):
        for metadata in [{'acceptance_blocked': True}, {'instrumentation_blocker': True}]:
            row = self.row()
            row['score_metadata']['workflow_effects'] = metadata
            self.assertTrue(self.runner.infrastructure_failure(row))
        row = self.row()
        row['observations']['acceptance_groups'] = {'failure': {'exit_code': None, 'execution_error': 'timeout'}}
        self.assertTrue(self.runner.infrastructure_failure(row))
        row['observations']['acceptance_groups']['failure'] = {'exit_code': 1}
        self.assertFalse(self.runner.infrastructure_failure(row))

    def test_strict_json_unknown_not_a_numeric_success(self):
        self.assertEqual(self.runner.json_safe({'unknown': float('nan'), 'pass': 1}), {'unknown': None, 'pass': 1})

    def test_parent_ledgers_count_invalidated_attempts_once(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            results = root / 'evals/results'
            directories = [results / name for name in ['invalid', 'corrected', 'final']]
            for directory, count in zip(directories, [10, 4, 18], strict=True):
                directory.mkdir(parents=True)
                (directory / 'launches.json').write_text(json.dumps([{'status': 'started'}] * count))
                parents = [{'directory': str(parent)} for parent in directories if parent != directory and parent.exists()]
                (directory / 'protocol.json').write_text(json.dumps({'prior_runs': parents}))
            with patch.object(self.runner, 'ROOT', root):
                records = self.runner.prior_run_records([directories[-1], directories[0]])
                self.assertEqual(sum(record['attempted_sessions'] for record in records), 32)
                self.assertEqual(len(records), 3)
                with self.assertRaises(ValueError):
                    self.runner.prior_run_records([root / 'outside'])

    def test_counterbalanced_finalists_and_untouched_holdout_schedule(self):
        plan = json.loads((SCRIPT.parents[1] / 'evals/accepted-work-plan.json').read_text())
        for stage, count, split in [('calibration', 18, 'development'),
                                    ('finalists', 12, 'development'), ('holdout', 4, 'holdout')]:
            blocks, actual_split, budget_key = self.runner.launch_blocks(plan, stage, 'conditional')
            self.assertEqual(sum(len(arms) for _, arms in blocks), count)
            self.assertEqual(actual_split, split)
            self.assertLessEqual(count, plan['budget'][budget_key])
            self.assertEqual([case for case, _ in blocks], plan['cases'][split])
            if stage != 'calibration':
                self.assertEqual(blocks[0][1], ['baseline', 'conditional'])
                self.assertEqual(blocks[1][1], ['conditional', 'baseline'])
        with self.assertRaises(ValueError):
            self.runner.launch_blocks(plan, 'holdout', None)

    def test_unknown_quality_gates_cannot_qualify_expansion(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            samples = root / 'samples.json'
            samples.write_text('[]')
            record = {'samples_sha256': hashlib.sha256(samples.read_bytes()).hexdigest(),
                      'reviewer': 'model-free test fixture', 'evidence': ['fixture artifact review'],
                      'gates': {gate: True for gate in ('scope_preserved', 'no_added_security_regression',
                          'accepted_artifacts_maintainable', 'claims_truthful', 'no_accepted_task_regression')}}
            path = root / 'adjudication.json'
            path.write_text(json.dumps(record))
            self.assertEqual(self.runner.require_adjudication(root), path)
            record['gates']['claims_truthful'] = None
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                self.runner.require_adjudication(root)
            record['gates']['claims_truthful'] = True
            path.write_text(json.dumps(record))
            samples.write_text('[{"changed":true}]')
            with self.assertRaises(ValueError):
                self.runner.require_adjudication(root)

    def test_changed_executable_or_dependency_stops_before_candidate_launch(self):
        from evals import skills
        plan = json.loads((SCRIPT.parents[1] / 'evals/accepted-work-plan.json').read_text())
        for defect in ('executable_path', 'dependency_bytes'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                preceding = root / 'evals/results/calibration'
                preceding.mkdir(parents=True)
                (root / 'evals/accepted-work-plan.json').write_text(json.dumps(plan))
                executable = root / 'candidate-elf'
                executable.write_text('test executable identity')
                lock = root / 'uv.lock'
                lock.write_text('old lock')
                earlier = {'stage': 'calibration', 'status': 'calibration-complete',
                           'model': 'frozen', 'effort': 'low', 'runtime': str(root / 'runtime'),
                           'candidate_binary': str(executable),
                           'hashes': self.runner.hashes([executable, lock])}
                (preceding / 'protocol.json').write_text(json.dumps(earlier))
                (preceding / 'launches.json').write_text(json.dumps([{}] * 18))
                selected = executable
                if defect == 'executable_path':
                    selected = root / 'different-elf'
                else:
                    lock.write_text('changed lock')
                argv = ['accepted-work-eval', str(root / 'evals/results/finalists'),
                        '--model', 'frozen', '--effort', 'low', '--runtime', str(root / 'runtime'),
                        '--stage', 'finalists', '--finalist', 'conditional', '--prior-run', str(preceding)]
                with patch.object(self.runner, 'ROOT', root), patch.object(sys, 'argv', argv), \
                     patch.object(skills, '_validate_tool_runtime', return_value=root / 'runtime'), \
                     patch.object(skills, '_native_codex_binary', return_value=selected), \
                     patch.object(self.runner.subprocess, 'run') as launch:
                    with self.assertRaises(SystemExit) as caught:
                        self.runner.main()
                    self.assertEqual(caught.exception.code, 2)
                    launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
