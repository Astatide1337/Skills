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
import base64
import fcntl
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, nullcontext
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases"
IMAGE = "skills-autonomous-eval"
HOME = "/home/node"
DEFAULT_MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6-luna"}
CODEX_HOME = f"{HOME}/.codex"
CODEX_AUTH = f"{CODEX_HOME}/auth.json"
TOKEN_FIELDS = ("id_token", "access_token", "refresh_token")
OTHER_AUTH_FIELDS = (
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
        self.limited = False
        self.probing = False
        self.lock = threading.Condition()

    def observe(self, event: dict) -> None:
        info = event.get("rate_limit_info") or {}
        with self.lock:
            self.limited |= info.get("status") == "rejected"
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

    def stop(self) -> None:
        with self.lock:
            self.limited = True
            self.lock.notify_all()

    @contextmanager
    def admit(self):
        with self.lock:
            self.lock.wait_for(lambda: self.limited or self.windows or not self.probing)
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


def jwt_identity(token: str) -> tuple[str, str]:
    if not re.fullmatch(r"[\w-]+\.[\w-]+\.[\w-]+", token, re.ASCII):
        raise ValueError("invalid JWT shape")
    _, payload, _ = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    auth = claims["https://api.openai.com/auth"]
    account = auth["chatgpt_account_id"]
    user = auth.get("chatgpt_user_id") or auth.get("user_id") or claims.get("sub")
    profile = claims.get("https://api.openai.com/profile")
    if (
        not all(nonempty_string(value) for value in (account, user))
        or any(
            auth.get(key) is not None and not isinstance(auth[key], str)
            for key in ("chatgpt_user_id", "user_id", "chatgpt_plan_type")
        )
        or not isinstance(auth.get("chatgpt_account_is_fedramp", False), bool)
        or (claims.get("email") is not None and not isinstance(claims["email"], str))
        or (
            profile is not None
            and profile.get("email") is not None
            and not isinstance(profile["email"], str)
        )
    ):
        raise ValueError("invalid ChatGPT JWT claims")
    return account, user


def nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def chatgpt_record(data: dict) -> tuple[dict, tuple[str, str]]:
    # AuthDotJson and TokenData in the pinned Codex login crate.
    mode = data.get("auth_mode")
    if mode != "chatgpt" and (
        mode is not None or any(data.get(key) is not None for key in OTHER_AUTH_FIELDS)
    ):
        raise ValueError("expected a ChatGPT login")
    tokens = data["tokens"]
    selected = {key: tokens[key] for key in (*TOKEN_FIELDS, "account_id")}
    if not all(
        nonempty_string(value) for value in selected.values()
    ) or not re.fullmatch(r"[!-~]+", selected["refresh_token"]):
        raise ValueError("incomplete ChatGPT login")
    identity = jwt_identity(tokens["id_token"])
    if (
        identity[0] != tokens["account_id"]
        or jwt_identity(tokens["access_token"]) != identity
    ):
        raise ValueError("ChatGPT token identities disagree")
    owner = tokens.get("login_owner_id")
    if owner is not None:
        if not nonempty_string(owner):
            raise ValueError("invalid login owner id")
        selected["login_owner_id"] = owner
    provenance = tokens.get("oauth_provenance")
    if provenance is not None:
        issuer, client_id = provenance["issuer"], provenance["client_id"]
        if not all(nonempty_string(value) for value in (issuer, client_id)):
            raise ValueError("invalid OAuth provenance")
        selected["oauth_provenance"] = {"issuer": issuer, "client_id": client_id}
    record = {"auth_mode": "chatgpt", "tokens": selected}
    refresh = data.get("last_refresh")
    if refresh is not None:
        if not re.fullmatch(
            r"[0-9]{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:[0-5]\d)",
            refresh,
            re.ASCII,
        ):
            raise ValueError("invalid last_refresh")
        datetime.fromisoformat(refresh)
        record["last_refresh"] = refresh
    return record, identity


def save_refreshed_auth(path: Path, original: bytes, updated: bytes) -> None:
    source, candidate = parse_event(original), parse_event(updated)
    try:
        before, old_identity = chatgpt_record(source)
        after, new_identity = chatgpt_record(candidate)
    except (AttributeError, KeyError, TypeError, ValueError):
        return
    if (
        old_identity != new_identity
        or before["tokens"].get("login_owner_id")
        != after["tokens"].get("login_owner_id")
        or "last_refresh" not in after
        or any(candidate.get(key) is not None for key in OTHER_AUTH_FIELDS)
    ):
        return
    # Keep the trusted host's non-login fields and OAuth authority.
    tokens = {**source["tokens"], **{key: after["tokens"][key] for key in TOKEN_FIELDS}}
    replacement = {**source, "tokens": tokens, "last_refresh": after["last_refresh"]}
    if replacement == source:
        return
    target = path.resolve()
    # Match Codex 0.167.1 storage_commit.rs's stable sidecar and Unix flock.
    fd = os.open(target.with_suffix(".json.lock"), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.resolve() != target or not target.exists():
            return
        with target.open("r+b") as current:
            if os.fstat(current.fileno()).st_nlink != 1 or current.read() != original:
                return
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
            pending = Path(tmp.name)
            try:
                tmp.write(json.dumps(replacement).encode())
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp.close()
                pending.replace(target)
            finally:
                pending.unlink(missing_ok=True)


@contextmanager
def codex_auth(name: str, secrets: set[str]):
    """Install auth for one invocation. The caller holds AUTH_LOCK."""
    path = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"

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
        tokens = parse_event(raw).get("tokens")
        if isinstance(tokens, dict):
            secrets.update(
                tokens[key] for key in TOKEN_FIELDS if nonempty_string(tokens.get(key))
            )

    original = path.read_bytes()
    try:
        selected, _ = chatgpt_record(parse_event(original))
    except (AttributeError, KeyError, TypeError, ValueError):
        raise InfraError(
            "Codex auth.json needs a valid file-backed ChatGPT login"
        ) from None
    supplied = json.dumps(selected).encode()
    remember(supplied)
    transfer(
        f"umask 077; tmp=$(mktemp {CODEX_HOME}/auth.XXXXXX) "
        f'&& cat > "$tmp" && mv -fT "$tmp" "{CODEX_AUTH}"',
        supplied,
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
    if any(
        limit in message
        for limit in (
            "hit your usage limit",
            "usage_limit_reached",
            "hit your spend cap",
            "workspace is out of credits",
        )
    ):
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
            if not failure or failure["api_error"] != "usage_limit_reached":
                failure = {
                    "result": message,
                    "num_turns": 1,
                    "api_error": codex_error(message) or "codex_error",
                }
            if kind == "turn.failed":
                return session, failure
    if failure and failure["api_error"] == "usage_limit_reached":
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
        if codex_error(stderr) == "usage_limit_reached":
            args.guard.stop()
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
