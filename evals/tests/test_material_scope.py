"""Behavioral acceptance controls for an essential public-format decision."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from evals import skills

IDS = [
    "issue-38-public-format-unresolved",
    "issue-38-public-format-settled",
    "issue-38-public-format-open-choice",
]
GOOD = """import tomllib
from pathlib import Path
def load(path):
    values=tomllib.loads(Path(path).read_text())
    if not isinstance(values.get('host'),str) or type(values.get('port')) is not int:
        raise ValueError('host and port types')
    return {'host':values['host'],'port':values['port']}
"""


class MaterialScopeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {s.id: s for s in skills.workflows_dataset(case_ids=IDS).samples}

    def run_control(self, case_id, code, settings='host = "localhost"\nport = 8080\n'):
        c = self.cases[case_id]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for n, v in c.files.items():
                (root / n).write_text(v)
            (root / "loader.py").write_text(code)
            (root / "settings.conf").write_text(settings)
            command, error = skills._runner_acceptance_command(
                c.metadata["fixture_contract"]
            )
            self.assertIsNone(error)
            return subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

    def test_valid_parser_alternatives_pass_both_twins(self):
        alternative = GOOD.replace(
            "values=tomllib.loads(Path(path).read_text())",
            "with open(path,'rb') as source: values=tomllib.load(source)",
        )
        for case in IDS:
            for code in (GOOD, alternative):
                with self.subTest(case=case, code=code):
                    r = self.run_control(case, code)
                    self.assertEqual(r.returncode, 0, r.stderr)

    def test_constant_output_is_not_a_working_format_migration(self):
        for case in IDS:
            r = self.run_control(
                case, "def load(path): return {'host':'localhost','port':8080}\n"
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("new public format not supported", r.stderr)

    def test_numeric_string_conversion_preserves_output_contract(self):
        coercing = GOOD.replace(
            "    if not isinstance(values.get('host'),str)",
            "    if isinstance(values.get('port'),str): values['port']=int(values['port'])\n"
            "    if not isinstance(values.get('host'),str)",
        )
        for case in IDS:
            result = self.run_control(
                case, coercing, 'host = "localhost"\nport = "8080"\n'
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_old_parser_is_rejected(self):
        for case in IDS:
            c = self.cases[case]
            r = self.run_control(case, c.files["loader.py"], c.files["settings.conf"])
            self.assertNotEqual(r.returncode, 0)

    def test_toml_without_existing_field_types_is_rejected(self):
        code = "import tomllib\nfrom pathlib import Path\ndef load(path): return tomllib.loads(Path(path).read_text())\n"
        for case in IDS:
            r = self.run_control(case, code)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("CLI field-type contract lost", r.stderr)

    def test_unresolved_cases_have_predecision_gate(self):
        settled = self.cases[IDS[1]].metadata
        self.assertNotIn("user_turns", settled)
        for case_id in (IDS[0], IDS[2]):
            unknown = self.cases[case_id].metadata
            self.assertEqual(
                unknown["user_turns"][0]["allowed_paths_before"],
                ["test_regressions.py"],
            )
            self.assertIsNone(skills._user_turns_contract_error(unknown))
