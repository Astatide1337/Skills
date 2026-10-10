#!/usr/bin/env python3
"""Execute an explicitly trusted verification profile; app CLIs own resources.

No discovery, shell interpolation, automatic installation, or sandbox claim.
Profiles and commands must be reviewed before use; never feed untrusted code
or credentials to this helper. Expectations are fixed before execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular, non-symlink file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Automatic content reads are limited to recognizable source/config inputs.
# Other tracked entries get metadata identity, never indiscriminate byte reads.
SOURCE_SUFFIXES = {".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
                   ".mts", ".cts", ".go", ".rs", ".java", ".c", ".h", ".cpp",
                   ".cs", ".rb", ".sh", ".css", ".scss", ".html", ".vue", ".svelte"}
CONFIG_NAMES = {"package.json", "package-lock.json", "pyproject.toml", "uv.lock",
                "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "Makefile",
                "tsconfig.json", "ruff.toml", ".gitignore", "AGENTS.md"}


def sensitive_path(path: Path) -> bool:
    return any(part.lower().startswith((".env", ".ssh", ".aws"))
               or part.lower() in {".config", "credentials", "secrets", "private", "keys.txt"}
               or any(word in part.lower() for word in ("credential", "secret", "password", "token", "private-key"))
               for part in path.parts) or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}


def bounded_path(workspace: Path, name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or ".git" in path.parts:
        raise ValueError(f"path must be bounded and relative: {name}")
    target = workspace / path
    # Reject every symlink component before resolving or opening its target.
    if any(p.is_symlink() for p in (target, *target.parents) if p != workspace.parent):
        raise ValueError(f"symlink is not a source input: {name}")
    if not target.resolve().is_relative_to(workspace):
        raise ValueError(f"source path escapes workspace: {name}")
    return target


def source_identity(workspace: Path, paths: list[str]) -> dict:
    result = {}
    for name in paths:
        if sensitive_path(Path(name)):
            raise ValueError(f"credential-like path cannot be a source input: {name}")
        result[name] = digest(bounded_path(workspace, name))
    return result


def profile_digest(profile: dict) -> str:
    return hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()


_GIT_CONTEXT_ENV = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
    "GIT_SUPER_PREFIX",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
}


def _workspace_git_environment() -> dict[str, str]:
    """Keep an inherited Git checkout from redirecting workspace inspection."""
    env = os.environ.copy()
    for name in tuple(env):
        if name in _GIT_CONTEXT_ENV or name.startswith(
            ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")
        ):
            env.pop(name, None)
    return env


def workspace_identity(workspace: Path, profile: dict) -> dict:
    """Capture Git identities without filters, index refresh or credential reads.

    Unsupported/ignored inputs are explicitly outside content coverage. This
    is freshness instrumentation, not proof of an application invocation.
    """
    options = profile.get("workspace_identity", {})
    mode = options.get("mode", "auto")
    git_environment = _workspace_git_environment()
    def git(*args):
        return subprocess.run(["git", "--no-optional-locks", "-C", str(workspace), *args],
                              capture_output=True, timeout=15, env=git_environment)
    root = None if mode == "artifact" else git("rev-parse", "--show-toplevel")
    non_git = False
    if mode == "auto" and root.returncode:
        # Repository metadata, permissions, or discovered markers can all make
        # a failed Git probe ambiguous; none justify an automatic downgrade.
        marker_found = False
        marker_path = None
        for directory in (workspace, *workspace.parents):
            try:
                (directory / ".git").lstat()
                marker_found = True
                marker_path = directory / ".git"
                break
            except FileNotFoundError:
                continue
        non_git = (not marker_found and root.returncode == 128
                   and root.stderr.startswith(b"fatal: not a git repository"))
        if not non_git:
            detail = " ".join(root.stderr.decode(errors="replace").split())[:300]
            marker = f"; marker={marker_path}" if marker_path is not None else ""
            raise ValueError(
                "Git discovery failed"
                f" (exit={root.returncode}{marker}; stderr={detail or 'empty'}); "
                "repair the repository or explicitly select bounded artifact mode"
            )
    if mode == "artifact" or non_git:
        return {"mode": "artifact", "coverage": "declared source_paths only",
                "sources": source_identity(workspace, profile["source_paths"]),
                "modes": {name: bounded_path(workspace, name).stat().st_mode for name in profile["source_paths"]}}
    if root.returncode or Path(os.fsdecode(root.stdout).strip()).resolve() != workspace:
        raise ValueError("Git identity requires the repository root; use explicit artifact mode for a bounded subdirectory")
    head = git("rev-parse", "--verify", "HEAD")
    index = git("ls-files", "--stage", "-z")
    others = git("ls-files", "--others", "--exclude-standard", "-z")
    if index.returncode or others.returncode:
        raise ValueError("Git index/untracked discovery unavailable")
    entries = {}
    opaque = {}
    generated = options.get("generated_paths", [])
    tracked = []
    for entry in index.stdout.split(b"\0"):
        if not entry:
            continue
        info, name = entry.split(b"\t", 1)
        if info.startswith(b"160000 "):
            raise ValueError("submodule identity unsupported; use a reviewed bounded artifact profile")
        tracked.append(os.fsdecode(name))
    untracked = {os.fsdecode(p) for p in others.stdout.split(b"\0") if p}
    for name in sorted(set(tracked) | untracked):
        path = Path(name)
        if name in untracked and any(path == Path(g) or Path(g) in path.parents for g in generated):
            continue
        target = workspace / path
        # lstat observes an entry without following symlinks or reading bytes.
        # Any parent symlink makes automatic content hashing unavailable.
        safe_source = not sensitive_path(path) and (path.suffix in SOURCE_SUFFIXES or path.name in CONFIG_NAMES)
        try:
            info = target.lstat()
        except FileNotFoundError:
            opaque[name] = {"missing": True}
            continue
        if safe_source and stat.S_ISREG(info.st_mode):
            entries[name] = {"sha256": source_identity(workspace, [name])[name], "mode": info.st_mode}
        else:
            opaque[name] = {"mode": info.st_mode, "size": info.st_size,
                            "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}
    return {"mode": "git", "revision": head.stdout.decode().strip() if head.returncode == 0 else None,
            "index_sha256": hashlib.sha256(index.stdout).hexdigest(),
            "sources": entries, "metadata_only": opaque,
            "excluded_generated": generated,
            "coverage": "safe source/config bytes; other nonignored entries metadata only; ignored files excluded"}


def check_freshness(receipt: dict, profile: dict, workspace: Path) -> dict:
    """Read-only comparison; the caller must also validate live app identity."""
    validate(profile)
    if receipt.get("version") != 2 or receipt.get("passed") is not True:
        return {"fresh": False, "reason": "receipt is failed or lacks workspace identity; rerun"}
    same = (receipt.get("workspace") == str(workspace)
            and receipt.get("profile_sha256") == profile_digest(profile)
            and receipt.get("source_after") == source_identity(workspace, profile["source_paths"])
            and receipt.get("workspace_after") == workspace_identity(workspace, profile))
    return {"fresh": same, "reason": "captured inputs unchanged; live app identity still requires validation" if same
            else "workspace/profile changed; rerun affected checks"}


def pointer(value, path: str):
    if path == "":
        return value
    if not path.startswith("/"):
        raise ValueError("expectation keys must be JSON pointers")
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def validate(profile: dict) -> None:
    if not isinstance(profile, dict) or not {"version", "source_paths", "steps"} <= set(profile) or set(profile) - {"version", "source_paths", "steps", "workspace_identity"} or type(profile["version"]) is not int or profile["version"] != 1:
        raise ValueError("profile requires version=1, source_paths, steps")
    options = profile.get("workspace_identity", {})
    if (not isinstance(options, dict) or set(options) - {"mode", "generated_paths"}
            or options.get("mode", "auto") not in {"auto", "git", "artifact"}):
        raise ValueError("workspace_identity supports auto/git/artifact and generated_paths")
    generated = options.get("generated_paths", [])
    if not isinstance(generated, list) or not all(isinstance(g, str) and bool(Path(g).parts) and not Path(g).is_absolute()
            and ".." not in Path(g).parts and ".git" not in Path(g).parts for g in generated):
        raise ValueError("generated_paths must be bounded relative paths")
    paths = profile["source_paths"]
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise ValueError("source_paths must name the files relevant to the claim")
    if any(Path(p) == Path(g) or Path(g) in Path(p).parents for p in paths for g in generated):
        raise ValueError("generated_paths cannot exclude declared sources")
    steps = profile["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= 50:
        raise ValueError("profile requires 1..50 steps")
    ids = set()
    phases = []
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"id", "phase", "argv", "timeout", "expect"}:
            raise ValueError("step requires id, phase, argv, timeout, expect")
        if not isinstance(step["id"], str) or not step["id"] or step["id"] in ids:
            raise ValueError("step IDs must be nonempty and unique")
        ids.add(step["id"])
        phase = step["phase"]
        if phase not in {"start", "doctor", "drive", "cleanup"}:
            raise ValueError("unsupported phase")
        phases.append(phase)
        argv = step["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a and "\0" not in a for a in argv):
            raise ValueError("argv must be a nonempty argument array")
        if type(step["timeout"]) not in (int, float) or not 0 < step["timeout"] <= 1800:
            raise ValueError("timeout must be in (0,1800] seconds")
        expected = step["expect"]
        if not isinstance(expected, dict) or not expected or not all(isinstance(p, str) and (p == "" or p.startswith("/")) for p in expected):
            raise ValueError("each step needs fixed JSON-pointer expectations")
    if "drive" not in phases:
        raise ValueError("profile needs an observable drive/check")
    if "start" in phases and (phases[0] != "start" or phases[-1] != "cleanup" or "doctor" not in phases):
        raise ValueError("a lifecycle profile requires start, doctor, drive, cleanup")
    if phases.count("start") > 1 or phases.count("cleanup") > 1 or ("cleanup" in phases and "start" not in phases):
        raise ValueError("one owned lifecycle requires exactly one start and cleanup")
    order = {"start": 0, "doctor": 1, "drive": 2, "cleanup": 3}
    if [order[p] for p in phases] != sorted(order[p] for p in phases):
        raise ValueError("phases must follow lifecycle order")


def execute(step: dict, workspace: Path) -> dict:
    record = {"id": step["id"], "phase": step["phase"], "status": "failed"}
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(step["argv"], cwd=workspace, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            try:
                process.wait(timeout=step["timeout"])
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    # A reaped leader does not mean its group is empty: a
                    # descendant may ignore SIGTERM. Reap the invocation group.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
                raise
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read(65537).decode(errors="replace")
            errors = stderr.read(4096).decode(errors="replace")
        record["exit_code"] = process.returncode
        # Results can contain private app evidence. Keep receipts private.
        record["stdout"] = output[:65536]
        record["stderr"] = errors
        if process.returncode:
            raise ValueError("command returned nonzero")
        if len(output.encode()) > 65536:
            raise ValueError("JSON output exceeds 64KiB; use app-owned evidence files")
        value = json.loads(output)
        for path, expected in step["expect"].items():
            observed = pointer(value, path)
            if json.dumps(observed, sort_keys=True) != json.dumps(expected, sort_keys=True):
                raise ValueError(f"expectation failed at {path}")
        record["status"] = "accepted"
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError, TypeError, KeyboardInterrupt) as exc:
        record["reason"] = str(exc) or "interrupted"
    return record


def run(profile: dict, workspace: Path) -> dict:
    validate(profile)
    before = source_identity(workspace, profile["source_paths"])
    workspace_before = workspace_identity(workspace, profile)
    results = [{"id": s["id"], "phase": s["phase"], "status": "not-run"} for s in profile["steps"]]
    failed = False
    started = False
    def checked(step, cleanup=False):
        try:
            if not cleanup and (source_identity(workspace, profile["source_paths"]) != before or workspace_identity(workspace, profile) != workspace_before):
                raise ValueError("source/workspace changed before this check")
            result = execute(step, workspace)
            result["source_after"] = source_identity(workspace, profile["source_paths"])
            result["workspace_after"] = workspace_identity(workspace, profile)
            if result["source_after"] != before or result["workspace_after"] != workspace_before:
                result.update(status="failed", reason="source/workspace changed during this step")
            return result
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return {"id": step["id"], "phase": step["phase"], "status": "failed", "reason": str(exc)}
    try:
        for index, step in enumerate(profile["steps"]):
            if step["phase"] == "cleanup" or failed:
                continue
            if step["phase"] == "start":
                # Uncertain startup can still own resources. The application
                # CLI's cleanup validates ownership; this helper never guesses.
                started = True
            results[index] = checked(step)
            failed |= results[index]["status"] != "accepted"
    except KeyboardInterrupt:
        failed = True
    finally:
        for index, step in enumerate(profile["steps"]):
            if step["phase"] == "cleanup" and started:
                results[index] = checked(step, cleanup=True)
                failed |= results[index]["status"] != "accepted"
    try:
        after = source_identity(workspace, profile["source_paths"])
        workspace_after = workspace_identity(workspace, profile)
        unchanged = before == after and workspace_before == workspace_after
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        after = {"error": str(exc)}
        workspace_after = after
        unchanged = False
    return {"version": 2, "workspace": str(workspace), "source_before": before,
            "source_after": after, "profile_sha256": profile_digest(profile),
            "workspace_before": workspace_before, "workspace_after": workspace_after,
            "claim": "profile expectations on captured inputs; does not prove app exercise or undeclared/ignored content",
            "checks": results, "passed": unchanged and not failed and all(r["status"] == "accepted" for r in results)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--receipt", type=Path)
    group.add_argument("--check-receipt", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if args.check_receipt is not None:
        result = check_freshness(json.loads(args.check_receipt.read_text()), json.loads(args.profile.read_text()), workspace)
        print(json.dumps(result))
        return 0 if result["fresh"] else 3
    if args.receipt.resolve().is_relative_to(workspace):
        raise ValueError("receipt must be outside the application checkout")
    # Reserve the receipt before any command effects; failed startup/checks
    # remain inspectable, and an existing receipt never causes a repeated run.
    with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        try:
            result = run(json.loads(args.profile.read_text()), workspace)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result = {"passed": False, "error": str(exc)}
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"passed": result["passed"], "receipt": str(args.receipt)}))
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    def terminate(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, terminate)
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
