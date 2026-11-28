"""Offline coverage for the autonomous runners and shared judge transcript."""

import builtins
import fcntl
import io
import json
import os
import signal
import subprocess
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from evals import grade, run


def jsonl(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


THREAD = {"type": "thread.started", "thread_id": "codex-thread"}
WORKSPACE_LIMITS = (
    "Your workspace is out of credits.",
    "You hit your spend cap set in your workspace.",
    "You hit your spend cap set by the owner of your workspace.",
)
EXPIRED_REFRESH = (
    "Your access token could not be refreshed because your refresh token has expired. "
    "Please log out and sign in again."
)
REPLY = {
    "type": "item.completed",
    "item": {
        "type": "agent_message",
        "id": "item_1",
        "text": "Fixed the tie-break.",
    },
}
CODEX_SUCCESS = jsonl(
    THREAD,
    REPLY,
    {
        "type": "turn.completed",
        "usage": {
            "input_tokens": 100,
            "cached_input_tokens": 80,
            "cache_write_input_tokens": 0,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
        },
    },
)
CLAUDE_SUCCESS = jsonl(
    {
        "type": "result",
        "session_id": "claude-session",
        "result": "Fixed the tie-break.",
        "num_turns": 2,
        "duration_ms": 123,
        "total_cost_usd": 0.05,
        "usage": {
            "input_tokens": 15,
            "cache_read_input_tokens": 50,
            "cache_creation_input_tokens": 35,
            "output_tokens": 20,
        },
    }
)


class RunTests(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(TemporaryDirectory())
        self.args = SimpleNamespace(
            out=Path(tmp),
            turn_timeout=3,
            model="mock-model",
            guard=run.UsageGuard(0.6, 0.8),
            agent="claude",
            codex_home=Path(tmp) / "eval-codex-home",
        )
        self.case = run.load_case(run.CASES / "flaky-tie-break")
        self.out = self.args.out / self.case["id"] / "none" / "run-1"
        self.commands = []
        self.enterContext(patch.object(run, "sh", side_effect=self.shell))
        self.enterContext(patch.object(run, "codex_auth", return_value=nullcontext()))

    def shell(self, *args, **kwargs):
        self.commands.append(args)
        stdout = "base123\n" if args[-3:] == ("git", "rev-parse", "HEAD") else ""
        return subprocess.CompletedProcess(args, 0, stdout, "")

    def execute(self, *outputs, catalog=None, stderr=""):
        def invoke(cmd, **kwargs):
            self.commands.append(tuple(cmd))
            outcome = next(events)
            if isinstance(outcome, BaseException):
                raise outcome
            stdout, code = outcome if isinstance(outcome, tuple) else (outcome, 0)
            return subprocess.CompletedProcess(cmd, code, stdout, stderr)

        events = iter(outputs)
        with patch.object(run.subprocess, "run", side_effect=invoke):
            run.run_one(self.case, "none", catalog, 1, self.args)
        return json.loads((self.out / "timing.json").read_text())

    def test_claude_stats_and_followup(self):
        self.case["turns"] = ["Check it again."]
        timing = self.execute(CLAUDE_SUCCESS, CLAUDE_SUCCESS)
        self.assertEqual(timing["total_tokens"], 240)
        self.assertEqual(timing["turns"], 4)
        self.assertEqual(timing["cost_usd"], 0.1)
        self.assertEqual(len([cmd for cmd in self.commands if "--resume" in cmd]), 1)

    def test_codex_resume_uses_thread_totals_and_catalog_paths(self):
        self.args.agent = "codex"
        self.case["turns"] = ["Check it again."]
        followup = jsonl(
            THREAD,
            REPLY,
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 130,
                    "output_tokens": 23,
                },
            },
        )
        catalog = self.args.out / "catalog"
        instructions = catalog / "global-instructions/AGENTS.md"
        instructions.parent.mkdir(parents=True)
        instructions.write_text("Use the catalog.")
        timing = self.execute(CODEX_SUCCESS, followup, catalog=catalog)
        self.assertEqual(timing["total_tokens"], 153)
        self.assertEqual(timing["turns"], 2)
        self.assertIsNone(timing["cost_usd"])
        first, second = [c for c in self.commands if "--json" in c]
        self.assertEqual(first[-1], "-")
        start = second.index("codex")
        self.assertEqual(
            second[start : start + 4], ("codex", "exec", "resume", "codex-thread")
        )
        copies = [c[-1] for c in self.commands if c[:2] == ("docker", "cp")]
        self.assertTrue(any(p.endswith("/.agents/skills") for p in copies))
        self.assertTrue(
            any('cat > "/home/node/.codex/AGENTS.md"' in c for c in self.commands)
        )

    def test_timeouts_keep_partial_trace_and_kill_before_checks(self):
        for agent, partial in (
            ("claude", '{"type":"assistant"}\n'),
            ("codex", jsonl(THREAD, REPLY)),
        ):
            with self.subTest(agent=agent):
                self.args.agent = agent
                self.case["turns"] = ["must not reach this turn"]
                self.out.mkdir(parents=True, exist_ok=True)
                (self.out / "trace-1.jsonl").write_text("stale artifact")
                (self.out / "timing.json").unlink(missing_ok=True)
                self.commands.clear()
                partial += '{"truncated":'
                timing = self.execute(
                    subprocess.TimeoutExpired(
                        agent,
                        3,
                        output=partial.encode(),
                        stderr=b"partial stderr",
                    )
                )
                self.assertTrue(timing["timed_out"])
                self.assertFalse(timing["usage_complete"])
                self.assertEqual((self.out / "trace-0.jsonl").read_text(), partial)
                self.assertFalse((self.out / "trace-1.jsonl").exists())
                self.assertIn("stopped after 3s", (self.out / "final.md").read_text())
                kill = next(
                    i for i, cmd in enumerate(self.commands) if run.KILL_AGENT in cmd
                )
                copy_checks = next(
                    i
                    for i, cmd in enumerate(self.commands)
                    if any(part.endswith("/checks/.") for part in cmd)
                )
                self.assertLess(kill, copy_checks)
                self.assertTrue(any("BASE_SHA=base123" in cmd for cmd in self.commands))
                self.assertTrue(
                    any("git diff --cached base123" in cmd[-1] for cmd in self.commands)
                )

    def test_agent_errors_are_graded(self):
        cases = {
            "claude": jsonl({"type": "result", "api_error": "max_output_tokens"}),
            "codex": jsonl(
                THREAD,
                {
                    "type": "turn.failed",
                    "error": {
                        "message": "Incomplete response returned, reason: max_output_tokens",
                    },
                },
            ),
        }
        for agent, output in cases.items():
            with self.subTest(agent=agent):
                self.args.agent = agent
                (self.out / "timing.json").unlink(missing_ok=True)
                timing = self.execute((output, 1))
                self.assertEqual(timing["agent_errors"], ["max_output_tokens"])
                self.assertTrue((self.out / "checks.json").exists())

    def test_infra_errors_leave_run_unfinished_and_hard_limit_stops_batch(self):
        cases = [
            ("claude", "auth", jsonl({"type": "result", "api_error_status": 401})),
            ("claude", "missing", '{"type":"assistant"}\n'),
            (
                "claude",
                "limit",
                jsonl({"type": "result", "api_error": "usage_limit_reached"}),
            ),
            (
                "codex",
                "auth",
                jsonl(THREAD, {"type": "error", "message": "401 Unauthorized"}),
            ),
            ("codex", "missing", jsonl(THREAD, REPLY)),
            (
                "codex",
                "outage",
                jsonl(
                    THREAD,
                    {
                        "type": "turn.failed",
                        "error": {
                            "message": "received 503 Service Unavailable",
                        },
                    },
                ),
            ),
            (
                "codex",
                "limit",
                jsonl(
                    THREAD,
                    {
                        "type": "turn.failed",
                        "error": {
                            "message": "You’ve hit your usage limit.",
                        },
                    },
                ),
            ),
        ] + [
            ("codex", "limit", jsonl(THREAD, {"type": "error", "message": message}))
            for message in WORKSPACE_LIMITS
        ]
        for agent, failure, output in cases:
            with self.subTest(agent=agent, failure=failure):
                self.args.agent = agent
                self.args.guard = run.UsageGuard(0.6, 0.8)
                with self.assertRaises(run.InfraError):
                    self.execute((output, 1))
                self.assertFalse((self.out / "timing.json").exists())
                if failure == "limit" or (agent == "codex" and failure == "auth"):
                    with self.assertRaisesRegex(run.InfraError, "skipped"):
                        self.args.guard.before_run()
                else:
                    self.args.guard.before_run()

    def test_hard_limit_in_stderr_stops_after_completed_turn(self):
        self.case["turns"] = ["must not reach this turn"]
        for agent, output, diagnostic in (
            ("codex", CODEX_SUCCESS, WORKSPACE_LIMITS[0]),
            ("claude", CLAUDE_SUCCESS, "usage_limit_reached"),
        ):
            with self.subTest(agent=agent):
                self.args.agent = agent
                self.args.guard = run.UsageGuard(0.6, 0.8)
                self.commands.clear()
                with self.assertRaisesRegex(run.InfraError, "usage limit reached"):
                    self.execute(output, output, stderr=diagnostic)
                self.assertEqual(sum("-i" in cmd for cmd in self.commands), 1)
                self.assertTrue((self.out / "trace-0.jsonl").exists())
                self.assertFalse((self.out / "timing.json").exists())
                with self.assertRaisesRegex(run.InfraError, "skipped"):
                    run.run_one(self.case, "none", None, 2, self.args)

    def test_auth_failure_stops_scripted_turns_and_batch(self):
        self.args.agent = "codex"
        self.case["turns"] = ["must not reach this turn"]
        for message in ("401 Unauthorized", "Login required", EXPIRED_REFRESH):
            with self.subTest(message=message):
                self.args.guard = run.UsageGuard(0.6, 0.8)
                self.commands.clear()
                with self.assertRaisesRegex(
                    run.InfraError, "Codex eval login.*CODEX_HOME="
                ):
                    self.execute(CODEX_SUCCESS, stderr=message)
                self.assertEqual(sum("--json" in cmd for cmd in self.commands), 1)
                self.assertFalse((self.out / "timing.json").exists())
                with self.assertRaisesRegex(
                    run.InfraError, "skipped: Codex eval login"
                ):
                    run.run_one(self.case, "none", None, 2, self.args)

    def test_latest_window_stops_next_run_at_either_threshold(self):
        def event(**windows):
            return {
                "type": "rate_limit_event",
                "rate_limit_info": {
                    "unifiedWindows": {
                        key: {"utilization": value} for key, value in windows.items()
                    },
                },
            }

        for window, threshold in self.args.guard.thresholds.items():
            with self.subTest(window=window):
                (self.out / "timing.json").unlink(missing_ok=True)
                self.args.guard = run.UsageGuard(0.6, 0.8)
                self.execute(
                    jsonl(
                        event(five_hour=0.1, seven_day=0.2),
                        event(**{window: threshold}),
                    )
                    + CLAUDE_SUCCESS
                )
                self.assertIn(f"{window}={threshold:.1%}", self.args.guard.progress())
                count = len(self.commands)
                with self.assertRaisesRegex(run.InfraError, window):
                    run.run_one(self.case, "none", None, 2, self.args)
                self.assertEqual(count, len(self.commands))
                self.assertFalse((self.out.parent / "run-2/timing.json").exists())

    def test_flat_usage_window_reaches_threshold(self):
        self.execute(
            jsonl(
                {
                    "type": "rate_limit_event",
                    "rate_limit_info": {
                        "rateLimitType": "seven_day",
                        "utilization": 0.8,
                    },
                }
            )
            + CLAUDE_SUCCESS
        )
        with self.assertRaisesRegex(run.InfraError, "seven_day utilization"):
            self.args.guard.before_run()

    def test_lower_reading_cannot_reopen_batch(self):
        for value in (0.7, 0.2):
            self.args.guard.observe(
                {
                    "rate_limit_info": {
                        "unifiedWindows": {"five_hour": {"utilization": value}}
                    }
                }
            )
        with self.assertRaisesRegex(run.InfraError, "five_hour utilization 70.0%"):
            self.args.guard.before_run()

    def test_cold_batch_runs_one_probe_until_it_has_a_reading(self):
        first_started = threading.Event()
        second_entered = threading.Event()
        second_started = threading.Event()
        release = threading.Event()

        def agent(case, name, project, out, args):
            if out.name == "run-1":
                first_started.set()
                self.assertTrue(release.wait(3))
            else:
                second_started.set()
            return {"input_tokens": 0, "output_tokens": 0}, set()

        def second():
            second_entered.set()
            run.run_one(self.case, "none", None, 2, self.args)

        with (
            patch.object(run, "run_agent", side_effect=agent),
            ThreadPoolExecutor(2) as pool,
        ):
            one = pool.submit(run.run_one, self.case, "none", None, 1, self.args)
            try:
                self.assertTrue(first_started.wait(3))
                two = pool.submit(second)
                self.assertTrue(second_entered.wait(3))
                self.assertFalse(second_started.wait(0.1))
                self.args.guard.observe(
                    {
                        "rate_limit_info": {
                            "unifiedWindows": {"five_hour": {"utilization": 0.1}}
                        }
                    }
                )
                self.assertTrue(second_started.wait(3))
            finally:
                release.set()
            one.result()
            two.result()

    def test_codex_container_uses_label_and_tmpfs(self):
        self.args.agent = "codex"
        self.execute(CODEX_SUCCESS)
        cmd = next(c for c in self.commands if c[:2] == ("docker", "run"))
        self.assertIn("--label", cmd)
        self.assertIn("--tmpfs", cmd)
        self.assertEqual(
            cmd[cmd.index("--tmpfs") + 1].split(":")[0], f"{run.HOME}/.codex"
        )


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(
            patch.object(run, "BATCH_LOCK_DIR", self.home / ".cache/skills-eval")
        )
        self.enterContext(patch.object(run, "build_image"))
        self.enterContext(patch.dict(os.environ, {"HOME": str(self.home)}))
        auth = run.DEFAULT_CODEX_HOME.expanduser() / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text("{}")
        self.cli = [
            "run.py",
            "--out",
            str(self.home / "out"),
            "--agent",
            "codex",
            "--case",
            "flaky-tie-break",
            "--arm",
            "none",
            "--jobs",
            "1",
        ]

    def test_startup_removes_orphan_but_leaves_live_batch(self):
        orphan, active = "a" * 32, "b" * 32
        cache = self.home / ".cache/skills-eval"
        cache.mkdir(parents=True)
        calls = []

        def docker(*cmd, **kwargs):
            calls.append(cmd)
            listing = (
                f"orphan-id {orphan}\nlive-id {active}\n" if "--format" in cmd else ""
            )
            return subprocess.CompletedProcess(cmd, 0, listing, "")

        with (
            (cache / active).open("ab") as lock,
            patch.object(run, "sh", side_effect=docker),
            patch.object(sys, "argv", self.cli + ["--samples", "0"]),
        ):
            fcntl.flock(lock, fcntl.LOCK_EX)
            run.main()
        self.assertTrue(
            any(c[:3] == ("docker", "rm", "-f") and "orphan-id" in c for c in calls)
        )
        self.assertFalse(any("live-id" in c for c in calls))

    def test_ctrl_c_cancels_queued_jobs_and_cleans_active_containers(self):
        started, release = threading.Event(), threading.Event()
        jobs, calls = [], []

        def worker(case, arm, catalog, n, args):
            jobs.append(n)
            started.set()
            release.wait(1)

        def docker(*cmd, **kwargs):
            calls.append(cmd)
            listing = (
                "active-id\n"
                if cmd[:2] == ("docker", "ps") and started.is_set()
                else ""
            )
            if cmd[:3] == ("docker", "rm", "-f"):
                release.set()
            return subprocess.CompletedProcess(cmd, 0, listing, "")

        def interrupt(futures):
            self.assertEqual(len(futures), 3)
            self.assertTrue(started.wait(2))
            signal.raise_signal(signal.SIGINT)

        with (
            patch.object(run, "run_one", side_effect=worker),
            patch.object(run, "sh", side_effect=docker),
            patch.object(run, "as_completed", side_effect=interrupt),
            patch.object(sys, "argv", self.cli),
            self.assertRaises(KeyboardInterrupt),
        ):
            run.main()
        self.assertEqual(jobs, [1])
        self.assertIn(("docker", "rm", "-f", "active-id"), calls)


class TranscriptTests(unittest.TestCase):
    def test_evidence_accepts_error_then_turn_failed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            message = "Incomplete response returned, reason: max_output_tokens"
            (path / "trace-0.jsonl").write_text(
                jsonl(
                    THREAD,
                    {"type": "error", "message": message},
                    {"type": "turn.failed", "error": {"message": message}},
                )
            )
            (path / "timing.json").write_text('{"agent_errors": ["max_output_tokens"]}')
            (path / "checks.json").write_text("[]")
            (path / "final.md").write_text("")
            (path / "diff.patch").write_text("")
            self.assertIn(
                "session reported errors: max_output_tokens", grade.evidence(path)
            )

    def test_both_event_formats_and_partial_commands(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "trace-0.jsonl").write_text(
                jsonl(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {"type": "text", "text": "Investigating."},
                                {
                                    "type": "tool_use",
                                    "name": "Read",
                                    "input": {
                                        "file_path": "/home/node/.claude/skills/verify-work/SKILL.md",
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "content": "verification guidance",
                                },
                            ]
                        },
                    },
                )
            )
            cmd = {
                "type": "command_execution",
                "id": "item_0",
                "command": "cat ~/.agents/skills/ponytail/SKILL.md",
                "aggregated_output": "",
                "exit_code": None,
                "status": "in_progress",
            }
            (path / "trace-1.jsonl").write_text(
                jsonl(
                    {"type": "item.started", "item": cmd},
                    {
                        "type": "item.completed",
                        "item": dict(
                            cmd,
                            exit_code=0,
                            aggregated_output="style guidance",
                            status="completed",
                        ),
                    },
                    REPLY,
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "item_2",
                            "type": "file_change",
                            "status": "completed",
                            "changes": [{"path": "scheduler.py", "kind": "update"}],
                        },
                    },
                    {
                        "type": "item.started",
                        "item": dict(cmd, id="item_3", command="python -m unittest"),
                    },
                )
                + '{"truncated":'
            )
            transcript, skills = grade.condense(path)
        self.assertEqual(skills, {"ponytail", "verify-work"})
        self.assertIn("#1 AGENT: Investigating.", transcript)
        self.assertIn("#5 RESULT: exit 0 (completed)\nstyle guidance", transcript)
        self.assertIn("#6 AGENT: Fixed the tie-break.", transcript)
        self.assertIn(
            '#7 CALL: file_change {"changes": [{"path": "scheduler.py"', transcript
        )
        self.assertIn("#9 CALL: command_execution python -m unittest", transcript)
        self.assertNotIn("#10", transcript)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(self.enterContext(TemporaryDirectory()))
        self.daily_auth = self.home / ".codex/auth.json"
        self.daily_auth.parent.mkdir()
        self.daily_auth.write_text("synthetic daily login")
        self.enterContext(
            patch.dict(
                os.environ,
                {"HOME": str(self.home), "CODEX_HOME": str(self.daily_auth.parent)},
            )
        )

    def forbid_daily_auth_access(self, allow_lstat=False):
        def guarded(operation):
            def call(path, *args, **kwargs):
                if not isinstance(path, int) and Path(path) == self.daily_auth:
                    self.fail(f"{operation.__name__} accessed the daily auth file")
                return operation(path, *args, **kwargs)

            return call

        for module, name in (
            (os, "stat"),
            (os, "lstat"),
            (os, "open"),
            (builtins, "open"),
            (io, "open"),
        ):
            if allow_lstat and name == "lstat":
                continue
            self.enterContext(
                patch.object(module, name, guarded(getattr(module, name)))
            )

    def test_runner_copies_and_refreshes_only_eval_auth_and_redacts_results(self):
        self.forbid_daily_auth_access()
        home = run.DEFAULT_CODEX_HOME.expanduser()
        home.mkdir(parents=True)
        path = home / "auth.json"
        old_tokens = {
            "id_token": "synthetic-id+/==",
            "access_token": "synthetic-old/access",
            "refresh_token": "synthetic-refresh/token",
        }
        tokens = dict(old_tokens, access_token="synthetic-new/access")
        original = json.dumps({"tokens": old_tokens}).encode()
        refreshed = json.dumps(
            {"tokens": tokens, "last_refresh": "a new timestamp"}
        ).encode()
        path.write_bytes(original)
        path.chmod(0o644)
        inode = path.stat().st_ino

        supplied = set(old_tokens.values()) | set(tokens.values())
        escaped = {value.replace("/", r"\/") for value in supplied}
        notice = "Raw values " + " ".join(sorted(supplied))
        notice += " and slash escapes " + " ".join(sorted(escaped))
        reply = {
            "type": "item.completed",
            "item": dict(REPLY["item"], text=notice),
        }
        partial = '{"type":"item.started","item":{"text":"' + " ".join(sorted(escaped))
        stdout = jsonl(THREAD, reply, {"type": "turn.completed", "usage": {}}) + partial
        stderr = notice
        calls = []

        def docker(*cmd, **kwargs):
            calls.append(cmd)
            if cmd[-3:] == ("git", "rev-parse", "HEAD"):
                return subprocess.CompletedProcess(cmd, 0, "base123\n", "")
            if "git diff --cached" in cmd[-1]:
                return subprocess.CompletedProcess(cmd, 0, f"+{notice}", "")
            if "BASE_SHA=base123" in cmd:
                return subprocess.CompletedProcess(cmd, 0, notice, notice)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        def assert_login_locked():
            self.assertTrue(path.read_bytes() == original)
            with (
                (home / ".eval-auth.lock").open("ab") as other,
                self.assertRaises(BlockingIOError),
            ):
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def invoke(cmd, *, input, **kwargs):
            calls.append(tuple(cmd))
            assert_login_locked()
            if cmd[4] == "bash":
                self.assertIn(run.CODEX_AUTH, cmd[-1])
                self.assertEqual(input, original)
                self.assertIn("umask 077", cmd[-1])
                return subprocess.CompletedProcess(cmd, 0, b"")
            return subprocess.CompletedProcess(cmd, 0, stdout, stderr)

        def refresh(_name):
            assert_login_locked()
            return refreshed

        out = self.home / "out"
        cli = [
            "run.py",
            "--agent",
            "codex",
            "--out",
            str(out),
            "--arm",
            "none",
            "--case",
            "flaky-tie-break",
            "--samples",
            "1",
        ]
        with (
            patch.object(sys, "argv", cli),
            patch.object(run, "container_batch", return_value=nullcontext()),
            patch.object(run, "build_image"),
            patch.object(run, "sh", side_effect=docker),
            patch.object(run.subprocess, "run", side_effect=invoke) as exec_,
            patch.object(run, "copy_codex_auth_out", side_effect=refresh) as copy_out,
        ):
            run.main()
        self.assertEqual(exec_.call_count, 2)
        copy_out.assert_called_once()
        container = next(c for c in calls if c[:2] == ("docker", "run"))
        self.assertEqual(
            container[container.index("--tmpfs") + 1].split(":")[0], run.CODEX_HOME
        )
        self.assertTrue(path.read_bytes() == refreshed)
        self.assertNotEqual(path.stat().st_ino, inode)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

        results = out / "flaky-tie-break/none/run-1"
        for name in (
            "trace-0.jsonl",
            "final.md",
            "stderr-0.txt",
            "diff.patch",
            "checks.json",
        ):
            with self.subTest(artifact=name):
                content = (results / name).read_text()
                self.assertIn("[redacted]", content)
                self.assertFalse(any(value in content for value in supplied | escaped))
        for check in json.loads((results / "checks.json").read_text()):
            self.assertIn("[redacted]", check["output"])
            self.assertFalse(
                any(value in check["output"] for value in supplied | escaped)
            )
        evidence = grade.evidence(results)
        self.assertIn("+Raw values [redacted]", evidence)
        self.assertFalse(any(value in evidence for value in supplied | escaped))
        trace = (results / "trace-0.jsonl").read_text().splitlines()
        parsed_reply = json.loads(trace[1])["item"]["text"]
        self.assertEqual(trace[-1].count("[redacted]"), len(supplied))
        self.assertFalse(any(value in parsed_reply for value in supplied))
        self.assertEqual(parsed_reply.count("[redacted]"), 2 * len(supplied))

    def test_symlinked_eval_home_and_lock_are_rejected(self):
        home = self.home / "eval-home"
        home.mkdir()
        (home / "auth.json").write_text("{}")
        alias = self.home / "alias"
        alias.symlink_to(home)
        lock = home / ".eval-auth.lock"
        outside = self.home / "outside"
        with patch.object(run.subprocess, "run") as invoke:
            with (
                self.assertRaises(run.InfraError),
                run.codex_auth("container", set(), alias),
            ):
                pass
            lock.symlink_to(outside)
            with (
                self.assertRaises(run.InfraError),
                run.codex_auth("container", set(), home),
            ):
                pass
        invoke.assert_not_called()
        self.assertFalse(outside.exists())

    def test_refresh_writes_to_the_directory_opened_for_copy_in(self):
        home = self.home / "eval-home"
        home.mkdir()
        (home / "auth.json").write_bytes(b"{}")
        moved = self.home / "opened-home"
        updated = b'{"tokens":{"access_token":"synthetic-refresh"}}'
        with (
            patch.object(
                run.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
            patch.object(run, "copy_codex_auth_out", return_value=updated),
            run.codex_auth("container", set(), home),
        ):
            home.rename(moved)
            home.mkdir()
            (home / "auth.json").write_bytes(b"{}")
        self.assertEqual((home / "auth.json").read_bytes(), b"{}")
        self.assertEqual((moved / "auth.json").read_bytes(), updated)

    def test_refresh_rejects_a_symlinked_auth_destination(self):
        home = self.home / "eval-home"
        home.mkdir()
        auth = home / "auth.json"
        auth.write_bytes(b"{}")
        updated = b'{"tokens":{"access_token":"synthetic-refresh"}}'
        self.forbid_daily_auth_access()
        with (
            patch.object(
                run.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
            patch.object(run, "copy_codex_auth_out", return_value=updated),
            self.assertRaisesRegex(run.InfraError, "re-run the one-time eval login"),
            run.codex_auth("container", set(), home),
        ):
            auth.unlink()
            auth.symlink_to(self.daily_auth)
        self.assertTrue(auth.is_symlink())

    def test_invalid_token_refused_before_copy_in(self):
        home = self.home / "eval-home"
        home.mkdir()
        for invalid in ('with"quote', "with\\slash", "with whitespace", "café", "", 42):
            (home / "auth.json").write_text(
                json.dumps({"tokens": {"access_token": invalid}})
            )
            with (
                self.subTest(invalid=invalid),
                patch.object(run.subprocess, "run") as invoke,
                self.assertRaisesRegex(run.InfraError, "unsupported characters"),
                run.codex_auth("container", set(), home),
            ):
                self.fail("accepted token outside the redaction charset")
            invoke.assert_not_called()

    def test_missing_login_after_startup_stops_batch(self):
        home = self.home / "eval-home"
        home.mkdir()
        auth = home / "auth.json"
        auth.write_text("{}")
        run.prepare_login("codex", None, home)
        auth.unlink()
        guard = run.UsageGuard(0.6, 0.8)
        with (
            patch.object(run.subprocess, "run") as invoke,
            self.assertRaisesRegex(run.InfraError, "re-run the one-time eval login"),
            run.codex_auth("container", set(), home, guard),
        ):
            self.fail("invoked the agent without an eval login")
        invoke.assert_not_called()
        with self.assertRaisesRegex(run.InfraError, "skipped: Codex eval login"):
            guard.before_run()

    def test_judge_does_not_retry_when_the_container_login_disappears(self):
        home = self.home / "eval-home"
        home.mkdir()
        (home / "auth.json").write_bytes(b"{}")
        replies = [
            subprocess.CompletedProcess([], 0, b""),
            subprocess.CompletedProcess([], 1, "", ""),
        ]
        with (
            patch.object(run, "sh"),
            patch.object(grade.time, "sleep") as pause,
            patch.object(run.subprocess, "run", side_effect=replies) as invoke,
            patch.object(run, "copy_codex_auth_out", return_value=b"") as copy_out,
            self.assertRaisesRegex(run.InfraError, "re-run the one-time eval login"),
        ):
            grade.judge("Prompt.", grade.PAIR_SCHEMA, "model", "codex", codex_home=home)
        self.assertEqual(invoke.call_count, 2)
        copy_out.assert_called_once()
        pause.assert_not_called()
        self.assertEqual((home / "auth.json").read_bytes(), b"{}")

    def test_oversized_copy_out_keeps_existing_login(self):
        home = self.home / "eval-home"
        home.mkdir()
        auth = home / "auth.json"
        auth.write_text("{}")
        popen = subprocess.Popen

        def oversized_output(cmd, **kwargs):
            self.assertIn("head -c 65537", cmd[-1])
            return popen(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.buffer.write(b'{}' + b' ' * 65536)",
                ],
                **kwargs,
            )

        with (
            patch.object(
                run.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ),
            patch.object(
                run.subprocess, "Popen", side_effect=oversized_output
            ) as invoke,
            self.assertRaisesRegex(run.InfraError, "64 KiB"),
            run.codex_auth("container", set(), home),
        ):
            pass
        invoke.assert_called_once()
        self.assertEqual(auth.read_text(), "{}")

    def test_missing_eval_login_fails_before_either_batch(self):
        self.forbid_daily_auth_access()
        out = self.home / "out"
        for module, flags in (
            (run, ["--agent", "codex", "--arm", "none"]),
            (grade, ["--judge", "codex", "--codex-home", str(self.home / "custom")]),
        ):
            with (
                self.subTest(module=module.__name__),
                patch.object(sys, "argv", ["eval", "--out", str(out), *flags]),
                patch.object(run, "container_batch") as containers,
                self.assertRaisesRegex(run.InfraError, "Codex eval login.*CODEX_HOME="),
            ):
                module.main()
            containers.assert_not_called()
            self.assertFalse(out.exists())

    def test_cancel_worker_waiting_for_eval_auth_lock(self):
        home = run.DEFAULT_CODEX_HOME.expanduser()
        home.mkdir(parents=True)
        (home / "auth.json").write_text("{}")
        guard = run.UsageGuard(0.6, 0.8)
        waiting = threading.Event()
        flock = fcntl.flock

        def observe_contention(fd, flags):
            try:
                flock(fd, flags)
            except BlockingIOError:
                waiting.set()
                raise

        def worker():
            with run.codex_auth("container", set(), home, guard):
                self.fail("worker launched despite cancellation")

        with (
            patch.object(fcntl, "flock", side_effect=observe_contention),
            patch.object(run.subprocess, "run") as invoke,
            ThreadPoolExecutor(1) as pool,
            (home / ".eval-auth.lock").open("ab") as other,
        ):
            flock(other, fcntl.LOCK_EX)
            job = pool.submit(worker)
            try:
                self.assertTrue(waiting.wait(2))
            finally:
                guard.stop("batch interrupted")
            with self.assertRaisesRegex(run.InfraError, "batch interrupted"):
                job.result(timeout=2)
            invoke.assert_not_called()

    def test_daily_auth_aliases_are_rejected(self):
        home_alias = self.home / "alias"
        home_alias.symlink_to(self.daily_auth.parent)
        other_home = self.home / "other"
        other_home.mkdir()
        auth_alias = other_home / "auth.json"
        auth_alias.symlink_to(self.daily_auth)
        self.forbid_daily_auth_access()
        for home in (self.daily_auth.parent, home_alias, other_home):
            with self.subTest(home=home), self.assertRaises(run.InfraError):
                run.prepare_login("codex", None, home)

    def test_both_clis_reject_token_and_home_paths_inside_daily_codex(self):
        daily = self.daily_auth.parent
        child = daily / "eval-home"
        child.mkdir()
        (child / "auth.json").write_text("{}")
        alias = self.home / "alias"
        alias.symlink_to(daily)
        self.forbid_daily_auth_access(allow_lstat=True)
        for module, selector, extra in (
            (run, "--agent", ["--arm", "none"]),
            (grade, "--judge", []),
        ):
            for provider, option, path in (
                ("claude", "--token-file", self.daily_auth),
                ("claude", "--token-file", alias / "auth.json"),
                ("codex", "--codex-home", child),
                ("codex", "--codex-home", alias / child.name),
            ):
                cli = [
                    "eval",
                    "--out",
                    str(self.home / "out"),
                    *extra,
                    selector,
                    provider,
                    option,
                    str(path),
                ]
                with (
                    self.subTest(module=module.__name__, path=path),
                    patch.object(sys, "argv", cli),
                    patch.object(
                        run,
                        "container_batch",
                        side_effect=AssertionError("batch started"),
                    ),
                    self.assertRaisesRegex(
                        run.InfraError, "outside the daily Codex home"
                    ),
                ):
                    module.main()


class JudgeTests(unittest.TestCase):
    def test_claude_hard_limit_on_stderr_is_never_retried(self):
        success = json.dumps({"structured_output": {"better": "tie"}})
        diagnostic = "usage_limit_reached"
        for outcome in (
            subprocess.CompletedProcess([], 0, success, diagnostic),
            subprocess.TimeoutExpired("claude", 900, stderr=diagnostic.encode()),
        ):
            with (
                self.subTest(outcome=outcome),
                patch.object(grade.time, "sleep") as pause,
                patch.object(grade.subprocess, "run", side_effect=[outcome]) as invoke,
                self.assertRaisesRegex(run.InfraError, "usage limit reached"),
            ):
                grade.judge("Prompt.", grade.PAIR_SCHEMA, "model", "claude")
            invoke.assert_called_once()
            pause.assert_not_called()

    def test_workspace_limits_are_never_retried(self):
        for message in WORKSPACE_LIMITS:
            with (
                self.subTest(message=message),
                patch.object(run, "sh"),
                patch.object(run, "codex_auth", return_value=nullcontext()),
                patch.object(grade.time, "sleep") as pause,
                patch.object(
                    grade.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        [], 1, jsonl(THREAD, {"type": "error", "message": message}), ""
                    ),
                ) as invoke,
            ):
                with self.assertRaises(run.InfraError):
                    grade.judge("Prompt.", grade.PAIR_SCHEMA, "model", "codex")
                invoke.assert_called_once()
                pause.assert_not_called()

    def test_partial_workspace_limit_on_timeout_is_never_retried(self):
        for output, stderr in (
            (jsonl({"type": "error", "message": WORKSPACE_LIMITS[1]}).encode(), None),
            (b'{"type":"error","message":"Your workspace is out of credits.', None),
            (None, WORKSPACE_LIMITS[0].encode()),
        ):
            timeout = subprocess.TimeoutExpired(
                "codex", 900, output=output, stderr=stderr
            )
            with (
                self.subTest(output=output, stderr=stderr),
                patch.object(run, "sh") as shell,
                patch.object(run, "codex_auth", return_value=nullcontext()),
                patch.object(grade.time, "sleep") as pause,
                patch.object(grade.subprocess, "run", side_effect=timeout) as invoke,
                self.assertRaisesRegex(run.InfraError, "usage limit reached"),
            ):
                grade.judge("Prompt.", grade.PAIR_SCHEMA, "model", "codex")
            self.assertTrue(
                any(run.KILL_AGENT in call.args for call in shell.call_args_list)
            )
            invoke.assert_called_once()
            pause.assert_not_called()

    def test_judge_auth_failure_is_never_retried(self):
        home = Path("/synthetic/eval-home")
        failure = subprocess.CompletedProcess([], 1, "", EXPIRED_REFRESH)
        with (
            patch.object(run, "sh"),
            patch.object(run, "codex_auth", return_value=nullcontext()) as auth,
            patch.object(grade.time, "sleep") as pause,
            patch.object(grade.subprocess, "run", return_value=failure) as invoke,
            self.assertRaisesRegex(run.InfraError, "CODEX_HOME=/synthetic/eval-home"),
        ):
            grade.judge("Prompt.", grade.PAIR_SCHEMA, "model", "codex", codex_home=home)
        self.assertEqual(auth.call_args.args[-1], home)
        invoke.assert_called_once()
        pause.assert_not_called()

    def test_codex_verdict_is_structured_and_judge_is_read_only(self):
        verdict = {"better": "tie", "reasons": "Equal outcomes."}
        reply = {
            "type": "item.completed",
            "item": dict(
                REPLY["item"],
                text=json.dumps(verdict),
            ),
        }
        stdout = jsonl(THREAD, reply, {"type": "turn.completed", "usage": {}})
        with (
            patch.object(run, "sh") as shell,
            patch.object(run, "codex_auth", return_value=nullcontext()),
            patch.object(
                grade.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    [],
                    0,
                    stdout,
                    "",
                ),
            ) as invoke,
        ):
            self.assertEqual(
                grade.judge_once(
                    "Choose a winner.", grade.PAIR_SCHEMA, "model", "codex"
                ),
                verdict,
            )
        self.assertEqual(invoke.call_args.kwargs["input"], "Choose a winner.")
        cmd = invoke.call_args.args[0]
        self.assertIn("--output-schema", cmd)
        self.assertIn("read-only", cmd)
        self.assertIn("shell_tool", cmd)
        self.assertIn("--ignore-user-config", cmd)
        self.assertEqual(shell.call_args.args[:3], ("docker", "rm", "-f"))

    def test_pairwise_uses_both_orders_with_selected_provider(self):
        a, b = Path("arm-a"), Path("arm-b")
        case = {"brief": "Fix the bug.", "assertions": {}}
        with (
            patch.object(grade, "evidence", side_effect=lambda path: path.name.upper()),
            patch.object(
                grade,
                "judge",
                side_effect=[
                    {"better": "1"},
                    {"better": "2"},
                ],
            ) as judge,
        ):
            winner = grade.compare(
                case,
                a,
                b,
                "model",
                SimpleNamespace(random=lambda: 0.0),
                "codex",
            )
        self.assertEqual(winner, "a")
        first, second = (call.args for call in judge.call_args_list)
        self.assertIn("SUBMISSION 1 ---\nARM-A", first[0])
        self.assertIn("SUBMISSION 1 ---\nARM-B", second[0])
        self.assertEqual(first[-1], second[-1])
        self.assertEqual(first[-1], "codex")
