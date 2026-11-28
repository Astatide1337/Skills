"""Run each case autonomously in a fresh container and save what happened.

    python evals/run.py --token-file F --out DIR --arm none --arm current=HEAD [--case ID ...]

An arm is `none` (no skills or global instructions) or `NAME=GIT_REF` (the
catalog and global instructions at that ref). Results use the agentskills.io
layout: DIR/<case>/<arm>/run-<n>/{trace-*.jsonl, final.md, diff.patch, checks.json, timing.json}.
Only the case's `repo/` enters the container before the run; the brief arrives
as the user's message and hidden `checks/` are copied in after the agent stops.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases"
IMAGE = "skills-autonomous-eval"
HOME = "/home/node"
# API errors the agent itself caused; they are graded outcomes. Every other API
# error (usage limit, auth, network, outage, ...) means the run could not happen.
AGENT_ERRORS = {
    "max_output_tokens",
    "prompt_too_long",
    "autocompact_thrashing",
    "empty_completion",
    "malformed_tool_use_exhausted",
    "safety_monitor_blocked",
}
USAGE_LIMIT = threading.Event()
# Stops this run's own agent process; skips the shell running the loop.
KILL_AGENT = (
    'for p in /proc/[0-9]*; do [ "${p#/proc/}" = "$$" ] && continue; '
    'grep -qa claude "$p/cmdline" 2>/dev/null && kill "${p#/proc/}" 2>/dev/null; done; true'
)


class InfraError(RuntimeError):
    """The run could not happen; leave it unfinished so a rerun repeats it."""


def is_infra(event: dict) -> bool:
    if event.get("api_error") in AGENT_ERRORS:
        return False
    return bool(event.get("api_error") or event.get("api_error_status"))


def parse_event(line: str) -> dict:
    """One stream-json event; a line cut off by a timeout kill is skipped."""
    try:
        event = json.loads(line)
    except ValueError:
        return {}
    return event if isinstance(event, dict) else {}


def sh(
    *args: str, check: bool = True, timeout: int = 120
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=check
    )


def build_image() -> None:
    subprocess.run(
        ["docker", "build", "-q", "-t", IMAGE, str(ROOT / "evals")],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def load_case(case_dir: Path) -> dict:
    case = yaml.safe_load((case_dir / "case.yaml").read_text())
    case["id"] = case_dir.name
    case["dir"] = case_dir
    return case


def export_arm(ref: str, dest: Path) -> None:
    """Materialize skills/ and global instructions from a git ref."""
    archive = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            ref,
            "skills",
            "global-instructions/AGENTS.md",
        ],
        check=True,
        capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def run_one(case: dict, arm: str, catalog: Path | None, n: int, args) -> None:
    out = args.out / case["id"] / arm / f"run-{n}"
    if (out / "timing.json").exists():
        return  # finished earlier; rerunning would overwrite evidence
    if USAGE_LIMIT.is_set():
        raise InfraError("skipped: usage limit reached earlier in this batch")
    out.mkdir(parents=True, exist_ok=True)
    name = f"skills-eval-{uuid.uuid4().hex[:10]}"
    project = f"{HOME}/{case['project']}"
    exec_ = ["docker", "exec", "-w", project, name]
    sh(
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-e",
        "CLAUDE_CODE_OAUTH_TOKEN",
        IMAGE,
        "sleep",
        "infinity",
    )
    try:
        sh("docker", "cp", f"{case['dir']}/repo/.", f"{name}:{project}")
        if catalog is not None:
            sh("docker", "exec", name, "mkdir", "-p", f"{HOME}/.claude")
            sh("docker", "cp", f"{catalog}/skills", f"{name}:{HOME}/.claude/skills")
            sh(
                "docker",
                "cp",
                f"{catalog}/global-instructions/AGENTS.md",
                f"{name}:{HOME}/.claude/CLAUDE.md",
            )
        sh("docker", "exec", "-u", "root", name, "chown", "-R", "node:node", HOME)
        setup = case.get("setup", "")
        sh(
            *exec_,
            "bash",
            "-c",
            f"{setup}\ngit init -q && git add -A && git commit -qm 'initial import'",
            timeout=300,
        )
        # Pin the starting commit: an agent may amend or rebase the root commit.
        base = sh(*exec_, "git", "rev-parse", "HEAD").stdout.strip()

        session, totals = (
            None,
            {
                "cost_usd": 0.0,
                "turns": 0,
                "duration_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "agent_errors": [],
                "timed_out": False,
                "wall_seconds": 0.0,
                # False when a turn was killed: its tokens and cost were never reported.
                "usage_complete": True,
            },
        )
        messages = [case["brief"], *case.get("turns", [])]
        final = []
        for i, message in enumerate(messages):
            cmd = [
                "docker",
                "exec",
                "-i",
                "-w",
                project,
                name,
                "claude",
                "-p",
                "--model",
                args.model,
                "--output-format",
                "stream-json",
                "--verbose",
                "--dangerously-skip-permissions",
            ]
            if session:
                cmd += ["--resume", session]
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    cmd,
                    input=message,
                    capture_output=True,
                    text=True,
                    timeout=args.turn_timeout,
                    check=False,
                )
                stdout, stderr, returncode = proc.stdout, proc.stderr, proc.returncode
            except subprocess.TimeoutExpired as exc:
                # The agent ran out of time: keep what it did and grade that.
                sh("docker", "exec", name, "bash", "-c", KILL_AGENT, check=False)
                stdout, stderr = (
                    x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
                    for x in (exc.stdout, exc.stderr)
                )
                returncode, totals["timed_out"], totals["usage_complete"] = (
                    None,
                    True,
                    False,
                )
            totals["wall_seconds"] += round(time.monotonic() - started, 1)
            (out / f"trace-{i}.jsonl").write_text(stdout)
            if stderr.strip():
                (out / f"stderr-{i}.txt").write_text(stderr)
            got_result = False
            for line in stdout.splitlines():
                event = parse_event(line)
                session = event.get("session_id", session)
                if event.get("type") == "result":
                    got_result = True
                    if is_infra(event):
                        if event.get("api_error") == "usage_limit_reached":
                            USAGE_LIMIT.set()
                        raise InfraError(
                            f"API error in turn {i}: {event.get('result')}"
                        )
                    if event.get("api_error"):
                        totals["agent_errors"].append(event["api_error"])
                    final.append(f"## Turn {i}\n\n{event.get('result', '')}")
                    totals["cost_usd"] += event.get("total_cost_usd") or 0
                    totals["turns"] += event.get("num_turns") or 0
                    totals["duration_ms"] += event.get("duration_ms") or 0
                    usage = event.get("usage") or {}
                    for key in ("input_tokens", "output_tokens"):
                        totals[key] += usage.get(key) or 0
                    totals["input_tokens"] += (
                        usage.get("cache_read_input_tokens") or 0
                    ) + (usage.get("cache_creation_input_tokens") or 0)
            if totals["timed_out"]:
                final.append(
                    f"## Turn {i}\n\n[stopped after {args.turn_timeout}s without finishing]"
                )
                break
            if not got_result:
                raise InfraError(
                    f"turn {i} ended without a result (exit {returncode}): {stderr[-500:]}"
                )
        (out / "final.md").write_text("\n\n".join(final))

        diff = sh(
            *exec_,
            "bash",
            "-c",
            f"git add -A && git diff --cached {base} && git log --oneline {base}..HEAD "
            "&& git status --short",
        )
        (out / "diff.patch").write_text(diff.stdout)
        checks = []
        if (case["dir"] / "checks").is_dir():
            sh("docker", "cp", f"{case['dir']}/checks/.", f"{name}:{HOME}/.grader")
            sh(
                "docker",
                "exec",
                "-u",
                "root",
                name,
                "chown",
                "-R",
                "node:node",
                f"{HOME}/.grader",
            )
        for check in case.get("checks", []):
            result = sh(
                "docker",
                "exec",
                "-e",
                f"BASE_SHA={base}",
                "-w",
                project,
                name,
                "bash",
                "-c",
                check["run"],
                check=False,
                timeout=300,
            )
            checks.append(
                {
                    "name": check["name"],
                    "passed": result.returncode == 0,
                    "output": (result.stdout + result.stderr)[-2000:],
                }
            )
        (out / "checks.json").write_text(json.dumps(checks, indent=2))
        totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
        (out / "timing.json").write_text(json.dumps(totals, indent=2))
    finally:
        sh("docker", "rm", "-f", name, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        required=True,
        help="file holding a `claude setup-token` token",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--arm", action="append", required=True, help="none, or NAME=GIT_REF"
    )
    parser.add_argument("--case", action="append", help="case id (default: all)")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--turn-timeout", type=int, default=1800)
    args = parser.parse_args()

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = args.token_file.read_text().strip()
    build_image()
    cases = (
        [load_case(CASES / c) for c in args.case]
        if args.case
        else [
            load_case(d) for d in sorted(CASES.iterdir()) if (d / "case.yaml").is_file()
        ]
    )
    staging = Path(tempfile.mkdtemp(prefix="skills-eval-arms-"))
    try:
        arms: dict[str, Path | None] = {}
        for spec in args.arm:
            if spec == "none":
                arms["none"] = None
            else:
                arm, ref = spec.split("=", 1)
                (staging / arm).mkdir()
                export_arm(ref, staging / arm)
                arms[arm] = staging / arm
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(
            json.dumps(
                {
                    "model": args.model,
                    "arms": args.arm,
                    "samples": args.samples,
                    "cases": [c["id"] for c in cases],
                    "image": IMAGE,
                },
                indent=2,
            )
        )
        jobs = [
            (c, a, p, n)
            for c in cases
            for a, p in arms.items()
            for n in range(1, args.samples + 1)
        ]
        with ThreadPoolExecutor(args.jobs) as pool:
            futures = {pool.submit(run_one, *job, args): job for job in jobs}
            for future, (case, arm, _, n) in futures.items():
                try:
                    future.result()
                    print(f"done {case['id']}/{arm}/run-{n}", flush=True)
                except (
                    OSError,
                    subprocess.SubprocessError,
                    ValueError,
                    RuntimeError,
                ) as exc:  # a rerun resumes missing runs
                    print(f"FAILED {case['id']}/{arm}/run-{n}: {exc!r}", flush=True)
    finally:
        shutil.rmtree(staging)


if __name__ == "__main__":
    main()
