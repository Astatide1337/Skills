#!/usr/bin/env python3
"""Claude Code hooks that make "done" depend on checks the agent did not write.

Subcommands, each reading the hook's JSON from stdin:

  session-start  snapshot the starting tree of the session's repository
  guard          before a tool runs: snapshot the repository it will touch,
                 and refuse hook bypasses and edits to the gates themselves
  format         after an edit: format the file with the project's formatter
  stop           before the agent stops: for every repository changed this
                 session, run the test-integrity check and the verify command

"Changed" means the working tree, including uncommitted and untracked files,
differs from its snapshot at session start, so a read-only session is never
verified and the user's own earlier edits are never blamed on the agent.
Standard library only; see README.md for installation.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_integrity

MAX_FAILED_STOPS = 3
OUTPUT_TAIL_LINES = 80
OUTPUT_TAIL_CHARS = 6000
FORMAT_TIMEOUT = 30
PRETTIER_FILES = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".mts",
    ".cts",
    ".css",
    ".scss",
    ".json",
    ".md",
    ".mdx",
    ".html",
    ".yaml",
    ".yml",
}
PRETTIER_CONFIGS = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.mjs",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    "prettier.config.js",
    "prettier.config.cjs",
    "prettier.config.mjs",
)
# Commands that switch off checks rather than satisfy them.
BYPASSES = (
    (re.compile(r"--no-verify\b"), "--no-verify skips the repository's hooks"),
    (
        re.compile(
            r"\bgit\b[^|;&\n\"']*\bcommit\b[^|;&\n\"']*\s-[A-Za-z]*n[A-Za-z]*\b"
        ),
        "git commit -n skips the repository's hooks",
    ),
    (re.compile(r"\bHUSKY=0\b"), "HUSKY=0 disables git hooks"),
    (
        re.compile(r"\bSKIP=\S+[^|;&\n]*\b(?:git|pre-commit)\b"),
        "SKIP= disables pre-commit checks",
    ),
    (re.compile(r"core\.hooksPath"), "changing core.hooksPath disables git hooks"),
)
VERIFY_GUIDANCE = (
    "Fix the cause in the code. Do not delete or skip tests, loosen lint or type "
    "settings, or edit the verify command to make this pass. If you believe the "
    "check itself is wrong, stop and explain why to the user instead."
)
INTEGRITY_GUIDANCE = (
    "This session weakened a check. Restore it, unless the user explicitly asked "
    "for this change. If they did, say so in your final message and name each "
    "item listed above, so the person reviewing the work sees it."
)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def state_dir() -> Path:
    configured = os.environ.get("AGENT_GATES_STATE")
    if configured:
        return Path(configured)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agent-gates"


def default_state() -> dict:
    return {
        "started_at": now(),
        "starts": {},
        "failed": {},
        "passed": [],
        "given_up": [],
        "acknowledged": [],
    }


def load_state(session: str) -> dict:
    state = default_state()
    try:
        stored = json.loads((state_dir() / f"{session}.json").read_text())
        if isinstance(stored, dict):
            state.update(
                {
                    key: value
                    for key, value in stored.items()
                    if isinstance(value, type(state[key]))
                }
            )
    except (OSError, ValueError, KeyError):
        pass
    return state


def save_state(session: str, state: dict) -> None:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".{session}.json.tmp"
    temporary.write_text(json.dumps(state))
    temporary.replace(directory / f"{session}.json")


def session_id(payload: dict) -> str:
    raw = str(payload.get("session_id") or "unknown")
    return "".join(ch for ch in raw if ch.isalnum() or ch in "-_")[:80] or "unknown"


def git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "surrogateescape").strip()


def repo_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    while not start.exists() and start != start.parent:
        start = start.parent
    top = git(start, "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def record_start(state: dict, root: Path | None) -> bool:
    """Snapshot a repository the first time the session touches it."""
    if root is None or str(root) in state["starts"]:
        return False
    try:
        tree = test_integrity.snapshot_tree(root)
    except RuntimeError:
        return False
    state["starts"][str(root)] = {
        "tree": tree,
        "head": git(root, "rev-parse", "HEAD"),
        "worktrees": [str(path) for path in worktrees(root)],
    }
    return True


def worktrees(root: Path) -> list[Path]:
    listing = git(root, "worktree", "list", "--porcelain") or ""
    return [
        Path(line[len("worktree ") :])
        for line in listing.splitlines()
        if line.startswith("worktree ")
    ]


def session_started(payload: dict, state: dict) -> str:
    """When the session began: the transcript's first timestamp, else the state's."""
    transcript = payload.get("transcript_path")
    try:
        with open(str(transcript), encoding="utf-8") as handle:
            for line in handle:
                stamp = json.loads(line).get("timestamp")
                if stamp:
                    return min(stamp, state["started_at"])
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return state["started_at"]


def start_for(state: dict, root: Path, started: str) -> tuple[str, str | None]:
    """The tree to compare against, and a note when it had to be inferred."""
    recorded = state["starts"].get(str(root))
    if recorded:
        return recorded["tree"], None
    common = git(root, "rev-parse", "--git-common-dir")
    for other, start in state["starts"].items():
        other_common = git(Path(other), "rev-parse", "--git-common-dir")
        if (
            common
            and other_common
            and start.get("head")
            and Path(root, common).resolve() == Path(other, other_common).resolve()
        ):
            tree = git(root, "rev-parse", f"{start['head']}^{{tree}}")
            if tree:
                return tree, f"{root}: compared with the session's starting commit"
    candidates = (
        (f"HEAD@{{{started}}}", "HEAD at the session's start, from the reflog"),
        (git(root, "merge-base", "HEAD", "@{upstream}"), "the upstream branch"),
        ("HEAD", "HEAD"),
    )
    for base, label in candidates:
        tree = (
            git(root, "rev-parse", "--verify", "-q", f"{base}^{{tree}}")
            if base
            else None
        )
        if tree:
            return tree, f"{root}: no session start recorded; compared with {label}"
    return "", f"{root}: no session start recorded and no commits to compare with"


def verify_command(root: Path) -> list[str] | str | None:
    configured = os.environ.get("AGENT_VERIFY_CMD")
    if configured:
        return configured
    package = root / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text()).get("scripts", {})
        except (OSError, ValueError, AttributeError):
            scripts = {}
        if isinstance(scripts, dict) and "verify" in scripts:
            for lockfile, runner in (
                ("pnpm-lock.yaml", "pnpm"),
                ("yarn.lock", "yarn"),
                ("bun.lock", "bun"),
                ("bun.lockb", "bun"),
            ):
                if (root / lockfile).exists():
                    return [runner, "run", "verify"]
            return ["npm", "run", "verify"]
    for name, runner in (("Makefile", "make"), ("justfile", "just")):
        file = root / name
        if file.is_file() and any(
            line.startswith("verify:")
            for line in file.read_text(errors="replace").splitlines()
        ):
            return [runner, "verify"]
    return None


def trusted(root: Path) -> bool:
    configured = os.environ.get("AGENT_GATES_TRUSTED")
    prefixes = configured.split(os.pathsep) if configured else [str(Path.home())]
    resolved = root.resolve()
    return any(
        prefix
        and (
            resolved == Path(prefix).expanduser().resolve()
            or Path(prefix).expanduser().resolve() in resolved.parents
        )
        for prefix in prefixes
    )


def tail(text: str) -> str:
    lines = text.strip().splitlines()[-OUTPUT_TAIL_LINES:]
    return "\n".join(lines)[-OUTPUT_TAIL_CHARS:]


def run_verify(root: Path, command: list[str] | str) -> tuple[bool, str]:
    timeout = int(os.environ.get("AGENT_VERIFY_TIMEOUT", "540"))
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            shell=isinstance(command, str),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError as error:
        return False, f"verify could not start: {error}"
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            try:
                process.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                continue
        return False, f"verify timed out after {timeout}s; its processes were stopped"
    return process.returncode == 0, output.decode("utf-8", "replace")


def check_repository(
    root: Path, state: dict, started: str, blocks: list, notices: list
) -> None:
    start_tree, note = start_for(state, root, started)
    if note:
        notices.append(note)
    if not start_tree:
        return
    current = test_integrity.snapshot_tree(root)
    if current == start_tree:
        return
    report = test_integrity.compare(root, start_tree, current)
    weakened = bool(report.failures(set()))
    rendered = test_integrity.render(report, [])
    key = str(root)

    command = verify_command(root)
    shown = (
        (command if isinstance(command, str) else shlex.join(command))
        if command
        else ""
    )
    verify_ok = True
    if command is None or current in state["passed"]:
        pass
    elif current in state["given_up"]:
        verify_ok = None
        notices.append(
            f"{root}: `{shown}` still fails on this unchanged tree; not rerun."
        )
    elif not trusted(root):
        verify_ok = None
        notices.append(
            f"{root}: `{shown}` not run; the path is outside AGENT_GATES_TRUSTED."
        )
    elif isinstance(command, list) and shutil.which(command[0]) is None:
        verify_ok = None
        notices.append(f"{root}: `{shown}` not run; `{command[0]}` is not installed.")
    elif state["failed"].get(key, 0) >= MAX_FAILED_STOPS:
        verify_ok = False
        state["given_up"].append(current)
        integrity = f"\n\n{rendered}" if weakened else ""
        notices.append(
            f"{root}: `{shown}` still fails after {MAX_FAILED_STOPS} attempts. "
            f"The work is not verified; review it before relying on it.{integrity}"
        )
    else:
        passed, output = run_verify(root, command)
        if passed:
            state["passed"].extend([current, test_integrity.snapshot_tree(root)])
            state["failed"].pop(key, None)
        else:
            verify_ok = False
            failures = state["failed"].get(key, 0) + 1
            state["failed"][key] = failures
            integrity = f"\n\n{rendered}" if weakened else ""
            blocks.append(
                f"`{shown}` failed in {root} (attempt {failures} of "
                f"{MAX_FAILED_STOPS}).\n\n{tail(output)}{integrity}\n\n{VERIFY_GUIDANCE}"
            )
            if weakened:
                state["acknowledged"].append(report.digest())

    if weakened and verify_ok is not False:
        digest = report.digest()
        if digest in state["acknowledged"]:
            notices.append(f"{root}: this session weakened a check.\n{rendered}")
        else:
            state["acknowledged"].append(digest)
            blocks.append(f"{root}:\n{rendered}\n\n{INTEGRITY_GUIDANCE}")


def handle_stop(payload: dict) -> int:
    session = session_id(payload)
    state = load_state(session)
    if not payload.get("stop_hook_active"):
        state["failed"] = {}  # a new turn gets fresh attempts
    roots: list[Path] = []
    cwd_root = repo_root(Path(payload.get("cwd") or os.getcwd()))
    known = {
        path
        for start in state["starts"].values()
        for path in start.get("worktrees", [])
    }
    for candidate in [*(Path(path) for path in state["starts"]), cwd_root]:
        if candidate is None or not candidate.exists():
            continue
        # Worktrees created during the session; ones that already existed are
        # the user's and are only checked if the session touched them.
        new = [path for path in worktrees(candidate) if str(path) not in known]
        for root in [candidate, *new]:
            if root.exists() and root not in roots:
                roots.append(root)
    started = session_started(payload, state)
    blocks: list[str] = []
    notices: list[str] = []
    try:
        for root in roots:
            check_repository(root, state, started, blocks, notices)
    finally:
        save_state(session, state)
    if blocks:
        print("\n\n---\n\n".join(blocks), file=sys.stderr)
        return 2
    if notices:
        print(json.dumps({"systemMessage": "Agent gates:\n" + "\n".join(notices)}))
    return 0


def protected(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    gates = state_dir().resolve()
    settings = (
        resolved.name.startswith("settings") and resolved.parent.name == ".claude"
    )
    return resolved == gates or gates in resolved.parents or settings


def handle_guard(payload: dict) -> int:
    session = session_id(payload)
    state = load_state(session)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or os.getcwd())
    reason = None
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        target = cwd
        reason = next(
            (why for pattern, why in BYPASSES if pattern.search(command)), None
        )
        if reason is None and (
            str(state_dir()) in command
            or "state/agent-gates" in command
            or re.search(r"\.claude/settings", command)
        ):
            reason = "this command touches the agent gates or Claude Code hook settings"
    else:
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        target = Path(raw) if Path(raw).is_absolute() else cwd / raw
        if raw and protected(target):
            reason = (
                "agent gate state and Claude Code hook settings are not agent-editable"
            )
    if record_start(state, repo_root(target)):
        save_state(session, state)
    if reason:
        print(
            f"Blocked by agent gates: {reason}. If the user wants this, they can run it "
            "themselves.",
            file=sys.stderr,
        )
        return 2
    return 0


def ignored(root: Path, path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", str(path)],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def formatter(root: Path, file: Path) -> list[str] | None:
    suffix = file.suffix.lower()
    bin_dir = root / "node_modules" / ".bin"
    local_bin = bin_dir.is_dir() and ignored(root, bin_dir)  # installed, not committed
    if suffix in PRETTIER_FILES and local_bin:
        if (bin_dir / "biome").exists() and any(
            (root / name).exists() for name in ("biome.json", "biome.jsonc")
        ):
            return [str(bin_dir / "biome"), "format", "--write", str(file)]
        has_config = any((root / name).exists() for name in PRETTIER_CONFIGS)
        if not has_config and (root / "package.json").is_file():
            has_config = '"prettier"' in (root / "package.json").read_text(
                errors="replace"
            )
        if (bin_dir / "prettier").exists() and has_config:
            return [str(bin_dir / "prettier"), "--write", "--ignore-unknown", str(file)]
    if suffix == ".py":
        venv_ruff = root / ".venv" / "bin" / "ruff"
        ruff = (
            str(venv_ruff)
            if venv_ruff.exists() and ignored(root, venv_ruff)
            else shutil.which("ruff")
        )
        pyproject = root / "pyproject.toml"
        configured = (
            (root / "ruff.toml").exists()
            or (root / ".ruff.toml").exists()
            or (
                pyproject.is_file()
                and "[tool.ruff" in pyproject.read_text(errors="replace")
            )
        )
        if ruff and configured:
            return [ruff, "format", str(file)]
    if suffix == ".go" and shutil.which("gofmt"):
        return ["gofmt", "-w", str(file)]
    return None


def handle_format(payload: dict) -> int:
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        return 0
    file = Path(raw)
    if not file.is_absolute():
        file = Path(payload.get("cwd") or os.getcwd()) / file
    root = repo_root(file)
    if root is None or not file.is_file() or "node_modules" in file.parts:
        return 0
    command = formatter(root, file)
    if command is None:
        return 0
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=FORMAT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"formatter skipped: {error}", file=sys.stderr)
        return 1
    if result.returncode != 0:
        print(
            f"formatter failed on {file.name}: {tail(result.stderr or result.stdout)}",
            file=sys.stderr,
        )
        return 1
    return 0


def handle_session_start(payload: dict) -> int:
    session = session_id(payload)
    state = load_state(session)
    if record_start(state, repo_root(Path(payload.get("cwd") or os.getcwd()))):
        save_state(session, state)
    return 0


HANDLERS = {
    "session-start": handle_session_start,
    "guard": handle_guard,
    "format": handle_format,
    "stop": handle_stop,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in HANDLERS:
        print(
            f"usage: {Path(argv[0]).name} {{{','.join(HANDLERS)}}} < hook-input.json",
            file=sys.stderr,
        )
        return 1
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    try:
        return HANDLERS[argv[1]](payload)
    except Exception as error:  # noqa: BLE001 - a crashed gate must say so, not pass silently
        if argv[1] == "stop":
            print(
                json.dumps(
                    {
                        "systemMessage": f"Agent gates did not run: {error!r}. "
                        "This stop was not checked."
                    }
                )
            )
            return 0
        print(f"agent gates {argv[1]} failed: {error!r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
