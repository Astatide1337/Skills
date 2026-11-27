"""Each case's hidden checks must fail on the untouched project and pass with the reference fix.

This validates the instrument without Docker or a model: a check that passes on the
starting repo measures nothing, and one that rejects the reference fix is too strict.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

CASES = Path(__file__).resolve().parents[1] / "cases"
CASE_DIRS = sorted(d for d in CASES.iterdir() if (d / "case.yaml").is_file())


def prepare(case_dir: Path, home: Path) -> tuple[dict, Path, dict]:
    case = yaml.safe_load((case_dir / "case.yaml").read_text())
    project = home / case["project"]
    shutil.copytree(case_dir / "repo", project)
    if (case_dir / "checks").is_dir():
        shutil.copytree(case_dir / "checks", home / ".grader")
    env = {
        **os.environ,
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    script = f"{case.get('setup', '')}\ngit init -q && git add -A && git commit -qm 'initial import'"
    subprocess.run(
        ["bash", "-c", script], cwd=project, env=env, check=True, capture_output=True
    )
    return case, project, env


def failing_checks(case: dict, project: Path, env: dict) -> list[str]:
    failed = []
    for check in case.get("checks", []):
        result = subprocess.run(
            ["bash", "-c", check["run"]],
            cwd=project,
            env=env,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            failed.append(check["name"])
    return failed


class AutonomousCaseTests(unittest.TestCase):
    def test_cases_exist(self):
        self.assertGreaterEqual(len(CASE_DIRS), 1)

    def test_checks_discriminate(self):
        for case_dir in CASE_DIRS:
            with self.subTest(case=case_dir.name), tempfile.TemporaryDirectory() as tmp:
                case, project, env = prepare(case_dir, Path(tmp))
                for key in ("project", "brief", "checks", "assertions"):
                    self.assertIn(key, case)
                self.assertTrue(
                    failing_checks(case, project, env),
                    "no hidden check fails on the untouched project",
                )
                subprocess.run(
                    ["git", "apply", str(case_dir / "reference.patch")],
                    cwd=project,
                    check=True,
                )
                self.assertEqual(
                    failing_checks(case, project, env),
                    [],
                    "reference fix fails a hidden check",
                )


if __name__ == "__main__":
    unittest.main()
