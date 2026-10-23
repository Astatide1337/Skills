"""Agent gates: the stop hook and integrity check fail on real shortcut patterns."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "global-instructions" / "hooks"
GATES = HOOKS / "agent_gates.py"
INTEGRITY = HOOKS / "test_integrity.py"

JS_TESTS = (
    "import { it } from 'vitest';\nit('adds', () => {});\nit('subtracts', () => {});\n"
)
PY_TESTS = "def test_create():\n    pass\n\ndef test_delete():\n    pass\n"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class Repo:
    """A disposable repository with one commit containing the given files."""

    def __init__(self, root: Path, files: dict[str, str]):
        self.path = root / "app"
        self.path.mkdir()
        git(self.path, "init", "-q", "-b", "main")
        git(self.path, "config", "user.email", "test@example.invalid")
        git(self.path, "config", "user.name", "Test")
        self.write(files)
        self.commit("base")
        self.base = self.head()

    def write(self, files):
        for name, text in files.items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)

    def commit(self, message):
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", message)

    def head(self):
        return subprocess.run(
            ["git", "-C", str(self.path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def check(self, repo, *extra):
        return subprocess.run(
            [
                sys.executable,
                str(INTEGRITY),
                "--repo",
                str(repo.path),
                "--base",
                repo.base,
                "--json",
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_unchanged_tests_pass(self):
        repo = Repo(
            self.root, {"src/math.test.ts": JS_TESTS, "src/math.ts": "export {}\n"}
        )
        repo.write({"src/math.ts": "export const one = 1;\n"})
        repo.commit("feature")
        result = self.check(repo)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_removed_test_fails_until_approved(self):
        repo = Repo(self.root, {"tests/test_orgs.py": PY_TESTS})
        repo.write({"tests/test_orgs.py": "def test_create():\n    pass\n"})
        repo.commit("drop a test")
        result = self.check(repo)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["failures"], ["tests"])
        self.assertEqual(self.check(repo, "--allow", "tests").returncode, 0)

    def test_deleted_test_file_fails(self):
        repo = Repo(
            self.root,
            {"pkg/client_test.go": "package pkg\n\nfunc TestGet(t *testing.T) {}\n"},
        )
        (repo.path / "pkg/client_test.go").unlink()
        repo.commit("delete")
        self.assertEqual(self.check(repo).returncode, 1)

    def test_skip_and_only_markers_fail(self):
        repo = Repo(self.root, {"src/math.test.ts": JS_TESTS})
        repo.write(
            {"src/math.test.ts": JS_TESTS.replace("it('adds'", "it.skip('adds'")}
        )
        repo.commit("skip")
        report = json.loads(self.check(repo).stdout)
        self.assertEqual(report["failures"], ["markers"])
        self.assertEqual(report["tests_removed"], [])

    def test_pytest_skip_decorator_fails(self):
        repo = Repo(self.root, {"test_api.py": PY_TESTS})
        repo.write({"test_api.py": "import pytest\n\n@pytest.mark.skip\n" + PY_TESTS})
        repo.commit("skip")
        self.assertEqual(json.loads(self.check(repo).stdout)["failures"], ["markers"])

    def test_gate_config_and_verify_script_changes_fail_until_approved(self):
        package = {"scripts": {"verify": "eslint --max-warnings=0 && tsc --noEmit"}}
        repo = Repo(
            self.root,
            {
                "package.json": json.dumps(package),
                "eslint.config.mjs": "export default [];\n",
            },
        )
        package["scripts"]["verify"] = "tsc --noEmit"
        repo.write(
            {
                "package.json": json.dumps(package),
                "eslint.config.mjs": "export default [{ rules: {} }];\n",
            }
        )
        repo.commit("loosen")
        report = json.loads(self.check(repo).stdout)
        self.assertEqual(report["failures"], ["gates"])
        self.assertEqual(len(report["gates_changed"]), 2)
        self.assertEqual(self.check(repo, "--allow", "gates").returncode, 0)

    def test_dependency_and_action_pin_bumps_are_not_gate_changes(self):
        workflow = (
            "jobs:\n  ci:\n    steps:\n      - uses: actions/checkout@aaaa # v6\n"
        )
        repo = Repo(
            self.root,
            {
                "package.json": json.dumps(
                    {"dependencies": {"next": "16.0.0"}, "scripts": {"verify": "tsc"}}
                ),
                "pyproject.toml": "[project]\ndependencies = ['httpx==0.27']\n\n[tool.ruff]\nline-length = 100\n",
                ".github/workflows/ci.yml": workflow,
            },
        )
        repo.write(
            {
                "package.json": json.dumps(
                    {"dependencies": {"next": "16.4.2"}, "scripts": {"verify": "tsc"}}
                ),
                "pyproject.toml": "[project]\ndependencies = ['httpx==0.28']\n\n[tool.ruff]\nline-length = 100\n",
                ".github/workflows/ci.yml": workflow.replace(
                    "@aaaa # v6", "@bbbb # v7"
                ),
            }
        )
        repo.commit("bump")
        self.assertEqual(self.check(repo).returncode, 0, self.check(repo).stdout)

    def test_workflow_edits_are_reported_without_failing(self):
        repo = Repo(self.root, {".github/workflows/ci.yml": "jobs: {}\n"})
        repo.write({".github/workflows/ci.yml": "jobs:\n  lint: {}\n"})
        repo.commit("ci")
        result = self.check(repo)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(json.loads(result.stdout)["ci_changed"]), 1)

    def test_worktree_mode_sees_uncommitted_edits(self):
        repo = Repo(self.root, {"src/math.test.ts": JS_TESTS})
        repo.write({"src/math.test.ts": "it('adds', () => {});\n"})
        result = self.check(repo, "--head", "WORKTREE")
        self.assertEqual(result.returncode, 1)


class StopHookTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.env = {**os.environ, "AGENT_GATES_STATE": str(self.root / "state")}
        self.env.pop("AGENT_VERIFY_CMD", None)

    def hook(self, event, repo, **payload):
        body = {"session_id": "s1", "cwd": str(repo.path), **payload}
        return subprocess.run(
            [sys.executable, str(GATES), event],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )

    def verifying_repo(self, verify_exit):
        makefile = f"verify:\n\t@echo checking && exit {verify_exit}\n"
        return Repo(self.root, {"Makefile": makefile, "tests/test_orgs.py": PY_TESTS})

    def test_unchanged_repository_is_not_verified(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        self.assertEqual(self.hook("stop", repo).returncode, 0)

    def test_failing_verify_blocks_then_gives_up(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        first = self.hook("stop", repo)
        self.assertEqual(first.returncode, 2)
        self.assertIn("make verify", first.stderr)
        self.assertIn("checking", first.stderr)
        self.assertIn("Do not delete or skip tests", first.stderr)
        self.hook("stop", repo)
        self.hook("stop", repo)
        final = self.hook("stop", repo)
        self.assertEqual(final.returncode, 0)
        self.assertIn("not verified", json.loads(final.stdout)["systemMessage"])

    def test_passing_verify_allows_stop_and_is_not_rerun(self):
        repo = self.verifying_repo(0)
        runs = self.root / "runs.log"
        self.env["AGENT_VERIFY_CMD"] = f"echo run >> '{runs}'"
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        self.assertEqual(self.hook("stop", repo).returncode, 0)
        self.assertEqual(self.hook("stop", repo).returncode, 0)
        self.assertEqual(runs.read_text().count("run"), 1)
        repo.write({"app.py": "x = 2\n"})
        self.assertEqual(self.hook("stop", repo).returncode, 0)
        self.assertEqual(runs.read_text().count("run"), 2)

    def test_committed_change_is_verified(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        repo.commit("agent commit")
        self.assertEqual(self.hook("stop", repo).returncode, 2)

    def test_removed_test_blocks_once_with_acknowledgement_request(self):
        repo = self.verifying_repo(0)
        self.hook("session-start", repo)
        repo.write({"tests/test_orgs.py": "def test_create():\n    pass\n"})
        first = self.hook("stop", repo)
        self.assertEqual(first.returncode, 2)
        self.assertIn("tests/test_orgs.py", first.stderr)
        self.assertIn("name each file", first.stderr)
        self.assertEqual(self.hook("stop", repo).returncode, 0)

    def test_repository_without_verify_command_still_checks_integrity(self):
        repo = Repo(self.root, {"tests/test_orgs.py": PY_TESTS})
        self.hook("session-start", repo)
        (repo.path / "tests/test_orgs.py").unlink()
        self.assertEqual(self.hook("stop", repo).returncode, 2)

    def test_explicit_verify_command_overrides_detection(self):
        repo = self.verifying_repo(0)
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        self.env["AGENT_VERIFY_CMD"] = "echo custom-check; exit 3"
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("custom-check", result.stderr)

    def test_outside_git_and_malformed_input_are_allowed(self):
        plain = self.root / "plain"
        plain.mkdir()
        result = subprocess.run(
            [sys.executable, str(GATES), "stop"],
            input=json.dumps({"cwd": str(plain)}),
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        result = subprocess.run(
            [sys.executable, str(GATES), "stop"],
            input="not json",
            capture_output=True,
            text=True,
            env=self.env,
            cwd=plain,
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_format_hook_records_start_and_skips_unconfigured_projects(self):
        repo = self.verifying_repo(1)
        repo.write({"app.py": "x=1\n"})
        result = self.hook(
            "format",
            repo,
            tool_name="Edit",
            tool_input={"file_path": str(repo.path / "app.py")},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual((repo.path / "app.py").read_text(), "x=1\n")
        state = json.loads((self.root / "state" / "s1.json").read_text())
        self.assertEqual(state["starts"][str(repo.path.resolve())], repo.base)


if __name__ == "__main__":
    unittest.main()
