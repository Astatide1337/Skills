"""Validate each case's hidden checks without Docker or a model.

Checks must fail on the untouched project, pass with `reference.patch` and every
`alternatives/*.patch` (other valid fixes), and fail with every `defects/*.patch`.
A check that passes on the starting repo measures nothing; one that rejects a valid
fix is too strict; one that accepts a planted defect is too loose.
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
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    env["BASE_SHA"] = (
        head.stdout.strip()
    )  # the runner exports the starting commit the same way
    return case, project, env


def failing_after(case_dir: Path, patch: Path | None) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        case, project, env = prepare(case_dir, Path(tmp))
        if patch is not None:
            subprocess.run(["git", "apply", str(patch)], cwd=project, check=True)
        return failing_checks(case, project, env)


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
            with self.subTest(case=case_dir.name):
                case = yaml.safe_load((case_dir / "case.yaml").read_text())
                for key in ("project", "brief", "checks", "assertions"):
                    self.assertIn(key, case)
                self.assertTrue(
                    failing_after(case_dir, None),
                    "no hidden check fails on the untouched project",
                )
                for patch in [
                    case_dir / "reference.patch",
                    *sorted(case_dir.glob("alternatives/*.patch")),
                ]:
                    self.assertEqual(
                        failing_after(case_dir, patch),
                        [],
                        f"{patch.name} is valid but fails a check",
                    )
                for patch in sorted(case_dir.glob("defects/*.patch")):
                    self.assertTrue(
                        failing_after(case_dir, patch),
                        f"{patch.name} is a defect but passes every check",
                    )


if __name__ == "__main__":
    unittest.main()
