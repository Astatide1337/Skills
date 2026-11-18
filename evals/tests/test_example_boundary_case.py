"""Exercise the boundary fixture's hidden controls on flawed and valid project gates."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.skills import _runner_acceptance_command


SCAN = """import ast
import sys
from pathlib import Path

for path in Path("screens").rglob("*.py"):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            modules = [node.module]
        elif isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        else:
            continue
        if "lowlevel" in modules:
            sys.exit(f"{path}: use public_api.label")
"""


class ExampleBoundaryCase(unittest.TestCase):
    def test_independent_screen_and_job_controls(self):
        cases = Path(__file__).resolve().parents[1] / "cases/skills-comparison.json"
        case = next(row for row in json.loads(cases.read_text())
                    if row["id"] == "examples-screen-import-boundary")
        command, error = _runner_acceptance_command(
            case["metadata"]["fixture_contract"], completion_marker="COMPLETE")
        self.assertIsNone(error)
        direct = "from public_api import label as display\n"
        wrapped = "import public_api\n\ndef display(value):\n    return public_api.label(value)\n"
        original = case["files"]["screens/listing.py"]
        for label, gate, screen, accepted in [
            ("valid alias", SCAN, direct, True),
            ("valid wrapper", SCAN, wrapped, True),
            ("still copies normalization", SCAN, "def display(v): return v.strip().casefold()", False),
            ("old production example", SCAN, original, False),
            ("cleanup alone", case["files"]["check.py"], direct, False),
            ("message lacks repair", SCAN.replace("use public_api.label", "bad import"), direct, False),
            ("outlaws legitimate jobs", SCAN.replace('Path("screens")', 'Path(".")'), direct, False),
            ("from imports only", SCAN.replace("ast.Import):", "ast.ImportFrom):"), direct, False),
        ]:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                tree = Path(temp)
                files = {**case["files"], "check.py": gate, "screens/listing.py": direct,
                         "screens/detail.py": screen}
                for name, content in files.items():
                    path = tree / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                result = subprocess.run([sys.executable, *command[1:]], cwd=tree, text=True,
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode == 0 and "COMPLETE" in result.stdout.splitlines(),
                                 accepted, msg=result.stderr)
