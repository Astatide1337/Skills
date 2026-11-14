"""Structural contracts: valid alternatives and targeted failures, without models."""
import importlib.util
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/agent-contracts/scripts/validate_spec.py'
loader = importlib.util.spec_from_file_location('validate_spec', SCRIPT)
module = importlib.util.module_from_spec(loader)
loader.loader.exec_module(module)
TEMPLATE = (ROOT / 'skills/agent-contracts/references/contract.md').read_text()
DRAFT = re.search(r'```markdown\n(.*?)\n```', TEMPLATE, re.DOTALL)[1]


class ContractTests(unittest.TestCase):
    def test_installed_documented_command_from_another_project(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / 'installed skills'
            result = subprocess.run(['bash', str(ROOT / 'scripts/install.sh'),
                                     '--skill', 'agent-contracts', '--target', str(target)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            skill = target / 'agent-contracts'
            documented = re.search(r'```sh\n(.*?)\n```', (skill / 'SKILL.md').read_text(), re.DOTALL)[1]
            spec = root / 'draft.md'
            spec.write_text(DRAFT)
            command = shlex.split(documented.replace('<skill-dir>', str(skill))
                                  .replace('/absolute/private/spec.md', str(spec)))
            command[0] = sys.executable
            project = root / 'another-project'
            project.mkdir()
            result = subprocess.run(command, cwd=project, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid_structure'])

    def test_id_mentions_and_hyphenated_prose_are_not_declarations(self):
        for sentence in ('A-01 was refuted; R-01 paused.',
                         'AC-01 reported-pass at abc123.', 'A-frame layout is reused.'):
            with self.subTest(sentence=sentence):
                self.assertTrue(module.validate(DRAFT + '\n' + sentence)['valid_structure'])

    def test_diagnostics_keep_source_line_numbers_after_fences(self):
        draft = DRAFT + '\n```text\nexample\n```\nR-1: invalid\n'
        expected_line = draft.splitlines().index('R-1: invalid') + 1
        self.assertIn(f'malformed declaration at source line {expected_line}', module.validate(draft)['errors'])

    def test_scaffolding_alone_does_not_fill_a_section(self):
        for content in ('-', '*', '---', '* * *', '- - -', '_ _ _', '<!-- TODO -->', '### TBD',
                        '<!-- multi\nline -->\n*\n---'):
            draft = re.sub(r'(?<=## SCOPE\n).*?(?=\n## AUTHORITY)', content + '\n', DRAFT, flags=re.DOTALL)
            with self.subTest(content=content):
                self.assertIn('empty section SCOPE', module.validate(draft)['errors'])
        draft = DRAFT.replace('## SCOPE\n', '## SCOPE\n<!-- note -->\n### Details\n')
        self.assertTrue(module.validate(draft)['valid_structure'])

    def test_unresolved_and_refuted_are_documented_states(self):
        for status in ('unresolved', 'refuted', 'verified'):
            result = module.validate(DRAFT.replace('status=unresolved', 'status=' + status))
            self.assertTrue(result['valid_structure'], result)
            self.assertEqual(len(result['diagnostics']), int(status != 'verified'))
            if result['diagnostics']:
                self.assertEqual(result['diagnostics'][0]['affected_requirements'], '@R-01')

    def test_alternate_markdown_and_wording(self):
        alternate = DRAFT.replace('condition=when remote verification is available',
                                  'condition=on receipt of a supported request')
        alternate = alternate.replace('R-01:', '* R-01:').replace('A-01:', '+ A-01:')
        alternate = alternate.replace('AC-01:', '- AC-01:').replace('Score: 6', '- Score: 8')
        alternate += '\n### Notes\nA different design satisfies **@R-01**.\n'
        self.assertTrue(module.validate(alternate)['valid_structure'])

    def test_targeted_structural_defects(self):
        defects = [
            DRAFT.replace('## DESIGN', '## DESIGN MISSING'),
            DRAFT.replace('Owner: integrating agent\n', ''),
            DRAFT.replace('Spec: PERSONAL-ADAPTER', 'Spec: PERSONAL-ADAPTER\nSpec: other'),
            DRAFT.replace('R-01:', 'R-1:'),
            DRAFT.replace('source=accepted request', 'source='),
            DRAFT.replace('source=accepted request', 'source=request | source=conflicting'),
            DRAFT.replace('status=unresolved', 'status=probably'),
            DRAFT.replace('Assigned: @R-01', 'Assigned: @R-99'),
            DRAFT.replace('acceptance=@AC-01', 'acceptance=@AC-99'),
            DRAFT.replace('assumptions=@A-01', 'assumptions=@A-99'),
            DRAFT.replace('assumptions=@A-01', 'assumptions=none'),
            DRAFT.replace('R-01:', 'R-01: condition=conflict\nR-01:', 1),
            DRAFT.replace('A-01:', 'A-01: status=refuted\nA-01:', 1),
            DRAFT.replace('AC-01:', 'AC-01: expected=conflict\nAC-01:', 1),
        ]
        for draft in defects:
            with self.subTest(draft=draft):
                self.assertFalse(module.validate(draft)['valid_structure'])

    def test_score_domain(self):
        for score in ('true', 'false', '6.5', '0', '11', '-1', '1/2'):
            with self.subTest(score=score):
                self.assertFalse(module.validate(DRAFT.replace('Score: 6', 'Score: ' + score))['valid_structure'])
        for score in range(1, 11):
            self.assertTrue(module.validate(DRAFT.replace('Score: 6', f'Score: {score}'))['valid_structure'])

    def test_fenced_declarations_cannot_supply_missing_contract(self):
        for fence in ('```', '~~~~'):
            hidden = re.sub(r'^(R-01:.*)$', fence + '\n' + r'\1' + '\n' + fence, DRAFT, flags=re.MULTILINE)
            self.assertFalse(module.validate(hidden)['valid_structure'])
            example = f'\n{fence}markdown\n## BAD\nR-1: bad\n@A-99\n{fence}\n'
            self.assertTrue(module.validate(DRAFT + example)['valid_structure'])

    def test_no_assumptions_and_multiple_references(self):
        draft = re.sub(r'^A-01:.*$', 'No material assumptions: isolated pure transformation.', DRAFT, flags=re.MULTILINE)
        draft = draft.replace('assumptions=@A-01', 'assumptions=none')
        self.assertTrue(module.validate(draft)['valid_structure'])
        declaration = next(line for line in DRAFT.splitlines() if line.startswith('R-01:'))
        draft = DRAFT.replace(declaration, declaration + '\n' + declaration.replace('R-01:', 'R-02:'))
        draft = draft.replace('affects=@R-01', 'affects=@R-01, @R-02')
        draft = draft.replace('requirements=@R-01', 'requirements=@R-01 @R-02')
        self.assertTrue(module.validate(draft)['valid_structure'])

    def test_cli_exit_and_input_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'spec.md'
            for content, expected in ((DRAFT, 0), (DRAFT.replace('Score: 6', 'Score: true'), 1)):
                path.write_text(content)
                before = path.read_bytes()
                result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(result.stdout)['valid_structure'], expected == 0)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(raw).iterdir()), [path])
            path.unlink()
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)

    def test_cases_load_and_primary_is_unique(self):
        catalog = json.loads((ROOT / 'evals/cases/catalog.json').read_text())
        self.assertEqual(sum(c['metadata'].get('skill') == 'agent-contracts' for c in catalog), 1)
        cases = json.loads((ROOT / 'evals/cases/workflows.json').read_text())
        selected = {c['id']: c for c in cases if c['id'].startswith('workflow-contract-')}
        self.assertEqual(len(selected), 3)
        self.assertIn('agent-contracts', selected['workflow-contract-full']['metadata']['expected_skills'])
        self.assertIn('agent-contracts', selected['workflow-contract-tiny']['metadata']['forbidden_skills'])
        self.assertIn('accepted alternatives', selected['workflow-contract-missing-check']['target'])
