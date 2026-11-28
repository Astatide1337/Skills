"""Offline coverage for the autonomous runners and shared judge transcript."""

import base64
import fcntl
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

    def execute(self, *outputs, catalog=None):
        def invoke(cmd, **kwargs):
            self.commands.append(tuple(cmd))
            outcome = next(events)
            if isinstance(outcome, BaseException):
                raise outcome
            stdout, code = outcome if isinstance(outcome, tuple) else (outcome, 0)
            return subprocess.CompletedProcess(cmd, code, stdout, "")

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
                if failure == "limit":
                    with self.assertRaisesRegex(run.InfraError, "skipped"):
                        self.args.guard.before_run()
                else:
                    self.args.guard.before_run()

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
        self.enterContext(patch.dict(os.environ, {"CODEX_HOME": ""}))

    @staticmethod
    def jwt(account, marker, user="user-123"):
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sub": user,
                        "https://api.openai.com/auth": {
                            "chatgpt_account_id": account,
                            "chatgpt_user_id": user,
                        },
                    }
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        return f"eyJhbGciOiJSUzI1NiJ9.{payload}.{marker}"

    @classmethod
    def auth(cls, account, access):
        return json.dumps(
            {
                "auth_mode": "chatgpt",
                "tokens": {
                    "account_id": account,
                    "access_token": cls.jwt(account, access),
                    "refresh_token": "fake-refresh",
                    "id_token": cls.jwt(account, "fake-id"),
                },
                "last_refresh": "2026-11-27T00:00:00Z",
            }
        ).encode()

    def test_refresh_round_trip_writes_only_changed_same_account_auth(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".codex/auth.json"
            path.parent.mkdir()
            original = self.auth("one", "fake-original")
            updated = self.auth("one", "fake-updated")
            path.write_bytes(original)
            path.chmod(0o644)
            inode = path.stat().st_ino
            for candidate in (original, b"invalid JSON", self.auth("two", "other")):
                run.save_refreshed_auth(path, original, candidate)
                self.assertEqual(path.stat().st_ino, inode)
            with (
                patch.object(Path, "home", return_value=home),
                patch.object(
                    run.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0, b"", b""),
                        subprocess.CompletedProcess([], 0, updated, b""),
                    ],
                ) as transfer,
            ):
                secrets = set()
                with run.codex_auth("container", secrets):
                    self.assertEqual(path.read_bytes(), original)
            self.assertEqual(
                json.loads(transfer.call_args_list[0].kwargs["input"]),
                json.loads(original),
            )
            self.assertEqual(json.loads(path.read_bytes()), json.loads(updated))
            self.assertNotEqual(path.stat().st_ino, inode)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                run.redact(
                    f"{self.jwt('one', 'fake-original')} and {self.jwt('one', 'fake-updated')}",
                    secrets,
                ),
                "[redacted] and [redacted]",
            )
            run.save_refreshed_auth(path, original, self.auth("one", "stale-worker"))
            self.assertEqual(json.loads(path.read_bytes()), json.loads(updated))

    def test_login_racing_the_replace_wins(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            original = self.auth("one", "old")
            login = self.auth("two", "new-login")
            path.write_bytes(original)
            replace = Path.replace

            def host_login():
                return subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        """
import fcntl, os, pathlib, sys
path = pathlib.Path(sys.argv[1])
with path.with_suffix(".json.lock").open("ab") as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(75)
    pending = path.with_suffix(".login")
    pending.write_bytes(sys.stdin.buffer.read())
    os.replace(pending, path)
""",
                        str(path),
                    ],
                    input=login,
                    timeout=3,
                    check=False,
                ).returncode

            def race(pending, target):
                status.append(host_login())
                return replace(pending, target)

            status = []
            with patch.object(Path, "replace", race):
                run.save_refreshed_auth(path, original, self.auth("one", "rotated"))
            self.assertEqual(len(status), 1)
            if status[0] == 75:
                self.assertEqual(host_login(), 0)
            self.assertEqual(path.read_bytes(), login)

    def test_damaged_or_mismatched_refresh_cannot_replace_host(self):
        original = self.auth("one", "old")
        valid = self.auth("one", "rotated")
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            for outer, tokens in (
                ({"last_refresh": "yesterday"}, {}),
                ({"auth_mode": "apikey"}, {}),
                ({"OPENAI_API_KEY": 42}, {}),
                ({}, {"access_token": self.jwt("two", "wrong-account")}),
                ({}, {"id_token": self.jwt("one", "wrong-user", "another-user")}),
                ({}, {"refresh_token": "invalid refresh token"}),
                ({}, {"login_owner_id": 42}),
                ({}, {"oauth_provenance": {"issuer": "https://example.test"}}),
            ):
                with self.subTest(fields=tuple(outer) + tuple(tokens)):
                    path.write_bytes(original)
                    candidate = json.loads(valid)
                    candidate.update(outer)
                    candidate["tokens"].update(tokens)
                    run.save_refreshed_auth(
                        path, original, json.dumps(candidate).encode()
                    )
                    self.assertEqual(path.read_bytes(), original)

    def test_transfer_allowlists_login_and_redacts_every_token(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            path = home / ".codex/auth.json"
            path.parent.mkdir()
            original = json.loads(self.auth("one", "original"))
            original.update(
                {
                    "OPENAI_API_KEY": "fake-api",
                    "personal_access_token": "fake-pat",
                    "agent_identity": "fake-agent",
                }
            )
            path.write_text(json.dumps(original))
            updated = self.auth("one", "rotated")
            with (
                patch.object(Path, "home", return_value=home),
                patch.object(
                    run.subprocess,
                    "run",
                    side_effect=[
                        subprocess.CompletedProcess([], 0, b"", b""),
                        subprocess.CompletedProcess([], 0, updated, b""),
                    ],
                ) as transfer,
            ):
                secrets = set()
                with run.codex_auth("container", secrets):
                    pass
            supplied = json.loads(transfer.call_args_list[0].kwargs["input"])
            self.assertEqual(set(supplied), {"auth_mode", "tokens", "last_refresh"})
            for field in ("access_token", "id_token", "refresh_token"):
                self.assertEqual(
                    run.redact(supplied["tokens"][field], secrets), "[redacted]"
                )
            stored = json.loads(path.read_bytes())
            self.assertEqual(stored["tokens"], json.loads(updated)["tokens"])
            self.assertEqual(stored["OPENAI_API_KEY"], original["OPENAI_API_KEY"])
            self.assertEqual(
                stored["personal_access_token"], original["personal_access_token"]
            )


class JudgeTests(unittest.TestCase):
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
