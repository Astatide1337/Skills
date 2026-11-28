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
import errno
import fcntl
import json
import os
import re
import shlex
import shutil
import signal
import socket
import stat
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
DEFAULT_MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6-luna"}
CODEX_HOME = f"{HOME}/.codex"
DEFAULT_CODEX_HOME = Path("~/.local/share/skills-evals/codex-home")
CODEX_AUTH = f"{CODEX_HOME}/auth.json"
TOKEN_FIELDS = ("id_token", "access_token", "refresh_token")
OTHER_CREDENTIAL_FIELDS = (
    "OPENAI_API_KEY",
    "personal_access_token",
    "agent_identity",
    "bedrock_api_key",
    "bedrock_access_keys",
)
AUTH_LOCK = threading.Lock()
BATCH_ID = uuid.uuid4().hex
BATCH_LOCK_DIR = Path.home().resolve() / ".cache" / "skills-eval"
OWNER_ID = uuid.uuid5(
    uuid.NAMESPACE_OID, f"{socket.gethostname()}:{os.getuid()}:{BATCH_LOCK_DIR}"
)
OWNER_LABEL = f"io.skills.eval.owner={OWNER_ID.hex}"
BATCH_LABEL = "io.skills.eval.batch"
CONTAINER_LABELS = ("--label", OWNER_LABEL, "--label", f"{BATCH_LABEL}={BATCH_ID}")
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
        self.stop_reason: str | None = None
        self.probing = False
        self.lock = threading.Condition()

    def observe(self, event: dict) -> None:
        info = event.get("rate_limit_info") or {}
        with self.lock:
            if info.get("status") == "rejected":
                self.stop()
            readings = [
                (window, data.get("utilization"))
                for window, data in (info.get("unifiedWindows") or {}).items()
                if isinstance(data, dict)
            ]
            readings.append((info.get("rateLimitType"), info.get("utilization")))
            for window, value in readings:
                if (
                    isinstance(window, str)
                    and window in self.thresholds
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and 0 <= value <= 1
                ):
                    self.windows[window] = max(value, self.windows.get(window, 0))
            self.lock.notify_all()

    def stop(self, reason: str = "usage limit reached earlier in this batch") -> None:
        with self.lock:
            self.stop_reason = self.stop_reason or reason
            self.lock.notify_all()

    @contextmanager
    def admit(self):
        with self.lock:
            self.lock.wait_for(
                lambda: self.stop_reason or self.windows or not self.probing
            )
            self.before_run()
            probe = not self.windows
            if probe:
                self.probing = True
        try:
            yield
        finally:
            if probe:
                with self.lock:
                    self.probing = False
                    self.lock.notify_all()

    def progress(self) -> str:
        with self.lock:
            return ", ".join(
                f"{window}={self.windows[window]:.1%}"
                if window in self.windows
                else f"{window}=unknown"
                for window in self.thresholds
            )

    def before_turn(self) -> None:
        with self.lock:
            if self.stop_reason:
                raise InfraError(f"skipped: {self.stop_reason}")

    def before_run(self) -> None:
        with self.lock:
            self.before_turn()
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


def codex_login_error(home: Path) -> InfraError:
    return InfraError(
        "Codex eval login missing or expired. Run "
        f"CODEX_HOME={shlex.quote(str(home.expanduser()))} "
        "codex -c 'cli_auth_credentials_store=\"file\"' login"
    )


def codex_auth_path(home: Path) -> Path:
    home = home.expanduser().resolve()
    if home == (Path.home() / ".codex").resolve():
        raise InfraError(
            "--codex-home must be a dedicated directory outside the daily Codex home"
        )
    path = home / "auth.json"
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise codex_login_error(home) from None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not info.st_size:
        raise codex_login_error(home)
    return path


def remember_codex_tokens(raw: bytes, secrets: set[str]) -> None:
    def remember(value) -> None:
        if isinstance(value, str) and value:
            secrets.add(value)
        elif isinstance(value, dict):
            for item in value.values():
                remember(item)

    data = parse_event(raw)
    tokens = data.get("tokens")
    if isinstance(tokens, dict):
        for key in TOKEN_FIELDS:
            remember(tokens.get(key))
    for key in OTHER_CREDENTIAL_FIELDS:
        remember(data.get(key))


@contextmanager
def codex_auth(
    name: str, secrets: set[str], home: Path, guard: UsageGuard | None = None
):
    """Serialize copy-in, invocation, and refresh for the dedicated eval login."""
    path = codex_auth_path(home)

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

    with AUTH_LOCK, (path.parent / ".eval-auth.lock").open("ab") as lock:
        if guard is None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        else:
            # Let the runner's main thread cancel a worker waiting on another batch.
            with guard.lock:
                while True:
                    guard.before_turn()
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        guard.lock.wait(0.1)
                    else:
                        break
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as exc:
            if exc.errno not in (errno.ENOENT, errno.ELOOP):
                raise
            raise codex_login_error(home) from None
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not info.st_size:
                raise codex_login_error(home)
            original = source.read()
        remember_codex_tokens(original, secrets)
        transfer(
            f"umask 077; tmp=$(mktemp {CODEX_HOME}/auth.XXXXXX) "
            f'&& cat > "$tmp" && mv -fT "$tmp" "{CODEX_AUTH}"',
            original,
        )
        try:
            yield
        finally:
            updated = transfer(
                f'p="{CODEX_AUTH}"; if [ -f "$p" ] && [ ! -L "$p" ]; then cat "$p" && rm -f "$p"; fi'
            )
            remember_codex_tokens(updated, secrets)
            if updated and updated != original:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                    pending = Path(tmp.name)
                    try:
                        tmp.write(updated)
                        tmp.flush()
                        os.fsync(tmp.fileno())
                        tmp.close()
                        pending.replace(path)
                    finally:
                        pending.unlink(missing_ok=True)


def redact(text: str, secrets: set[str]) -> str:
    spellings = set(secrets)
    for secret in secrets:
        for ascii_only in (True, False):
            escaped = json.dumps(secret, ensure_ascii=ascii_only)[1:-1]
            spellings.add(escaped)
            # A partial JSONL event may contain embedded JSON we cannot decode.
            spellings.add(json.dumps(escaped, ensure_ascii=ascii_only)[1:-1])
    for spelling in sorted(spellings, key=len, reverse=True):
        text = text.replace(spelling, "[redacted]")
    return text


def redact_json(value, secrets: set[str]):
    if isinstance(value, str):
        return redact(value, secrets)
    if isinstance(value, list):
        return [redact_json(item, secrets) for item in value]
    if isinstance(value, dict):
        return {
            redact(key, secrets): redact_json(item, secrets)
            for key, item in value.items()
        }
    return value


def redact_jsonl(text: str, secrets: set[str]) -> str:
    if not secrets:
        return text
    lines = []
    for line in text.splitlines(keepends=True):
        event = parse_event(line)
        if event:
            # Decode alternate JSON escapes before checking string content.
            clean = redact_json(event, secrets)
            if clean != event:
                line = json.dumps(clean) + ("\n" if line.endswith("\n") else "")
        else:
            line = redact(line, secrets)
        lines.append(line)
    return "".join(lines)


def timeout_output(exc: subprocess.TimeoutExpired) -> tuple[str, str]:
    def decode(value: bytes | str | None) -> str:
        return (
            value.decode(errors="replace") if isinstance(value, bytes) else value or ""
        )

    return decode(exc.stdout), decode(exc.stderr)


def is_infra(event: dict) -> bool:
    if event.get("api_error") in AGENT_ERRORS:
        return False
    return bool(event.get("api_error") or event.get("api_error_status"))


def parse_event(line: str | bytes) -> dict:
    """One stream-json event; a line cut off by a timeout kill is skipped."""
    try:
        event = json.loads(line)
    except ValueError:
        return {}
    return event if isinstance(event, dict) else {}


def sh(
    *args: str, check: bool = True, timeout: int = 120, input: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=check, input=input
    )


def start_container(name: str, agent: str) -> None:
    options = (
        ["--tmpfs", f"{CODEX_HOME}:rw,nosuid,nodev,uid=1000,gid=1000,mode=0700"]
        if agent == "codex"
        else ["-e", "CLAUDE_CODE_OAUTH_TOKEN"]
    )
    sh(
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        *CONTAINER_LABELS,
        *options,
        IMAGE,
        "sleep",
        "infinity",
    )


def cleanup_containers(lock_dir: Path | None = None) -> None:
    filters = ["--filter", f"label={OWNER_LABEL}"]
    if lock_dir is None:
        listed = sh(
            "docker",
            "ps",
            "-aq",
            *filters,
            "--filter",
            f"label={BATCH_LABEL}={BATCH_ID}",
        ).stdout.split()
        if listed:
            sh("docker", "rm", "-f", *listed, check=False)
        return
    batches: dict[str, list[str]] = {}
    listed = sh(
        "docker",
        "ps",
        "-a",
        *filters,
        "--format",
        '{{.ID}} {{.Label "' + BATCH_LABEL + '"}}',
    ).stdout
    for line in listed.splitlines():
        fields = line.split()
        if len(fields) == 2 and re.fullmatch(r"[0-9a-f]{32}", fields[1]):
            container, batch = fields
            batches.setdefault(batch, []).append(container)
    for batch, containers in batches.items():
        path = lock_dir / batch
        with path.open("ab") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            if sh("docker", "rm", "-f", *containers, check=False).returncode == 0:
                path.unlink(missing_ok=True)


@contextmanager
def container_batch():
    lock_dir = BATCH_LOCK_DIR
    lock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = lock_dir / BATCH_ID
    interrupted = False

    def interrupt(_signum, _frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt

    with path.open("ab") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        handlers = {}
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                handlers[sig] = signal.signal(sig, interrupt)
            cleanup_containers(lock_dir)
            yield
        finally:
            try:
                cleanup_containers()
            finally:
                path.unlink(missing_ok=True)
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)


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
    return None


def codex_events(stdout: str, stderr: str, home: Path) -> list[dict]:
    events = []
    diagnostics = [stderr]
    for line in stdout.splitlines():
        event = parse_event(line)
        if not event:
            diagnostics.append(line)  # A timeout may leave an incomplete error event.
        elif event.get("type") in ("error", "turn.failed"):
            diagnostics.append((event.get("error") or event).get("message", ""))
        events.append(event)
    for detail in diagnostics:
        message = detail.lower()
        if any(
            limit in message
            for limit in (
                "hit your usage limit",
                "usage_limit_reached",
                "workspace_limit_reached",
                "hit your spend cap",
                "workspace is out of credits",
            )
        ):
            raise InfraError(f"Codex usage limit reached: {detail[-500:]}")
        if (
            re.search(r"\b(?:status(?: code)?[ :=]+401|401 unauthorized)\b", message)
            or message.strip() == "401"
            or any(
                hint in message
                for hint in (
                    "login required",
                    "login_required",
                    "not logged in",
                    "run `codex login`",
                )
            )
        ):
            raise codex_login_error(home)
    return events


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
    if args.agent == "codex":
        try:
            events = codex_events(stdout, stderr, args.codex_home)
        except InfraError as exc:
            args.guard.stop(str(exc))
            raise
        thread, result = codex_result(events)
        session = thread or session
        results = [result] if result is not None else []
        if returncode and result is not None and not result.get("api_error"):
            raise InfraError(f"Codex exited {returncode} after reporting completion")
    else:
        results = []
        for line in stdout.splitlines():
            event = parse_event(line)
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
    args.guard.before_run()
    for pattern in ("trace-*.jsonl", "stderr-*.txt"):
        for path in out.glob(pattern):
            path.unlink()
    for i, message in enumerate(messages):
        args.guard.before_turn()
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
        auth = (
            codex_auth(name, secrets, args.codex_home, args.guard)
            if args.agent == "codex"
            else nullcontext()
        )
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
                stdout, stderr = timeout_output(exc)
                returncode = None
                totals["timed_out"] = True
                totals["usage_complete"] = False
            elapsed = time.monotonic() - started
            totals["wall_seconds"] += round(elapsed, 1)
            if args.agent == "codex":
                totals["duration_ms"] += round(elapsed * 1000)
        stdout, stderr = redact_jsonl(stdout, secrets), redact(stderr, secrets)
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
    (out / "final.md").write_text(redact("\n\n".join(final), secrets))
    return totals, secrets


def run_one(case: dict, arm: str, catalog: Path | None, n: int, args) -> None:
    out = args.out / case["id"] / arm / f"run-{n}"
    if (out / "timing.json").exists():
        return  # finished earlier; rerunning would overwrite evidence
    with args.guard.admit():
        run_in_container(case, catalog, out, args)


def run_in_container(case: dict, catalog: Path | None, out: Path, args) -> None:
    out.mkdir(parents=True, exist_ok=True)
    name = f"skills-eval-{uuid.uuid4().hex[:10]}"
    project = f"{HOME}/{case['project']}"
    exec_ = ["docker", "exec", "-w", project, name]
    try:
        start_container(name, args.agent)
        args.guard.before_run()
        sh("docker", "cp", f"{case['dir']}/repo/.", f"{name}:{project}")
        if catalog is not None:
            skills, instructions = {
                "claude": (f"{HOME}/.claude/skills", f"{HOME}/.claude/CLAUDE.md"),
                "codex": (f"{HOME}/.agents/skills", f"{CODEX_HOME}/AGENTS.md"),
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
            source = catalog / "global-instructions/AGENTS.md"
            if args.agent == "codex":
                # docker cp targets the writable layer even when the path has a tmpfs.
                sh(
                    "docker",
                    "exec",
                    "-i",
                    name,
                    "bash",
                    "-c",
                    f'cat > "{instructions}"',
                    input=source.read_text(),
                )
            else:
                sh("docker", "cp", str(source), f"{name}:{instructions}")
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
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=DEFAULT_CODEX_HOME,
        help=f"dedicated Codex login directory (default: {DEFAULT_CODEX_HOME})",
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
    else:
        codex_auth_path(args.codex_home)
    manifest = args.out / "manifest.json"
    if manifest.exists():
        previous = json.loads(manifest.read_text())
        if (previous.get("agent", "claude"), previous.get("model")) != (
            args.agent,
            args.model,
        ):
            parser.error("--out already holds runs for another agent or model")
    with container_batch():
        run_batch(args, manifest)


def run_batch(args, manifest: Path) -> None:
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
        pool = ThreadPoolExecutor(args.jobs)
        try:
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
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            args.guard.stop()
            cleanup_containers()
            raise
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
    finally:
        shutil.rmtree(staging)


if __name__ == "__main__":
    main()
