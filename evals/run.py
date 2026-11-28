"""Run each case autonomously in a fresh container and save what happened.

    python evals/run.py --agent claude --token-file F --out DIR --arm none --arm current=HEAD

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases"
IMAGE = "skills-autonomous-eval"
HOME = "/home/node"
DEFAULT_MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-5.6-luna"}
CODEX_AUTH = f"{HOME}/.codex/auth.json"
AUTH_LOCK = threading.Lock()
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
# The container is dedicated to this run. Kill the agent and its tools, leaving PID 1.
KILL_AGENT = "kill -KILL -1 2>/dev/null || true"


class InfraError(RuntimeError):
    """The run could not happen; leave it unfinished so a rerun repeats it."""


class UsageGuard:
    def __init__(self, five_hour: float, seven_day: float):
        self.thresholds = {"five_hour": five_hour, "seven_day": seven_day}
        self.windows: dict[str, float] = {}
        self.limited = False
        self.lock = threading.Lock()

    def observe(self, event: dict) -> None:
        info = event.get("rate_limit_info") or {}
        with self.lock:
            self.limited |= info.get("status") == "rejected"
            for window, data in (info.get("unifiedWindows") or {}).items():
                value = data.get("utilization") if isinstance(data, dict) else None
                if (
                    window in self.thresholds
                    and isinstance(value, (int, float))
                    and 0 <= value <= 1
                ):
                    self.windows[window] = value

    def stop(self) -> None:
        with self.lock:
            self.limited = True

    def progress(self) -> str:
        with self.lock:
            return ", ".join(
                f"{window}={self.windows[window]:.1%}"
                if window in self.windows
                else f"{window}=unknown"
                for window in self.thresholds
            )

    def before_run(self) -> None:
        with self.lock:
            if self.limited:
                raise InfraError("skipped: usage limit reached earlier in this batch")
            for window, value in self.windows.items():
                if value >= self.thresholds[window]:
                    raise InfraError(
                        f"skipped: {window} utilization {value:.1%} reached its threshold"
                    )


def fraction(raw: str) -> float:
    value = float(raw)
    if not 0 <= value <= 1:
        raise argparse.ArgumentTypeError("expected a fraction between 0 and 1")
    return value


def auth_tokens(raw: bytes) -> dict:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        return {}
    tokens = data.get("tokens") if isinstance(data, dict) else None
    return tokens if isinstance(tokens, dict) else {}


def save_refreshed_auth(path: Path, original: bytes, updated: bytes) -> None:
    if updated == original or path.read_bytes() != original:
        return
    before, after = auth_tokens(original), auth_tokens(updated)
    account = before.get("account_id")
    if (
        not account
        or after.get("account_id") != account
        or not all(
            isinstance(after.get(key), str) and after[key]
            for key in ("access_token", "refresh_token", "id_token")
        )
    ):
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        pending = Path(tmp.name)
        try:
            tmp.write(updated)
            tmp.close()
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)


@contextmanager
def codex_auth(name: str, secrets: set[str]):
    """Install auth for one invocation. The caller holds AUTH_LOCK."""
    path = (Path.home() / ".codex" / "auth.json").resolve()

    def transfer(command: str, data: bytes | None = None) -> bytes:
        proc = subprocess.run(
            ["docker", "exec", "-i", name, "bash", "-c", command],
            input=data,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if proc.returncode:
            raise InfraError("Codex auth transfer failed")
        return proc.stdout

    def remember(raw: bytes) -> None:
        secrets.update(
            value
            for key, value in auth_tokens(raw).items()
            if key.endswith("_token") and isinstance(value, str) and value
        )

    original = path.read_bytes()
    if not auth_tokens(original).get("account_id"):
        raise InfraError("Codex auth.json needs a ChatGPT login with an account id")
    remember(original)
    transfer(
        f"umask 077; mkdir -p ~/.codex && tmp=$(mktemp ~/.codex/auth.XXXXXX) "
        f'&& cat > "$tmp" && mv -fT "$tmp" "{CODEX_AUTH}"',
        original,
    )
    try:
        yield
    finally:
        updated = transfer(
            f'p="{CODEX_AUTH}"; if [ -f "$p" ] && [ ! -L "$p" ]; then head -c 65536 "$p"; fi; rm -f "$p"'
        )
        remember(updated)
        save_refreshed_auth(path, original, updated)


def redact(text: str, secrets: set[str]) -> str:
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return text


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
        ["docker", "build", "-q", "-t", IMAGE, "-"],
        input=(ROOT / "evals" / "Dockerfile").read_bytes(),
        check=True,
        stdout=subprocess.DEVNULL,
    )


def codex_exec(model: str, session: str | None = None) -> list[str]:
    cmd = ["codex", "exec"]
    if session:
        cmd += ["resume", session]
    return cmd + [
        "--json",
        "--skip-git-repo-check",
        "-m",
        model,
        "-c",
        'cli_auth_credentials_store="file"',
        "-c",
        "skills.bundled.enabled=false",
        "-c",
        "cloud.skills.enabled=false",
        "--disable",
        "apps",
    ]


def codex_error(message: str) -> str | None:
    message = message.lower()
    if "ran out of room in the model's context window" in message:
        return "prompt_too_long"
    if "reason: max_output_tokens" in message:
        return "max_output_tokens"
    if "reason: content_filter" in message:
        return "safety_monitor_blocked"
    if "hit your usage limit" in message or "usage_limit_reached" in message:
        return "usage_limit_reached"
    return None


def codex_result(events: list[dict]) -> tuple[str | None, dict | None]:
    session, result, failure, reply = None, None, None, ""
    for event in events:
        kind = event.get("type")
        if kind == "thread.started":
            session = event["thread_id"]
        elif kind == "item.completed" and event["item"]["type"] == "agent_message":
            reply = event["item"]["text"]
        elif kind == "turn.completed":
            result = {"result": reply, "num_turns": 1, "usage": event["usage"]}
        elif kind in ("turn.failed", "error"):
            message = (event.get("error") or event).get("message", "")
            failure = {
                "result": message,
                "num_turns": 1,
                "api_error": codex_error(message) or "codex_error",
            }
            if kind == "turn.failed":
                return session, failure
    return session, result or failure


def record_turn(
    stdout: str,
    stderr: str,
    returncode: int | None,
    index: int,
    session: str | None,
    totals: dict,
    final: list[str],
    args,
) -> str | None:
    events = [parse_event(line) for line in stdout.splitlines()]
    if args.agent == "codex":
        thread, result = codex_result(events)
        session = thread or session
        results = [result] if result is not None else []
        if returncode and result is not None and not result.get("api_error"):
            raise InfraError(f"Codex exited {returncode} after reporting completion")
    else:
        results = []
        for event in events:
            session = event.get("session_id", session)
            if event.get("type") == "rate_limit_event":
                args.guard.observe(event)
            elif event.get("type") == "result":
                results.append(event)
    for result in results:
        if is_infra(result):
            if result.get("api_error") == "usage_limit_reached":
                args.guard.stop()
            raise InfraError(f"API error in turn {index}: {result.get('result')}")
        if result.get("api_error"):
            totals["agent_errors"].append(result["api_error"])
        final.append(f"## Turn {index}\n\n{result.get('result', '')}")
        totals["turns"] += result.get("num_turns") or 0
        usage = result.get("usage") or {}
        if args.agent == "claude":
            totals["cost_usd"] += result.get("total_cost_usd") or 0
            totals["duration_ms"] += result.get("duration_ms") or 0
            totals["input_tokens"] += sum(
                usage.get(key) or 0
                for key in (
                    "input_tokens",
                    "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                )
            )
            totals["output_tokens"] += usage.get("output_tokens") or 0
        elif usage:
            # Exec reports thread totals, including cached input and reasoning output.
            for key in ("input_tokens", "output_tokens"):
                totals[key] = usage[key]
        else:
            totals["usage_complete"] = False
    if totals["timed_out"]:
        final.append(
            f"## Turn {index}\n\n[stopped after {args.turn_timeout}s without finishing]"
        )
    elif not results or (args.agent == "codex" and not session):
        if args.agent == "codex" and codex_error(stderr) == "usage_limit_reached":
            args.guard.stop()
        raise InfraError(
            f"turn {index} ended without a result (exit {returncode}): {stderr[-500:]}"
        )
    return session


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


def run_agent(
    case: dict, name: str, project: str, out: Path, args
) -> tuple[dict, set[str]]:
    session, totals = (
        None,
        {
            "cost_usd": 0.0 if args.agent == "claude" else None,
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
    secrets: set[str] = set()
    token = (
        os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") if args.agent == "claude" else None
    )
    if token:
        secrets.add(token)
    # Keep auth and the quota decision ordered across Codex workers.
    with AUTH_LOCK if args.agent == "codex" else nullcontext():
        args.guard.before_run()
        for pattern in ("trace-*.jsonl", "stderr-*.txt"):
            for path in out.glob(pattern):
                path.unlink()
        for i, message in enumerate(messages):
            cmd = ["docker", "exec", "-i", "-w", project, name]
            if args.agent == "claude":
                cmd += [
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
            else:
                cmd += codex_exec(args.model, session) + [
                    "--dangerously-bypass-approvals-and-sandbox",
                    "-",
                ]
            auth = codex_auth(name, secrets) if args.agent == "codex" else nullcontext()
            with auth:
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
                    stdout, stderr, returncode = (
                        proc.stdout,
                        proc.stderr,
                        proc.returncode,
                    )
                except subprocess.TimeoutExpired as exc:
                    # Keep the partial trace, then grade only after the tools have stopped.
                    sh("docker", "exec", name, "bash", "-c", KILL_AGENT)
                    stdout, stderr = (
                        x.decode(errors="replace")
                        if isinstance(x, bytes)
                        else (x or "")
                        for x in (exc.stdout, exc.stderr)
                    )
                    returncode = None
                    totals["timed_out"] = True
                    totals["usage_complete"] = False
                elapsed = time.monotonic() - started
                totals["wall_seconds"] += round(elapsed, 1)
                if args.agent == "codex":
                    totals["duration_ms"] += round(elapsed * 1000)
            stdout, stderr = redact(stdout, secrets), redact(stderr, secrets)
            (out / f"trace-{i}.jsonl").write_text(stdout)
            stderr_path = out / f"stderr-{i}.txt"
            if stderr.strip():
                stderr_path.write_text(stderr)
            else:
                stderr_path.unlink(missing_ok=True)
            session = record_turn(
                stdout, stderr, returncode, i, session, totals, final, args
            )
            if totals["timed_out"]:
                break
    (out / "final.md").write_text("\n\n".join(final))
    return totals, secrets


def run_one(case: dict, arm: str, catalog: Path | None, n: int, args) -> None:
    out = args.out / case["id"] / arm / f"run-{n}"
    if (out / "timing.json").exists():
        return  # finished earlier; rerunning would overwrite evidence
    args.guard.before_run()
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
        *(["-e", "CLAUDE_CODE_OAUTH_TOKEN"] if args.agent == "claude" else []),
        IMAGE,
        "sleep",
        "infinity",
    )
    try:
        sh("docker", "cp", f"{case['dir']}/repo/.", f"{name}:{project}")
        if catalog is not None:
            skills, instructions = {
                "claude": (f"{HOME}/.claude/skills", f"{HOME}/.claude/CLAUDE.md"),
                "codex": (f"{HOME}/.agents/skills", f"{HOME}/.codex/AGENTS.md"),
            }[args.agent]
            sh(
                "docker",
                "exec",
                name,
                "mkdir",
                "-p",
                str(Path(skills).parent),
                str(Path(instructions).parent),
            )
            sh("docker", "cp", f"{catalog}/skills", f"{name}:{skills}")
            sh(
                "docker",
                "cp",
                f"{catalog}/global-instructions/AGENTS.md",
                f"{name}:{instructions}",
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

        totals, secrets = run_agent(case, name, project, out, args)

        diff = sh(
            *exec_,
            "bash",
            "-c",
            f"git add -A && git diff --cached {base} && git log --oneline {base}..HEAD "
            "&& git status --short",
        )
        (out / "diff.patch").write_text(redact(diff.stdout, secrets))
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
                    "output": redact(result.stdout + result.stderr, secrets)[-2000:],
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
        help="file holding a `claude setup-token` token",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--arm", action="append", required=True, help="none, or NAME=GIT_REF"
    )
    parser.add_argument("--case", action="append", help="case id (default: all)")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--agent", choices=DEFAULT_MODELS, default="claude")
    parser.add_argument(
        "--model", help="defaults to the selected agent's default model"
    )
    parser.add_argument("--max-five-hour", type=fraction, default=0.6)
    parser.add_argument("--max-seven-day", type=fraction, default=0.8)
    parser.add_argument("--turn-timeout", type=int, default=1800)
    args = parser.parse_args()

    args.model = args.model or DEFAULT_MODELS[args.agent]
    args.guard = UsageGuard(args.max_five_hour, args.max_seven_day)
    if args.agent == "claude":
        if args.token_file is None:
            parser.error("--token-file is required for Claude")
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = args.token_file.read_text().strip()
    manifest = args.out / "manifest.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        if (previous.get("agent", "claude"), previous.get("model")) != (
            args.agent,
            args.model,
        ):
            parser.error("--out already holds runs for another agent or model")
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
        manifest.write_text(
            json.dumps(
                {
                    "agent": args.agent,
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
            for future in as_completed(futures):
                case, arm, _, n = futures[future]
                label = f"{case['id']}/{arm}/run-{n}"
                try:
                    future.result()
                    print(
                        f"done {label} ({args.agent}: {args.guard.progress()})",
                        flush=True,
                    )
                except (
                    OSError,
                    subprocess.SubprocessError,
                    ValueError,
                    RuntimeError,
                ) as exc:  # a rerun resumes missing runs
                    print(
                        f"FAILED {label}: {exc!r} ({args.agent}: {args.guard.progress()})",
                        flush=True,
                    )
    finally:
        shutil.rmtree(staging)


if __name__ == "__main__":
    main()
