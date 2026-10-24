"""Agent gates: the hooks and integrity check catch shortcuts without false blocks.

Each test drives the hooks exactly as Claude Code does: JSON on stdin, exit
code and stdout/stderr out. Repositories are disposable.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "global-instructions" / "hooks"
GATES = HOOKS / "agent_gates.py"
INTEGRITY = HOOKS / "test_integrity.py"
sys.path.insert(0, str(HOOKS))
import test_integrity

JS_TESTS = (
    "import { it } from 'vitest';\nit('adds', () => {});\nit('subtracts', () => {});\n"
)
PY_TESTS = "def test_create():\n    pass\n\ndef test_delete():\n    pass\n"
ONE_PY_TEST = "def test_create():\n    pass\n"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class Repo:
    """A disposable repository with one commit containing the given files."""

    def __init__(self, parent: Path, files: dict, name: str = "app"):
        self.path = parent / name
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
            if isinstance(text, bytes):
                target.write_bytes(text)
            else:
                target.write_text(text)

    def commit(self, message):
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", message)

    def head(self):
        result = subprocess.run(
            ["git", "-C", str(self.path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def check(self, repo, *extra, base=None):
        return subprocess.run(
            [
                sys.executable,
                str(INTEGRITY),
                "--repo",
                str(repo.path),
                "--base",
                base or repo.base,
                "--json",
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def report(self, repo, *extra, base=None):
        result = self.check(repo, *extra, base=base)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_unchanged_tests_pass(self):
        repo = Repo(
            self.root, {"src/math.test.ts": JS_TESTS, "src/math.ts": "export {}\n"}
        )
        repo.write({"src/math.ts": "export const one = 1;\n"})
        repo.commit("feature")
        self.assertEqual(self.report(repo)[0], 0)

    def test_removed_test_fails_until_approved(self):
        repo = Repo(self.root, {"tests/test_orgs.py": PY_TESTS})
        repo.write({"tests/test_orgs.py": ONE_PY_TEST})
        repo.commit("drop a test")
        code, report = self.report(repo)
        self.assertEqual((code, report["failures"]), (1, ["tests"]))
        self.assertEqual(self.report(repo, "--allow", "tests")[0], 0)

    def test_deleted_go_test_file_fails(self):
        repo = Repo(
            self.root,
            {"pkg/client_test.go": "package pkg\n\nfunc TestGet(t *testing.T) {}\n"},
        )
        (repo.path / "pkg/client_test.go").unlink()
        repo.commit("delete")
        self.assertEqual(self.report(repo)[0], 1)

    def test_renames_splits_and_moves_are_not_removals(self):
        repo = Repo(
            self.root,
            {
                "src/math.test.ts": JS_TESTS,
                "test_x.py": PY_TESTS,
                "test_skipped.py": "import pytest\n\n@pytest.mark.skip\ndef test_old():\n    pass\n",
            },
        )
        git(repo.path, "mv", "src/math.test.ts", "src/arith.test.ts")
        git(repo.path, "mv", "test_skipped.py", "test_moved.py")
        repo.write(
            {"test_x.py": ONE_PY_TEST, "test_y.py": "def test_delete():\n    pass\n"}
        )
        repo.commit("reorganize")
        code, report = self.report(repo)
        self.assertEqual(code, 0, report)

    def test_skip_markers_fail(self):
        cases = {
            "src/math.test.ts": (
                JS_TESTS,
                JS_TESTS.replace("it('adds'", "it.concurrent.skip('adds'"),
            ),
            "test_api.py": (
                PY_TESTS,
                "import pytest\npytestmark = pytest.mark.skip\n" + PY_TESTS,
            ),
            "spec/e2e.spec.cjs": (
                "test('loads', () => {});\n",
                "test.fixme('loads', () => {});\n",
            ),
        }
        for name, (before, after) in cases.items():
            with self.subTest(name=name):
                parent = self.root / name.replace("/", "_")
                parent.mkdir()
                repo = Repo(parent, {name: before})
                repo.write({name: after})
                repo.commit("skip")
                self.assertEqual(self.report(repo)[1]["failures"], ["markers"])

    def test_new_gated_test_files_are_not_weakening(self):
        repo = Repo(self.root, {"src/a.test.ts": JS_TESTS})
        repo.write(
            {
                "src/db.integration.test.ts": "describe.skipIf(!process.env.DB)('db', () => { it('reads', () => {}); });\n"
            }
        )
        repo.commit("add gated integration tests")
        self.assertEqual(self.report(repo)[0], 0)
        repo.base = repo.head()
        repo.write(
            {
                "src/a.test.ts": "describe.skipIf(!process.env.CI)('a', () => {\n"
                + JS_TESTS
                + "});\n"
            }
        )
        repo.commit("gate existing tests")
        self.assertEqual(self.report(repo)[1]["failures"], ["markers"])

    def test_verify_recipe_and_delegated_scripts_are_gates(self):
        package = {
            "scripts": {"verify": "npm run test:unit && tsc", "test:unit": "vitest run"}
        }
        repo = Repo(
            self.root,
            {
                "Makefile": "verify: lint\n\tpython3 -m pytest -q\nlint:\n\truff check .\ndeploy:\n\techo hi\n",
                "package.json": json.dumps(package),
            },
        )
        package["scripts"]["test:unit"] = "true"
        repo.write(
            {
                "Makefile": "verify: lint\n\t@true\nlint:\n\truff check .\ndeploy:\n\techo hi\n",
                "package.json": json.dumps(package),
            }
        )
        repo.commit("weaken")
        gates = self.report(repo)[1]["gates_changed"]
        self.assertEqual(len(gates), 2, gates)

    def test_unrelated_makefile_and_dependency_changes_pass(self):
        workflow = (
            "jobs:\n  ci:\n    steps:\n      - uses: actions/checkout@aaaa # v6\n"
        )
        repo = Repo(
            self.root,
            {
                "Makefile": "verify:\n\tpytest\ndeploy:\n\techo old\n",
                "package.json": json.dumps(
                    {"dependencies": {"next": "16.0.0"}, "scripts": {"verify": "tsc"}}
                ),
                "pyproject.toml": "[project]\nversion = '1'\n\n[tool.ruff]\nline-length = 100\n",
                "setup.cfg": "[metadata]\nversion = 1.0.0\n\n[flake8]\nmax-line-length = 100\n",
                ".github/workflows/ci.yml": workflow,
            },
        )
        repo.write(
            {
                "Makefile": "verify:\n\tpytest\ndeploy:\n\techo new\n",
                "package.json": json.dumps(
                    {"dependencies": {"next": "16.4.2"}, "scripts": {"verify": "tsc"}}
                ),
                "pyproject.toml": "[project]\nversion = '2'\n\n[tool.ruff]\nline-length = 100\n",
                "setup.cfg": "[metadata]\nversion = 1.0.1\n\n[flake8]\nmax-line-length = 100\n",
                ".github/workflows/ci.yml": workflow.replace(
                    "@aaaa # v6", "@bbbb # v7"
                ),
            }
        )
        repo.commit("bump")
        code, report = self.report(repo)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["ci_changed"], [])

    def test_checker_sections_and_arrays_of_tables_are_gates(self):
        repo = Repo(
            self.root,
            {"pyproject.toml": "[project]\n\n[[tool.mypy.overrides]]\nmodule = 'a'\n"},
        )
        repo.write(
            {
                "pyproject.toml": "[project]\n\n[[tool.mypy.overrides]]\nmodule = '*'\nignore_errors = true\n"
            }
        )
        repo.commit("loosen")
        self.assertEqual(self.report(repo)[1]["failures"], ["gates"])

    def test_workflow_edits_are_reported_without_failing(self):
        repo = Repo(self.root, {".github/workflows/ci.yml": "jobs: {}\n"})
        repo.write({".github/workflows/ci.yml": "jobs:\n  lint: {}\n"})
        repo.commit("ci")
        code, report = self.report(repo)
        self.assertEqual((code, len(report["ci_changed"])), (0, 1))

    def test_repinning_the_integrity_workflow_is_reported(self):
        line = "      - uses: Astatide1337/Skills/.github/workflows/test-integrity.yml@{}\n"
        repo = Repo(
            self.root, {".github/workflows/ci.yml": "jobs:\n" + line.format("aaa")}
        )
        repo.write({".github/workflows/ci.yml": "jobs:\n" + line.format("bbb")})
        repo.commit("repin")
        self.assertEqual(len(self.report(repo)[1]["ci_changed"]), 1)

    def test_worktree_snapshot_ignores_crlf_symlinks_and_sparse_paths(self):
        repo = Repo(
            self.root,
            {
                "svc-a/tsconfig.json": "{}\r\n",
                "svc-b/test_b.py": PY_TESTS,
                "setup.cfg": "[flake8]\r\nmax-line-length = 100\r\n",
            },
        )
        os.symlink("svc-a/tsconfig.json", repo.path / "tsconfig.json")
        repo.commit("link")
        repo.base = repo.head()
        git(repo.path, "config", "core.autocrlf", "true")
        git(repo.path, "sparse-checkout", "set", "svc-a")
        code, report = self.report(repo, "--head", "WORKTREE")
        self.assertEqual(code, 0, report)

    def test_worktree_mode_sees_uncommitted_and_untracked_edits(self):
        repo = Repo(self.root, {"tests/test_a.py": PY_TESTS})
        repo.write({"tests/test_a.py": ONE_PY_TEST, "tests/test_new.py": "x = 1\n"})
        self.assertEqual(self.report(repo, "--head", "WORKTREE")[0], 1)

    def test_non_utf8_content_and_paths_do_not_crash(self):
        repo = Repo(
            self.root,
            {"legacy.txt": "caf\xe9\n".encode("latin-1"), "tests/test_a.py": PY_TESTS},
        )
        (
            repo.path
            / "r\xe9sum\xe9.txt".encode("latin-1").decode("utf-8", "surrogateescape")
        ).write_bytes(b"x")
        repo.write(
            {
                "legacy.txt": "na\xefve\n".encode("latin-1"),
                "tests/test_a.py": ONE_PY_TEST,
            }
        )
        result = self.check(repo, "--head", "WORKTREE")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_approvals_require_a_human_label_after_the_head_commit(self):
        def labeled(name, when, login="soham", kind="User", event="labeled"):
            return {
                "event": event,
                "created_at": when,
                "label": {"name": name},
                "actor": {"login": login, "type": kind},
            }

        head_time = "2026-10-23T12:00:00Z"
        approvals = test_integrity.approvals
        self.assertEqual(
            approvals(
                [labeled("tests-removed-ok", "2026-10-23T12:05:00Z")], head_time, set()
            ),
            {"tests"},
        )
        self.assertEqual(
            approvals(
                [labeled("tests-removed-ok", "2026-10-23T11:00:00Z")], head_time, set()
            ),
            set(),
            "a label from before the latest commit must not count",
        )
        self.assertEqual(
            approvals(
                [labeled("gates-changed-ok", "2026-10-23T12:05:00Z", "ci[bot]", "Bot")],
                head_time,
                set(),
            ),
            set(),
        )
        self.assertEqual(
            approvals(
                [labeled("gates-changed-ok", "2026-10-23T12:05:00Z", "agent")],
                head_time,
                {"soham"},
            ),
            set(),
        )
        self.assertEqual(
            approvals(
                [
                    labeled("tests-removed-ok", "2026-10-23T12:05:00Z"),
                    labeled(
                        "tests-removed-ok", "2026-10-23T12:06:00Z", event="unlabeled"
                    ),
                ],
                head_time,
                set(),
            ),
            set(),
        )


class WorkflowTests(unittest.TestCase):
    def test_cli_applies_only_fresh_human_approvals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = Repo(root, {"tests/test_a.py": PY_TESTS})
            repo.write({"tests/test_a.py": ONE_PY_TEST})
            repo.commit("drop")
            events = root / "events.json"

            def run(created_at, actor_type="User"):
                events.write_text(
                    json.dumps(
                        [
                            {
                                "event": "labeled",
                                "created_at": created_at,
                                "label": {"name": "tests-removed-ok"},
                                "actor": {"login": "soham", "type": actor_type},
                            }
                        ]
                    )
                )
                return subprocess.run(
                    [
                        sys.executable,
                        str(INTEGRITY),
                        "--repo",
                        str(repo.path),
                        "--base",
                        repo.base,
                        "--approval-events",
                        str(events),
                        "--approval-after",
                        "2026-10-23T12:00:00Z",
                        "--approvers",
                        "soham",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                ).returncode

            self.assertEqual(run("2026-10-23T12:30:00Z"), 0)
            self.assertEqual(run("2026-10-23T11:30:00Z"), 1, "stale approval")
            self.assertEqual(run("2026-10-23T12:30:00Z", "Bot"), 1, "bot approval")

    def test_reusable_workflow_wires_approvals_and_the_pinned_checker(self):
        text = (ROOT / ".github/workflows/test-integrity.yml").read_text()
        for needle in (
            "--approval-events",
            "--approval-after",
            "--approvers",
            "ref: ${{ inputs.skills-ref }}",
            "pull-requests: read",
            'exit "${PIPESTATUS[0]}"',
        ):
            self.assertIn(needle, text)


class VerifyCommandTests(unittest.TestCase):
    def test_runner_follows_the_lockfile(self):
        sys.path.insert(0, str(HOOKS))
        import agent_gates

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"verify": "tsc"}})
            )
            self.assertEqual(agent_gates.verify_command(root), ["npm", "run", "verify"])
            for lockfile, runner in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn")):
                (root / lockfile).write_text("")
                self.assertEqual(
                    agent_gates.verify_command(root), [runner, "run", "verify"]
                )
                (root / lockfile).unlink()
            (root / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest"}})
            )
            self.assertIsNone(agent_gates.verify_command(root))


class StopHookTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.env = {
            **os.environ,
            "AGENT_GATES_STATE": str(self.root / "state"),
            "AGENT_GATES_TRUSTED": str(self.root),
        }
        self.env.pop("AGENT_VERIFY_CMD", None)

    def hook(self, event, repo_or_path, active=False, **payload):
        cwd = repo_or_path.path if isinstance(repo_or_path, Repo) else repo_or_path
        body = {
            "session_id": "s1",
            "cwd": str(cwd),
            "stop_hook_active": active,
            **payload,
        }
        return subprocess.run(
            [sys.executable, str(GATES), event],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )

    def verifying_repo(self, verify_exit, extra=None, name="app"):
        makefile = f"verify:\n\t@echo checking && exit {verify_exit}\n"
        return Repo(
            self.root,
            {"Makefile": makefile, "tests/test_orgs.py": PY_TESTS, **(extra or {})},
            name=name,
        )

    def stops(self, repo, count, **payload):
        return [
            self.hook("stop", repo, active=index > 0, **payload)
            for index in range(count)
        ]

    def test_read_only_session_in_a_dirty_repo_is_not_verified_or_blamed(self):
        repo = self.verifying_repo(1)
        repo.write({"NOTES.txt": "user notes\n", "tests/test_orgs.py": ONE_PY_TEST})
        self.hook("session-start", repo)
        self.assertEqual(
            [result.returncode for result in self.stops(repo, 3)], [0, 0, 0]
        )

    def test_failing_verify_blocks_three_times_then_gives_up(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        results = self.stops(repo, 4)
        self.assertEqual([result.returncode for result in results], [2, 2, 2, 0])
        self.assertIn("attempt 3 of 3", results[2].stderr)
        self.assertIn("make verify", results[0].stderr)
        self.assertIn("checking", results[0].stderr)
        self.assertIn("Do not delete or skip tests", results[0].stderr)
        self.assertIn("not verified", json.loads(results[3].stdout)["systemMessage"])

    def test_a_new_turn_gets_fresh_attempts_and_an_unchanged_failure_is_not_rerun(self):
        repo = self.verifying_repo(1)
        runs = self.root / "runs.log"
        self.env["AGENT_VERIFY_CMD"] = f"echo run >> '{runs}'; exit 1"
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        self.stops(repo, 4)
        self.assertEqual(runs.read_text().count("run"), 3)
        self.assertEqual(
            self.hook("stop", repo).returncode, 0, "unchanged given-up tree"
        )
        self.assertEqual(runs.read_text().count("run"), 3)
        repo.write({"app.py": "x = 2\n"})
        self.assertEqual(self.hook("stop", repo).returncode, 2, "new turn, new change")

    def test_passing_verify_is_not_rerun_even_when_it_writes_report_files(self):
        repo = self.verifying_repo(0)
        runs = self.root / "runs.log"
        self.env["AGENT_VERIFY_CMD"] = f"echo run >> '{runs}'; date +%N > junit.xml"
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        self.assertEqual(
            [result.returncode for result in self.stops(repo, 3)], [0, 0, 0]
        )
        self.assertEqual(runs.read_text().count("run"), 1)
        repo.write({"app.py": "x = 2\n"})
        self.assertEqual(self.hook("stop", repo).returncode, 0)
        self.assertEqual(runs.read_text().count("run"), 2)

    def test_removed_test_blocks_once_then_tells_the_user(self):
        repo = self.verifying_repo(0)
        self.env["AGENT_VERIFY_CMD"] = "date +%N > junit.xml"
        self.hook("session-start", repo)
        repo.write({"tests/test_orgs.py": ONE_PY_TEST})
        first, second, third = self.stops(repo, 3)
        self.assertEqual(first.returncode, 2)
        self.assertIn("tests/test_orgs.py", first.stderr)
        self.assertIn("name each item", first.stderr)
        self.assertEqual((second.returncode, third.returncode), (0, 0))
        self.assertIn("weakened a check", json.loads(second.stdout)["systemMessage"])
        repo.write({"app.py": "x = 1\n"})
        self.assertEqual(
            self.hook("stop", repo).returncode, 0, "approved finding must not re-block"
        )

    def test_deleted_tests_are_reported_even_while_verify_fails(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        (repo.path / "tests/test_orgs.py").unlink()
        results = self.stops(repo, 4)
        self.assertTrue(all("test_orgs.py" in result.stderr for result in results[:3]))
        self.assertIn("test_orgs.py", json.loads(results[3].stdout)["systemMessage"])

    def test_weakened_verify_recipe_blocks(self):
        repo = Repo(
            self.root, {"Makefile": "verify:\n\tpython3 -c 'raise SystemExit(1)'\n"}
        )
        self.hook("session-start", repo)
        repo.write({"Makefile": "verify:\n\t@true\n", "app.py": "x = 1\n"})
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("verify recipe", result.stderr)

    def test_committed_change_is_verified(self):
        repo = self.verifying_repo(1)
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        repo.commit("agent commit")
        self.assertEqual(self.hook("stop", repo).returncode, 2)

    def test_second_repository_touched_through_an_edit_is_checked(self):
        first = self.verifying_repo(0)
        second = self.verifying_repo(1, name="other")
        self.hook("session-start", first)
        self.hook(
            "guard",
            first,
            tool_name="Edit",
            tool_input={"file_path": str(second.path / "app.py")},
        )
        second.write({"app.py": "x = 1\n"})
        result = self.hook("stop", first)
        self.assertEqual(result.returncode, 2)
        self.assertIn(str(second.path), result.stderr)

    def test_commits_in_a_worktree_created_this_session_are_checked(self):
        repo = self.verifying_repo(0)
        self.hook("session-start", repo)
        tree = self.root / "wt"
        git(repo.path, "worktree", "add", "-q", str(tree), "-b", "agent")
        (tree / "tests/test_orgs.py").write_text(ONE_PY_TEST)
        git(tree, "commit", "-qam", "drop")
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("test_orgs.py", result.stderr)

    def test_missing_state_falls_back_to_the_reflog(self):
        repo = self.verifying_repo(0)
        transcript = self.root / "transcript.jsonl"
        transcript.write_text(json.dumps({"timestamp": "2000-01-01T00:00:00Z"}) + "\n")
        repo.write({"tests/test_orgs.py": ONE_PY_TEST})
        repo.commit("drop")
        result = self.hook("stop", repo, transcript_path=str(transcript))
        self.assertEqual(result.returncode, 2, result.stdout)

    @unittest.skipIf(shutil.which("just"), "needs a machine without `just`")
    def test_missing_runner_notifies_instead_of_blocking(self):
        repo = Repo(self.root, {"justfile": "verify:\n\tfalse\n"})
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("not installed", json.loads(result.stdout)["systemMessage"])

    def test_untrusted_paths_are_not_executed(self):
        repo = self.verifying_repo(1)
        self.env["AGENT_GATES_TRUSTED"] = "/nowhere"
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AGENT_GATES_TRUSTED", json.loads(result.stdout)["systemMessage"])

    def test_verify_timeout_stops_child_processes(self):
        repo = self.verifying_repo(0)
        marker = self.root / "survivor"
        self.env["AGENT_VERIFY_CMD"] = f"sleep 3; touch '{marker}'"
        self.env["AGENT_VERIFY_TIMEOUT"] = "1"
        self.hook("session-start", repo)
        repo.write({"app.py": "x = 1\n"})
        result = self.hook("stop", repo)
        self.assertEqual(result.returncode, 2)
        self.assertIn("timed out", result.stderr)
        subprocess.run(["sleep", "3"], check=True)
        self.assertFalse(marker.exists(), "a timed-out verify's children kept running")

    def test_corrupt_state_and_crashes_fail_noisily(self):
        repo = self.verifying_repo(1)
        (self.root / "state").mkdir()
        (self.root / "state" / "s1.json").write_text("{}")
        repo.write({"app.py": "x = 1\n"})
        result = self.hook("stop", repo)
        self.assertEqual(
            result.returncode, 2, "a partial state file must not disable the gate"
        )

    def test_outside_git_and_malformed_input_are_allowed(self):
        plain = self.root / "plain"
        plain.mkdir()
        self.assertEqual(self.hook("stop", plain).returncode, 0)
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

    def test_guard_blocks_bypasses_and_gate_tampering(self):
        repo = self.verifying_repo(0)
        blocked = [
            "git commit --no-verify -m wip",
            "git commit -nm wip",
            "HUSKY=0 git push",
            "git config core.hooksPath /dev/null",
            f"rm -rf {self.root / 'state'}",
        ]
        for command in blocked:
            with self.subTest(command=command):
                result = self.hook(
                    "guard", repo, tool_name="Bash", tool_input={"command": command}
                )
                self.assertEqual(result.returncode, 2, result.stderr)
        allowed = [
            "git commit -m 'use -n carefully'",
            "git switch agent-gates",
            "npm test",
        ]
        for command in allowed:
            with self.subTest(command=command):
                result = self.hook(
                    "guard", repo, tool_name="Bash", tool_input={"command": command}
                )
                self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.root / ".claude" / "settings.json"
        result = self.hook(
            "guard", repo, tool_name="Edit", tool_input={"file_path": str(settings)}
        )
        self.assertEqual(result.returncode, 2)

    def test_format_hook_skips_unconfigured_projects_and_committed_binaries(self):
        repo = self.verifying_repo(
            1, {"ruff.toml": "", ".venv/bin/ruff": "#!/bin/sh\ntouch PWNED\n"}
        )
        (repo.path / ".venv/bin/ruff").chmod(0o755)
        repo.commit("binary")
        repo.write({"app.py": "x=1\n"})
        self.env["PATH"] = "/usr/bin:/bin"
        result = self.hook(
            "format",
            repo,
            tool_name="Edit",
            tool_input={"file_path": str(repo.path / "app.py")},
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(
            (repo.path / "PWNED").exists(), "a committed binary was executed"
        )

    def test_format_hook_ignores_a_committed_node_modules_binary(self):
        script = "#!/bin/sh\ntouch PWNED\n"
        repo = self.verifying_repo(
            1, {".prettierrc": "{}", "node_modules/.bin/prettier": script}
        )
        (repo.path / "node_modules/.bin/prettier").chmod(0o755)
        repo.commit("binary")
        repo.write({"app.ts": "const x=1\n"})
        result = self.hook(
            "format",
            repo,
            tool_name="Write",
            tool_input={"file_path": str(repo.path / "app.ts")},
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(
            (repo.path / "PWNED").exists(), "a committed binary was executed"
        )


if __name__ == "__main__":
    unittest.main()
