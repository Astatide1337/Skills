#!/usr/bin/env python3
"""Claude Code hooks that make "done" depend on checks the agent did not write.

Subcommands, each reading the hook's JSON from stdin:

  session-start  remember HEAD for the session's repository
  format         format the file an Edit/Write just touched (project tools only)
  stop           run the repository's verify command and the test-integrity
                 check before the agent may stop

The stop gate only runs when the repository changed during the session. It
blocks (exit 2) with the failing output so the agent keeps working, gives up
after a bounded number of attempts, and never edits anything itself.
Standard library only; see README.md for installation.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
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

VERIFY_GUIDANCE = (
    "Fix the cause in the code. Do not delete or skip tests, loosen lint or type "
    "settings, or edit the verify command to make this pass. If you believe the "
    "check itself is wrong, stop and explain why to the user instead."
)
INTEGRITY_GUIDANCE = (
    "This session weakened a check. Restore it, unless the user explicitly asked "
    "for this change. If they did, say so in your final message and name each "
    "file listed above, so the person reviewing the work sees it."
)


def state_dir() -> Path:
    configured = os.environ.get("AGENT_GATES_STATE")
    if configured:
        return Path(configured)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "agent-gates"


def load_state(session: str) -> dict:
    path = state_dir() / f"{session}.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"starts": {}, "failed": {}, "passed": [], "acknowledged": []}


def save_state(session: str, state: dict) -> None:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".{session}.json.tmp"
    temporary.write_text(json.dumps(state))
    temporary.replace(directory / f"{session}.json")


def git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def repo_root(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    top = git(start, "rev-parse", "--show-toplevel") if start.exists() else None
    return Path(top) if top else None


def session_id(payload: dict) -> str:
    raw = str(payload.get("session_id") or "unknown")
    return "".join(ch for ch in raw if ch.isalnum() or ch in "-_")[:80] or "unknown"


def remember_start(payload: dict, root: Path) -> None:
    session = session_id(payload)
    state = load_state(session)
    head = git(root, "rev-parse", "HEAD")
    if head and str(root) not in state["starts"]:
        state["starts"][str(root)] = head
        save_state(session, state)


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


def fingerprint(root: Path) -> str:
    """Identify the exact tree state, including new files `git diff` omits."""
    digest = hashlib.sha256()
    for part in (
        git(root, "rev-parse", "HEAD"),
        git(root, "status", "--porcelain"),
        git(root, "diff", "HEAD"),
    ):
        digest.update((part or "").encode() + b"\0")
    untracked = git(root, "ls-files", "-z", "--others", "--exclude-standard") or ""
    for name in sorted(filter(None, untracked.split("\0"))):
        try:
            digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
        except OSError:
            digest.update(name.encode() + b"\0")
    return digest.hexdigest()[:24]


def tail(text: str) -> str:
    lines = text.strip().splitlines()[-OUTPUT_TAIL_LINES:]
    return "\n".join(lines)[-OUTPUT_TAIL_CHARS:]


def run_verify(root: Path, command: list[str] | str) -> tuple[bool, str]:
    timeout = int(os.environ.get("AGENT_VERIFY_TIMEOUT", "540"))
    try:
        result = subprocess.run(
            command,
            cwd=root,
            shell=isinstance(command, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"verify timed out after {timeout}s"
    except OSError as error:
        return False, f"verify could not start: {error}"
    return result.returncode == 0, result.stdout + result.stderr


def block(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def allow_with_notice(message: str) -> int:
    print(json.dumps({"systemMessage": message}))
    return 0


def handle_stop(payload: dict) -> int:
    root = repo_root(Path(payload.get("cwd") or os.getcwd()))
    if root is None:
        return 0
    session = session_id(payload)
    state = load_state(session)
    start = state["starts"].get(str(root))
    head = git(root, "rev-parse", "HEAD")
    dirty = bool(git(root, "status", "--porcelain"))
    if not dirty and (start is None or start == head):
        return 0

    current = fingerprint(root)
    command = verify_command(root)
    if command is not None and current not in state["passed"]:
        passed, output = run_verify(root, command)
        if passed:
            state["passed"].append(current)
        else:
            failures = state["failed"].get(str(root), 0) + 1
            state["failed"][str(root)] = failures
            save_state(session, state)
            shown = command if isinstance(command, str) else shlex.join(command)
            if failures > MAX_FAILED_STOPS:
                return allow_with_notice(
                    f"`{shown}` still fails in {root} after {MAX_FAILED_STOPS} attempts. "
                    "The work is not verified; review it before relying on it."
                )
            return block(
                f"`{shown}` failed in {root} (attempt {failures} of "
                f"{MAX_FAILED_STOPS}).\n\n{tail(output)}\n\n{VERIFY_GUIDANCE}"
            )
        state["failed"].pop(str(root), None)

    if start and current not in state["acknowledged"]:
        report = test_integrity.compare(root, start, test_integrity.WORKTREE)
        if report.failures(set()):
            state["acknowledged"].append(current)
            save_state(session, state)
            return block(
                test_integrity.render(report, []) + "\n\n" + INTEGRITY_GUIDANCE
            )
    save_state(session, state)
    return 0


def formatter(root: Path, file: Path) -> list[str] | None:
    suffix = file.suffix.lower()
    bin_dir = root / "node_modules" / ".bin"
    if suffix in PRETTIER_FILES:
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
        ruff = root / ".venv" / "bin" / "ruff"
        ruff_path = str(ruff) if ruff.exists() else shutil.which("ruff")
        pyproject = root / "pyproject.toml"
        configured = (
            (root / "ruff.toml").exists()
            or (root / ".ruff.toml").exists()
            or (
                pyproject.is_file()
                and "[tool.ruff" in pyproject.read_text(errors="replace")
            )
        )
        if ruff_path and configured:
            return [ruff_path, "format", str(file)]
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
    remember_start(payload, root)
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
    root = repo_root(Path(payload.get("cwd") or os.getcwd()))
    if root is not None:
        remember_start(payload, root)
    return 0


HANDLERS = {
    "session-start": handle_session_start,
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
    return HANDLERS[argv[1]](payload if isinstance(payload, dict) else {})


if __name__ == "__main__":
    sys.exit(main(sys.argv))
