"""Offline coverage for the autonomous runners and shared judge transcript."""

import json
import subprocess
import unittest
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from evals import grade, run


def jsonl(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


THREAD = {"type": "thread.started", "thread_id": "codex-thread"}
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
        timing = self.execute(CODEX_SUCCESS, followup, catalog=Path("/catalog"))
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
        self.assertTrue(any(p.endswith("/.codex/AGENTS.md") for p in copies))

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


class TranscriptTests(unittest.TestCase):
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
    @staticmethod
    def auth(account, access):
        return json.dumps(
            {
                "tokens": {
                    "account_id": account,
                    "access_token": access,
                    "refresh_token": "fake-refresh",
                    "id_token": "fake-id",
                }
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
            self.assertEqual(transfer.call_args_list[0].kwargs["input"], original)
            self.assertEqual(path.read_bytes(), updated)
            self.assertNotEqual(path.stat().st_ino, inode)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                run.redact("fake-original and fake-updated", secrets),
                "[redacted] and [redacted]",
            )
            run.save_refreshed_auth(path, original, self.auth("one", "stale-worker"))
            self.assertEqual(path.read_bytes(), updated)


class JudgeTests(unittest.TestCase):
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
