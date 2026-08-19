#!/usr/bin/env python3
"""Provider adapters used by the repository-local eval harness.

Adapters deliberately launch each provider with isolated configuration and an
empty MCP configuration. An explicitly supplied credential home contributes
only the provider's auth file to a temporary home outside the result artifacts;
global skills, settings, and caches are never exposed to the child process.
"""

from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProviderResult:
    status: str
    return_code: int | None
    final_response: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    available_skills: list[str] = field(default_factory=list)
    system_skills: list[str] = field(default_factory=list)
    system_skill_inventory_complete: bool = True
    # The adapters request an offline configuration, but Codex/Claude do not
    # expose a proof that the provider's network sandbox was actually applied
    # to this process.  Keep this explicitly false; the evaluator must rely on
    # transcript observation and fail closed on any network attempt.
    network_policy_enforced: bool = False
    # Codex exec does not accept the same fine-grained tool allowlist as the
    # Claude adapter.  Do not claim that the requested list was enforced.
    tool_policy_enforced: bool = False


def _event_lines(stdout: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass


def _ephemeral_home(prefix: str, credential_home: Path | None, credential_files: tuple[str, ...]) -> Path:
    """Create a temporary provider home with only explicitly requested auth files."""

    home = Path(tempfile.mkdtemp(prefix=prefix))
    if credential_home:
        for filename in credential_files:
            source = credential_home / filename
            if source.is_file():
                shutil.copy2(source, home / filename)
    return home


def _isolated_env(home: Path, *, home_variable: str) -> dict[str, str]:
    # Provider authentication is file-based and copied explicitly above. Do
    # not leak host tokens, proxy settings, or cloud credentials into a trial.
    allowed = {
        "LANG", "LC_ALL", "LC_CTYPE", "PATH", "SHELL", "TERM", "TMPDIR",
        "TZ", "USER", "LOGNAME", "SSL_CERT_FILE", "SSL_CERT_DIR",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / "config")
    env["XDG_CACHE_HOME"] = str(home / "cache")
    env[home_variable] = str(home)
    return env


def _sum_tokens(usage: dict[str, Any]) -> int:
    for key in ("total_tokens", "totalTokens"):
        if isinstance(usage.get(key), (int, float)):
            return int(usage[key])
    input_tokens = usage.get("input_tokens", usage.get("inputTokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("outputTokens", 0))
    if isinstance(input_tokens, (int, float)) or isinstance(output_tokens, (int, float)):
        return int(input_tokens or 0) + int(output_tokens or 0)
    return 0


def _system_skills(home: Path) -> list[str]:
    system_root = home / "skills" / ".system"
    try:
        return sorted(path.name for path in system_root.iterdir() if path.is_dir())
    except OSError:
        return []


class ClaudeAdapter:
    """Claude Code adapter with project-only skills and no MCP servers."""

    def __init__(self, binary: str = "claude") -> None:
        self.binary = binary

    def run(
        self,
        *,
        prompt: str,
        project: Path,
        run_dir: Path,
        model: str | None,
        with_skill: bool,
        timeout_seconds: int,
        allowed_tools: list[str],
        writable: bool = False,
        credential_home: Path | None = None,
        reasoning_effort: str | None = None,
    ) -> ProviderResult:
        home = _ephemeral_home("skills-evals-claude-home-", credential_home, (".credentials.json",))
        mcp_config = run_dir / "empty-mcp.json"
        home.mkdir(parents=True, exist_ok=True)
        mcp_config.write_text(json.dumps({"mcpServers": {}}, indent=2) + "\n")

        cmd = [
            self.binary,
            "--bare",
            "--no-session-persistence",
            "--setting-sources",
            "project",
            "--strict-mcp-config",
            "--mcp-config",
            str(mcp_config),
            "--tools",
            ",".join(allowed_tools),
            "--allowedTools",
            *allowed_tools,
            "--permission-mode",
            "dontAsk",
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if not with_skill:
            cmd.append("--disable-slash-commands")
        if model:
            cmd.extend(["--model", model])
        if reasoning_effort:
            cmd.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        cmd.extend(["--add-dir", str(project), "-p", prompt])

        start = time.monotonic()
        process: subprocess.Popen[bytes] | None = None
        stdout = ""
        stderr = ""
        status = "completed"
        return_code: int | None = None
        try:
            process = subprocess.Popen(
                cmd,
                cwd=project,
                env=_isolated_env(home, home_variable="CLAUDE_CONFIG_DIR"),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=timeout_seconds)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                return_code = process.returncode
            except subprocess.TimeoutExpired as exc:
                status = "timed_out"
                stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                _kill_process(process)
                return_code = process.returncode
        except OSError as exc:
            status = "provider_error"
            shutil.rmtree(home, ignore_errors=True)
            return ProviderResult(status, None, "", stderr=str(exc), error=str(exc))

        events = _event_lines(stdout)
        tool_calls: list[dict[str, Any]] = []
        seen_tools: set[str] = set()
        text_parts: list[str] = []
        final_response = ""
        usage: dict[str, Any] = {}
        available_skills: list[str] = []
        for event in events:
            if event.get("type") == "system" and event.get("subtype") == "init":
                skills = event.get("skills", [])
                if isinstance(skills, list):
                    available_skills = [str(skill) for skill in skills]
            if event.get("type") == "assistant":
                message = event.get("message", {})
                for item in message.get("content", []) if isinstance(message, dict) else []:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        text_parts.append(item["text"])
                    if item.get("type") == "tool_use":
                        key = str(item.get("id") or f"{item.get('name')}:{len(tool_calls)}")
                        if key not in seen_tools:
                            seen_tools.add(key)
                            tool_calls.append({"name": item.get("name", ""), "input": item.get("input", {}), "id": item.get("id")})
            if event.get("type") == "result":
                if isinstance(event.get("result"), str):
                    final_response = event["result"]
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
        if not final_response:
            final_response = "\n".join(text_parts).strip()
        if return_code not in (0, None) and status == "completed":
            status = "provider_error"
        elapsed = time.monotonic() - start
        if not final_response and status == "completed":
            status = "empty_response"
        result = ProviderResult(
            status=status,
            return_code=return_code,
            final_response=final_response,
            tool_calls=tool_calls,
            total_tokens=_sum_tokens(usage),
            stdout=stdout,
            stderr=stderr,
            error=f"Claude returned status {return_code}" if status == "provider_error" else "",
            usage={**usage, "duration_seconds": round(elapsed, 3)},
            available_skills=available_skills,
            system_skills=_system_skills(home),
            system_skill_inventory_complete=True,
            network_policy_enforced=False,
            tool_policy_enforced=False,
        )
        shutil.rmtree(home, ignore_errors=True)
        return result


class CodexAdapter:
    """Codex exec adapter. Live web search is never enabled by this adapter."""

    def __init__(self, binary: str = "codex") -> None:
        self.binary = binary

    def run(
        self,
        *,
        prompt: str,
        project: Path,
        run_dir: Path,
        model: str | None,
        with_skill: bool,
        timeout_seconds: int,
        allowed_tools: list[str],
        writable: bool = False,
        credential_home: Path | None = None,
        reasoning_effort: str | None = None,
    ) -> ProviderResult:
        del with_skill, allowed_tools
        home = _ephemeral_home("skills-evals-codex-home-", credential_home, ("auth.json",))
        home.mkdir(parents=True, exist_ok=True)
        last_message = run_dir / "codex-last-message.md"
        cmd = [
            self.binary,
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            # The host can inject app/plugin MCP resources independently of
            # user config.  Disable those capability surfaces explicitly for
            # this offline, documentation-free pilot.
            "--disable",
            "apps",
            "--disable",
            "plugins",
            # Codex can expose app-provided MCP resources independently of the
            # user's config file.  An explicit empty server map keeps the
            # provider boundary closed for offline evals; the grader still
            # fails closed if a provider emits a web/MCP call.
            "-c",
            "mcp_servers={}",
            # Current Codex releases enable web search by default unless this
            # top-level setting is explicitly disabled.
            "-c",
            'web_search="disabled"',
            # Set the supported workspace-write network policy.  Read-only
            # mode has no supported per-mode config field in this Codex
            # release; the provider result records network isolation as
            # unverified and the grader invalidates observed attempts.
            "-c",
            "sandbox_workspace_write.network_access=false",
            "--sandbox",
            "workspace-write" if writable else "read-only",
            "--skip-git-repo-check",
            "--cd",
            str(project),
            "--output-last-message",
            str(last_message),
        ]
        if model:
            cmd.extend(["--model", model])
        if reasoning_effort:
            cmd.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        cmd.append(prompt)

        start = time.monotonic()
        process: subprocess.Popen[bytes] | None = None
        stdout = ""
        stderr = ""
        status = "completed"
        return_code: int | None = None
        try:
            process = subprocess.Popen(
                cmd,
                cwd=project,
                env=_isolated_env(home, home_variable="CODEX_HOME"),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=timeout_seconds)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                return_code = process.returncode
            except subprocess.TimeoutExpired as exc:
                status = "timed_out"
                stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                _kill_process(process)
                return_code = process.returncode
        except OSError as exc:
            status = "provider_error"
            shutil.rmtree(home, ignore_errors=True)
            return ProviderResult(status, None, "", stderr=str(exc), error=str(exc))

        events = _event_lines(stdout)
        tool_calls: list[dict[str, Any]] = []
        text_parts: list[str] = []
        usage: dict[str, Any] = {}
        for event in events:
            item = event.get("item") if isinstance(event.get("item"), dict) else event
            if isinstance(item, dict):
                item_type = str(item.get("type", ""))
                if item_type in {"agent_message", "assistant_message"}:
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        text_parts.append(text)
                if "tool" in item_type or item_type in {"command_execution", "mcp_tool_call", "web_search", "web_search_call"}:
                    tool_calls.append({"name": item.get("name") or item_type, "input": item})
            if isinstance(event.get("usage"), dict):
                usage = event["usage"]
            if isinstance(event.get("response"), dict) and isinstance(event["response"].get("usage"), dict):
                usage = event["response"]["usage"]
        final_response = ""
        try:
            final_response = last_message.read_text(errors="replace")
        except OSError:
            final_response = "\n".join(text_parts).strip()
        if return_code not in (0, None) and status == "completed":
            status = "provider_error"
        if not final_response and status == "completed":
            status = "empty_response"
        elapsed = time.monotonic() - start
        result = ProviderResult(
            status=status,
            return_code=return_code,
            final_response=final_response,
            tool_calls=tool_calls,
            total_tokens=_sum_tokens(usage),
            stdout=stdout,
            stderr=stderr,
            error=f"Codex returned status {return_code}" if status == "provider_error" else "",
            usage={**usage, "duration_seconds": round(elapsed, 3)},
            system_skills=_system_skills(home),
            system_skill_inventory_complete=True,
            network_policy_enforced=False,
            tool_policy_enforced=False,
        )
        shutil.rmtree(home, ignore_errors=True)
        return result
