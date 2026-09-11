"""Runner-owned, bounded evidence for Inspect workspaces.

The candidate runs in a workspace it can mutate, including the workspace's
``.git`` metadata.  This module therefore captures a filesystem snapshot
before candidate execution and compares it with a second snapshot afterwards.
Git is used for trusted pre-candidate inventory and, only after the validated
``.git`` boundary remains unchanged, bounded post-candidate revision/index/blob
plumbing.  Filter, text-conversion, replacement-ref, and external-diff paths
are disabled.  No evidence path is followed through a symlink, hardlink, or
filesystem mount boundary.
"""

from __future__ import annotations

import hashlib
import os
import re
import selectors
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


DEFAULT_MAX_BYTES = 20_000
DEFAULT_MAX_PATHS = 10_000
DEFAULT_SNAPSHOT_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_SNAPSHOT_TOTAL_BYTES = 64 * 1024 * 1024
DEFAULT_EVIDENCE_MAX_BYTES = 512 * 1024
_BWRAP_REQUIRED_MOUNTS = ("/usr", "/bin", "/lib", "/lib64", "/etc")
# Protect names that are themselves credential containers, not every source
# filename that happens to mention a security concept.  Content-level
# redaction remains the fallback for ordinary source and report files.
_SENSITIVE_EXAMPLE_NAMES = {".env.example", ".env.sample", ".env.template"}
_SENSITIVE_EXACT_NAMES = {
    "secret",
    "secrets",
    "credential",
    "credentials",
    "password",
    "passwords",
    "passwd",
    "private",
    "private_key",
    "token",
    "tokens",
    "api_key",
    "apikey",
    "api_token",
    "auth_token",
    "access_token",
    "refresh_token",
    "client_secret",
    "id_rsa",
    "id_ed25519",
}
_SENSITIVE_SUFFIXES = (
    ".secret",
    ".secrets",
    ".credential",
    ".credentials",
    ".password",
    ".passwd",
    ".private",
    ".token",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
)
_SENSITIVE_DIRECTORY_NAMES = {
    "secret",
    "secrets",
    "credential",
    "credentials",
    "private",
}
# Only well-known interpreter/test cache locations are auxiliary by default.
# An arbitrary binary created by a candidate remains material unless the task
# explicitly identifies it as a required artifact and the collector can read
# it safely.
_AUXILIARY_BINARY_DIRECTORIES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
}
_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^(\s*(?:[A-Z0-9_.-]*(?:secret|token|password|private[_ -]?key|api[_ -]?key)"
    r"[A-Z0-9_.-]*)\s*[:=]\s*)([^\s#]+)(.*)$"
)
_PEM_BLOCK = re.compile(
    r"(?s)-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----"
)
# ``git ls-files -v --stage -z`` exposes the semantic index fields and the
# documented status tag without the mutable, human-oriented ``--debug``
# stat-cache dump.  Keep the two flags that affect our comparison in the
# same representation used by Git's index, but derive them from the tags
# rather than parsing the binary index or guessing a numeric base.
_INDEX_ASSUME_UNCHANGED = 0x8000
_INDEX_SKIP_WORKTREE = 0x4000
_INDEX_TAG_FLAGS = {
    "H": 0,
    "h": _INDEX_ASSUME_UNCHANGED,
    "S": _INDEX_SKIP_WORKTREE,
    "s": _INDEX_ASSUME_UNCHANGED | _INDEX_SKIP_WORKTREE,
    # An unmerged cached entry is valid and its stage field is authoritative.
    "U": 0,
}


def bwrap_preflight(workspace: Path | str | None = None) -> str | None:
    """Check the supported Bubblewrap namespace before an execution.

    A ``None`` return means the namespace probe succeeded.  This is a
    prerequisite for runner-owned Git commands; it is not a claim that the
    Inspect local sandbox contains Python reads or native Codex execution.
    Those live/adversarial arrangements remain explicitly unsupported.
    """

    bwrap = shutil.which("bwrap")
    if bwrap is None:
        return "Bubblewrap is required but not installed"
    for mount in _BWRAP_REQUIRED_MOUNTS:
        if not Path(mount).exists():
            return f"Bubblewrap prerequisite mount is unavailable: {mount}"

    command = [
        bwrap,
        "--die-with-parent",
        "--unshare-all",
    ]
    if workspace is not None:
        root = Path(workspace).resolve()
        if not root.is_dir():
            return f"workspace is not a directory for Bubblewrap preflight: {root}"
        command.extend(["--ro-bind", str(root), "/workspace"])
    command.extend(
        [
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--ro-bind",
            "/etc",
            "/etc",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--clearenv",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
        ]
    )
    if workspace is not None:
        command.extend(["--chdir", "/workspace"])
    command.append("/bin/true")
    try:
        result = subprocess.run(
            command,
            env={"PATH": "/usr/bin:/bin"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Bubblewrap namespace preflight failed: {exc}"
    if result.returncode:
        detail = _decode(result.stderr).strip() or "no diagnostic"
        return f"Bubblewrap namespace preflight failed (exit {result.returncode}): {detail}"
    return None


@dataclass(frozen=True)
class Baseline:
    """Trusted state captured immediately before candidate execution."""

    status: str
    revision: str | None = None
    initial_paths: tuple[str, ...] = ()
    tracked_paths: tuple[str, ...] = ()
    # (path, object ID, file mode, merge stage, semantic index flags). Git's
    # maintained listing intentionally omits the mutable stat-cache fields.
    index_entries: tuple[tuple[str, str, int, int, int], ...] = ()
    object_id_bytes: int = 20
    # (kind, device, inode, target-or-note); only a real local directory is
    # accepted so post-candidate Git plumbing cannot be redirected elsewhere.
    git_boundary: tuple[str, int, int, str | None] = ()
    # (relative path, kind, size, digest, target-or-note)
    snapshot: tuple[tuple[str, str, int | None, str | None, str | None], ...] = ()
    git_control: tuple[tuple[str, str, int | None, str | None], ...] = ()
    snapshot_omissions: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def available(self) -> bool:
        return self.status == "available" and bool(self.revision)


@dataclass(frozen=True)
class Evidence:
    """Bounded final observation, with changes split by observable boundary."""

    status: str
    available: bool
    baseline_revision: str | None = None
    final_revision: str | None = None
    tracked_worktree_paths: tuple[str, ...] = ()
    tracked_index_paths: tuple[str, ...] = ()
    tracked_paths: tuple[str, ...] = ()
    committed_paths: tuple[str, ...] = ()
    baseline_untracked_paths: tuple[str, ...] = ()
    current_untracked_paths: tuple[str, ...] = ()
    untracked_paths: tuple[str, ...] = ()
    required_paths: tuple[str, ...] = ()
    content: tuple[str, ...] = ()
    omissions: tuple[str, ...] = ()
    truncated: bool = False
    index_changed: bool = False
    git_metadata_changed: bool = False
    has_changes: bool = False
    outcome: str = "unavailable"
    reason: str | None = None

    def as_text(self) -> str:
        """Render structured fields and bounded content for a behavior grader."""

        fields = [
            f"STATUS: {self.status}",
            f"BASELINE REVISION: {self.baseline_revision or 'unavailable'}",
            f"FINAL REVISION: {self.final_revision or 'unavailable'}",
            f"OUTCOME: {self.outcome}",
            f"TRACKED WORKTREE PATHS: {list(self.tracked_worktree_paths)}",
            f"TRACKED INDEX PATHS: {list(self.tracked_index_paths)}",
            f"TRACKED PATHS SINCE BASELINE: {list(self.tracked_paths)}",
            f"COMMITTED PATHS: {list(self.committed_paths)}",
            f"BASELINE UNTRACKED PATHS: {list(self.baseline_untracked_paths)}",
            f"CURRENT UNTRACKED PATHS: {list(self.current_untracked_paths)}",
            f"UNTRACKED PATHS: {list(self.untracked_paths)}",
            f"REQUIRED PATHS: {list(self.required_paths)}",
            f"INDEX CHANGED: {self.index_changed}",
            f"GIT METADATA CHANGED: {self.git_metadata_changed}",
        ]
        if self.reason:
            fields.append(f"REASON: {self.reason}")
        if self.omissions:
            fields.append("OMISSIONS: " + "; ".join(self.omissions))
        fields.extend(self.content)
        return "\n".join(fields)


def _git(
    workspace: Path,
    args: Sequence[str],
    *,
    output_limit: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run fixed Git argv with a finite timeout and bounded output."""

    command = ["git", *args]
    bwrap = shutil.which("bwrap")
    if bwrap is None:
        return subprocess.CompletedProcess(
            command,
            125,
            stdout=b"",
            stderr=b"contained Git execution unavailable: bwrap is not installed",
        )
    contained_command = [
        bwrap,
        "--die-with-parent",
        "--unshare-all",
        "--ro-bind",
        str(workspace),
        "/workspace",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--ro-bind",
        "/etc",
        "/etc",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--clearenv",
        "--setenv",
        "HOME",
        "/tmp",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--setenv",
        "GIT_CONFIG_NOSYSTEM",
        "1",
        "--setenv",
        "GIT_CONFIG_GLOBAL",
        "/dev/null",
        "--setenv",
        "GIT_NO_REPLACE_OBJECTS",
        "1",
        "--setenv",
        "GIT_OPTIONAL_LOCKS",
        "0",
        "--setenv",
        "GIT_PAGER",
        "cat",
        "--chdir",
        "/workspace",
        "git",
        *args,
    ]
    process = subprocess.Popen(
        contained_command,
        env={"PATH": "/usr/bin:/bin"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if output_limit is None:
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(
                command,
                124,
                stdout=stdout,
                stderr=(stderr or b"") + b" git command timed out",
            )
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    selector = selectors.DefaultSelector()
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    stdout_truncated = False
    try:
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        deadline = time.monotonic() + 30
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, 30)
            for key, _ in selector.select(remaining):
                try:
                    data = os.read(key.fd, 64 * 1024)
                except OSError:
                    data = b""
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    room = output_limit + 1 - len(stdout_buffer)
                    if room > 0:
                        stdout_buffer.extend(data[:room])
                    if len(stdout_buffer) > output_limit and not stdout_truncated:
                        stdout_truncated = True
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                elif len(stderr_buffer) < 64 * 1024:
                    stderr_buffer.extend(data[: 64 * 1024 - len(stderr_buffer)])
        return subprocess.CompletedProcess(
            command,
            0 if stdout_truncated else process.wait(timeout=1),
            stdout=bytes(stdout_buffer),
            stderr=(
                bytes(stderr_buffer) + b" (output truncated by evaluator)"
                if stdout_truncated
                else bytes(stderr_buffer)
            ),
        )
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(
            command,
            124,
            stdout=stdout[: output_limit + 1],
            stderr=(stderr or b"")[: 64 * 1024] + b" git command timed out",
        )
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="surrogateescape")


def _nul_paths(raw: bytes) -> tuple[str, ...]:
    return tuple(_decode(item) for item in raw.split(b"\0") if item)


def _bounded_unique(
    paths: Iterable[str], limit: int = DEFAULT_MAX_PATHS
) -> tuple[tuple[str, ...], bool]:
    result: list[str] = []
    seen: set[str] = set()
    overflow = False
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        if len(result) >= limit:
            overflow = True
            continue
        result.append(path)
    return tuple(result), overflow


def _unique(paths: Iterable[str], limit: int = DEFAULT_MAX_PATHS) -> tuple[str, ...]:
    """Compatibility helper for callers that only need bounded names."""

    return _bounded_unique(paths, limit)[0]


def validate_relative_path(path: str) -> bool:
    """Reject absolute, parent-traversing, empty, and NUL-containing paths."""

    if not path or "\0" in path:
        return False
    pure = PurePosixPath(path)
    return not pure.is_absolute() and all(part not in {".", ".."} for part in pure.parts)


def _sensitive(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    if name in _SENSITIVE_EXAMPLE_NAMES:
        return False
    if name == ".env" or name.startswith(".env."):
        return True

    # Normalize separators only within a basename.  This keeps
    # ``reset_password.py`` and ``tokenizer.py`` inspectable while still
    # recognizing conventional credential container names.
    stem = name.rsplit(".", 1)[0] if "." in name and not name.startswith(".") else name
    normalized = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    if normalized in _SENSITIVE_EXACT_NAMES:
        return True
    if any(name.endswith(suffix) for suffix in _SENSITIVE_SUFFIXES):
        return True

    # A directory explicitly named for secret material is a useful boundary;
    # arbitrary substrings in source paths are not.
    return any(
        component.lower() in _SENSITIVE_DIRECTORY_NAMES
        for component in PurePosixPath(path).parts[:-1]
    )

def _redact_text(raw: str) -> str:
    """Redact common secret assignments before evidence reaches a grader."""

    raw = _PEM_BLOCK.sub("[REDACTED PRIVATE KEY]", raw)
    return _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]\3", raw)


def _is_auxiliary_binary(relative: str) -> bool:
    """Recognize bounded runtime caches without making arbitrary binaries harmless."""

    return any(
        component in _AUXILIARY_BINARY_DIRECTORIES
        for component in PurePosixPath(relative).parts
    )


def _safe_open(path: Path, root_dev: int) -> tuple[int, os.stat_result] | None:
    """Open a regular file without following links or crossing a mount."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        info = os.fstat(descriptor)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_dev != root_dev or info.st_nlink > 1:
        os.close(descriptor)
        return None
    return descriptor, info


def _digest_descriptor(descriptor: int, size: int, max_bytes: int) -> str | None:
    if size > max_bytes:
        return None
    digest = hashlib.sha256()
    remaining = size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            return None
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def _read_bounded(
    workspace: Path,
    relative: str,
    max_bytes: int,
    *,
    required: bool = False,
    label: str | None = None,
) -> tuple[str, bool, str | None]:
    """Read a regular in-workspace file without following any boundary."""

    label = label or ("REQUIRED" if required else "UNTRACKED")
    if not validate_relative_path(relative):
        return f"{label} PATH {relative}: rejected (must be workspace-relative)", False, "path-boundary"
    root = workspace.resolve()
    path = root / relative
    try:
        path.relative_to(root)
        info = path.lstat()
    except (FileNotFoundError, OSError, ValueError) as exc:
        return f"{label} FILE {relative}: MISSING ({exc})", False, "missing"
    if stat.S_ISLNK(info.st_mode):
        try:
            target = os.readlink(path)
        except OSError as exc:
            target = f"unreadable ({exc})"
        return f"SYMLINK {label} PATH {relative} -> {target}; content not followed", True, None
    root_info = root.stat()
    if not stat.S_ISREG(info.st_mode):
        return f"{label} PATH {relative}: not a regular file", False, "not-regular"
    if info.st_dev != root_info.st_dev:
        return f"{label} FILE {relative}: content omitted (mount boundary)", False, "mount-boundary"
    if info.st_nlink > 1:
        return f"{label} FILE {relative}: content omitted (hardlink boundary; size={info.st_size})", False, "hardlink-boundary"
    if _sensitive(relative):
        return f"{label} FILE {relative}: content omitted (sensitive-looking path; size={info.st_size})", False, "sensitive-omitted"
    if info.st_size > max_bytes:
        return f"{label} FILE {relative}: content truncated (size={info.st_size}, limit={max_bytes})", False, "truncated"
    opened = _safe_open(path, root_info.st_dev)
    if opened is None:
        return f"{label} FILE {relative}: content could not be safely opened", False, "unsafe-open"
    descriptor, opened_info = opened
    try:
        digest = _digest_descriptor(descriptor, opened_info.st_size, max_bytes)
        if digest is None:
            return f"{label} FILE {relative}: content could not be safely read", False, "unreadable"
        os.lseek(descriptor, 0, os.SEEK_SET)
        raw = os.read(descriptor, max_bytes + 1)
    except OSError as exc:
        return f"{label} FILE {relative}: unreadable ({exc})", False, "unreadable"
    finally:
        os.close(descriptor)
    if len(raw) > max_bytes:
        return f"{label} FILE {relative}: content truncated (limit={max_bytes})", False, "truncated"
    if b"\0" in raw:
        return f"{label} FILE {relative}: binary content omitted (size={len(raw)})", False, "binary"
    return f"{label} FILE {relative}:\n{_redact_text(_decode(raw))}", True, None


def _entry_tuple(
    relative: str,
    kind: str,
    size: int | None,
    digest: str | None,
    target_or_note: str | None = None,
) -> tuple[str, str, int | None, str | None, str | None]:
    return (relative, kind, size, digest, target_or_note)


def _snapshot_workspace(
    root: Path,
    *,
    max_bytes: int = DEFAULT_SNAPSHOT_MAX_BYTES,
    max_paths: int = DEFAULT_MAX_PATHS,
    total_bytes: int = DEFAULT_SNAPSHOT_TOTAL_BYTES,
    protected_git_identity: tuple[int, int] | None = None,
) -> tuple[tuple[tuple[str, str, int | None, str | None, str | None], ...], tuple[str, ...], bool]:
    """Snapshot visible workspace files without traversing ``.git`` or links."""

    if max_bytes <= 0 or max_paths <= 0 or total_bytes <= 0:
        return (), ("snapshot limits must be positive",), True
    try:
        root_info = root.stat()
    except OSError as exc:
        return (), (f"workspace stat failed: {exc}",), False
    entries: list[tuple[str, str, int | None, str | None, str | None]] = []
    omissions: list[str] = []
    total_read = 0
    truncated = False
    stack: list[tuple[Path, str]] = [(root, "")]

    while stack:
        directory, prefix = stack.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            omissions.append(f"{prefix or '.'}: directory enumeration failed ({exc})")
            continue
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if relative == ".git":
                continue
            if len(entries) >= max_paths:
                truncated = True
                omissions.append(f"path limit exceeded ({max_paths})")
                break
            try:
                info = child.stat(follow_symlinks=False)
            except OSError as exc:
                omissions.append(f"{relative}: stat failed ({exc})")
                continue
            mode = info.st_mode
            # A candidate may rename the runner-authorized .git directory and
            # replace the root with another repository.  Protect the original
            # object by identity, not by a filename prefix: tracked files such
            # as .git-blame-ignore-revs are ordinary workspace artifacts.
            if (
                not prefix
                and protected_git_identity is not None
                and stat.S_ISDIR(mode)
                and (int(info.st_dev), int(info.st_ino)) == protected_git_identity
            ):
                entries.append(_entry_tuple(relative, "git-alias", None, None, "metadata boundary"))
                omissions.append(f"{relative}: original Git metadata boundary not traversed")
                continue
            if stat.S_ISLNK(mode):
                try:
                    target = os.readlink(child.path)
                except OSError as exc:
                    target = f"unreadable ({exc})"
                entries.append(_entry_tuple(relative, "symlink", None, None, target))
                continue
            if stat.S_ISDIR(mode):
                if info.st_dev != root_info.st_dev:
                    entries.append(_entry_tuple(relative, "mount", None, None, "mount boundary"))
                    omissions.append(f"{relative}: mount boundary not traversed")
                else:
                    stack.append((Path(child.path), relative))
                continue
            if stat.S_ISREG(mode):
                if info.st_dev != root_info.st_dev:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "mount boundary"))
                    omissions.append(f"{relative}: mount boundary content omitted")
                    continue
                if info.st_nlink > 1:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "hardlink boundary"))
                    omissions.append(f"{relative}: hardlink content omitted")
                    continue
                if _sensitive(relative):
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "sensitive content omitted"))
                    omissions.append(f"{relative}: sensitive content omitted")
                    continue
                if info.st_size > max_bytes:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "file size limit"))
                    omissions.append(f"{relative}: file exceeds snapshot limit {max_bytes}")
                    truncated = True
                    continue
                if total_read + info.st_size > total_bytes:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "snapshot byte budget"))
                    omissions.append(f"{relative}: snapshot byte budget exceeded")
                    truncated = True
                    continue
                opened = _safe_open(Path(child.path), root_info.st_dev)
                if opened is None:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "unsafe open"))
                    omissions.append(f"{relative}: safe open failed")
                    continue
                descriptor, opened_info = opened
                try:
                    digest = _digest_descriptor(descriptor, opened_info.st_size, max_bytes)
                finally:
                    os.close(descriptor)
                if digest is None:
                    entries.append(_entry_tuple(relative, "file", info.st_size, None, "unreadable"))
                    omissions.append(f"{relative}: digest failed")
                    continue
                # Keep the executable/mode bits in the identity so a chmod-only
                # change is not mistaken for an unchanged workspace.
                entries.append(
                    _entry_tuple(
                        relative,
                        "file",
                        info.st_size,
                        digest,
                        str(stat.S_IMODE(info.st_mode)),
                    )
                )
                total_read += info.st_size
                continue
            entries.append(_entry_tuple(relative, "other", None, None, "unsupported file type"))
            omissions.append(f"{relative}: unsupported file type")
        if truncated:
            # There is no meaningful way to enumerate omitted descendants once
            # the bounded path contract has been exceeded.
            break
    entries.sort(key=lambda item: item[0])
    return tuple(entries), tuple(omissions), truncated


def _capture_git_boundary(
    root: Path,
) -> tuple[tuple[str, int, int, str | None], str | None]:
    """Capture the only Git metadata location the runner authorizes.

    A normal disposable repository owns ``.git`` as a directory on the same
    filesystem as the workspace.  Gitfiles, symlinks, and mount redirects are
    deliberately unsupported: accepting them would let candidate-controlled
    metadata choose a different repository before the evaluator can compare
    objects or index entries.
    """

    git_path = root / ".git"
    try:
        root_info = root.stat()
        info = git_path.lstat()
    except OSError as exc:
        return (), f".git boundary unavailable ({exc})"
    if not stat.S_ISDIR(info.st_mode):
        return (), ".git boundary must be a directory, not a symlink or gitfile"
    if info.st_dev != root_info.st_dev:
        return (), ".git boundary crosses a filesystem mount"
    return ("directory", int(info.st_dev), int(info.st_ino), None), None


def _validate_git_boundary(
    root: Path,
    expected: Sequence[str | int | None],
    *,
    allow_missing_index: bool = False,
) -> str | None:
    """Reject a post-candidate metadata redirect before any Git command."""

    if not expected:
        return "baseline did not record an authorized .git boundary"
    current, error = _capture_git_boundary(root)
    if error:
        return error
    if tuple(current) != tuple(expected):
        return ".git metadata boundary changed after baseline capture"
    root_dev = root.stat().st_dev
    # Git can redirect object lookup through an internal symlink or an
    # ``objects/info/alternates`` file without changing the .git inode. Reject
    # those alternate metadata roots before invoking post-candidate plumbing.
    for relative in (
        ".git/objects",
        ".git/objects/info",
        ".git/objects/info/alternates",
        ".git/refs",
        ".git/HEAD",
        ".git/index",
        ".git/config",
    ):
        path = root / relative
        try:
            info = path.lstat()
        except OSError as exc:
            if relative == ".git/objects/info/alternates" and isinstance(exc, FileNotFoundError):
                continue
            if relative == ".git/index" and allow_missing_index and isinstance(exc, FileNotFoundError):
                continue
            return f"Git metadata path {relative} unavailable ({exc})"
        if stat.S_ISLNK(info.st_mode):
            return f"Git metadata path {relative} is a symlink"
        if info.st_dev != root_dev:
            return f"Git metadata path {relative} crosses a filesystem mount"
        if relative == ".git/objects/info/alternates":
            return "Git object alternates are not an authorized evidence boundary"
        if relative in {".git/HEAD", ".git/index", ".git/config"} and not stat.S_ISREG(info.st_mode):
            return f"Git metadata path {relative} is not a regular file"
    return None


def _validate_object_path(root: Path, oid: str) -> str | None:
    """Reject redirects on the concrete Git object path before ``cat-file``."""

    if not re.fullmatch(r"[0-9a-f]{40,64}", oid):
        return f"invalid Git object ID {oid!r}"
    root_dev = root.stat().st_dev
    objects = root / ".git" / "objects"
    try:
        objects_info = objects.lstat()
    except OSError as exc:
        return f"Git object store unavailable ({exc})"
    if stat.S_ISLNK(objects_info.st_mode) or objects_info.st_dev != root_dev:
        return "Git object store crosses a filesystem boundary"

    fanout = objects / oid[:2]
    try:
        fanout_info = fanout.lstat()
    except FileNotFoundError:
        fanout_info = None
    except OSError as exc:
        return f"Git object fan-out could not be checked ({exc})"
    if fanout_info is not None:
        if stat.S_ISLNK(fanout_info.st_mode):
            return f"Git object fan-out {oid[:2]} is a symlink"
        if not stat.S_ISDIR(fanout_info.st_mode) or fanout_info.st_dev != root_dev:
            return f"Git object fan-out {oid[:2]} crosses a filesystem boundary"
        loose = fanout / oid[2:]
        try:
            loose_info = loose.lstat()
        except FileNotFoundError:
            loose_info = None
        except OSError as exc:
            return f"Git loose object could not be checked ({exc})"
        if loose_info is not None:
            if stat.S_ISLNK(loose_info.st_mode):
                return f"Git loose object {oid} is a symlink"
            if not stat.S_ISREG(loose_info.st_mode) or loose_info.st_dev != root_dev:
                return f"Git loose object {oid} crosses a filesystem boundary"

    pack_dir = objects / "pack"
    try:
        pack_info = pack_dir.lstat()
    except FileNotFoundError:
        pack_info = None
    except OSError as exc:
        return f"Git pack directory could not be checked ({exc})"
    if pack_info is not None:
        if stat.S_ISLNK(pack_info.st_mode) or not stat.S_ISDIR(pack_info.st_mode):
            return "Git pack directory is not a local directory"
        if pack_info.st_dev != root_dev:
            return "Git pack directory crosses a filesystem boundary"
        try:
            pack_files = list(os.scandir(pack_dir))
        except OSError as exc:
            return f"Git pack directory enumeration failed ({exc})"
        if len(pack_files) > DEFAULT_MAX_PATHS:
            return "Git pack directory exceeds the bounded path limit"
        for child in pack_files:
            try:
                child_info = child.stat(follow_symlinks=False)
            except OSError as exc:
                return f"Git pack entry {child.name} could not be checked ({exc})"
            if stat.S_ISLNK(child_info.st_mode):
                return f"Git pack entry {child.name} is a symlink"
            if child_info.st_dev != root_dev:
                return f"Git pack entry {child.name} crosses a filesystem boundary"
    return None


def _control_snapshot(
    root: Path,
    *,
    max_bytes: int = DEFAULT_SNAPSHOT_MAX_BYTES,
    max_paths: int = DEFAULT_MAX_PATHS,
    allow_missing_index: bool = False,
) -> tuple[tuple[tuple[str, str, int | None, str | None], ...], tuple[str, ...], bool]:
    """Record only fixed Git controls and maintained ref output.

    This is deliberately not a recursive ``.git`` scanner.  Object reads are
    performed by the contained ``_git`` route; the evidence contract only
    needs fixed control files plus Git's own ref listing to identify semantic
    metadata changes.
    """

    entries: list[tuple[str, str, int | None, str | None]] = []
    omissions: list[str] = []
    root_dev = root.stat().st_dev
    for relative in (".git/HEAD", ".git/config", ".git/index"):
        path = root / relative
        try:
            info = path.lstat()
        except OSError as exc:
            if relative == ".git/index" and allow_missing_index and isinstance(exc, FileNotFoundError):
                # An empty initial commit is allowed to have no index file.
                # Preserve that fact as an explicit control entry so a later
                # candidate-created index is still observable.
                entries.append((relative, "missing", None, None))
                continue
            omissions.append(f"{relative}: unavailable ({exc})")
            continue
        if stat.S_ISLNK(info.st_mode):
            omissions.append(f"{relative}: symlink control boundary")
            entries.append((relative, "symlink", None, "not followed"))
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_dev != root_dev:
            omissions.append(f"{relative}: control boundary is not a local regular file")
            entries.append((relative, "file", info.st_size, "omitted"))
            continue
        opened = _safe_open(path, root_dev)
        if opened is None:
            omissions.append(f"{relative}: safe open failed")
            entries.append((relative, "file", info.st_size, "omitted"))
            continue
        descriptor, opened_info = opened
        try:
            digest = _digest_descriptor(descriptor, opened_info.st_size, max_bytes)
        finally:
            os.close(descriptor)
        if digest is None:
            omissions.append(f"{relative}: control file exceeds snapshot limit")
            digest = "omitted"
        entries.append((relative, "file", opened_info.st_size, digest))

    refs = _git(
        root,
        ["for-each-ref", "--format=%(refname) %(objectname)", "--sort=refname"],
        output_limit=max_bytes,
    )
    refs_error = _error(refs)
    if refs_error:
        omissions.append(f"Git refs: {refs_error}")
    else:
        raw_refs = refs.stdout
        if "output truncated by evaluator" in _decode(refs.stderr):
            omissions.append("Git refs: output truncated")
        elif len(raw_refs) > max_bytes:
            omissions.append(f"Git refs: output exceeds snapshot limit {max_bytes}")
        else:
            entries.append((".git/refs", "git-output", len(raw_refs), hashlib.sha256(raw_refs).hexdigest()))

    return tuple(sorted(entries)), tuple(omissions), bool(omissions)


def _error(result: subprocess.CompletedProcess[bytes]) -> str | None:
    if result.returncode == 0:
        return None
    return result.stderr.decode("utf-8", errors="replace").strip() or "git command failed"


def _git_paths(
    result: subprocess.CompletedProcess[bytes],
    *,
    max_paths: int,
) -> tuple[tuple[str, ...], str | None, bool]:
    error = _error(result)
    if error:
        return (), error, False
    paths, overflow = _bounded_unique(_nul_paths(result.stdout), max_paths)
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    if "output truncated by evaluator" in stderr:
        overflow = True
    return paths, None, overflow


def _read_index_entries(
    root: Path,
    *,
    object_id_bytes: int,
    max_paths: int,
    max_bytes: int,
) -> tuple[tuple[tuple[str, str, int, int, int], ...], str | None, bool]:
    """Read semantic index entries through Git's maintained interface.

    ``--stage`` supplies mode/object/stage fields and ``-v`` supplies the
    documented assume-unchanged/skip-worktree tags.  A successful zero-byte
    response is a valid empty index, including an empty initial commit whose
    index file is absent.  Any non-empty malformed record remains unavailable.
    """

    result = _git(
        root,
        ["ls-files", "--cached", "--stage", "-v", "--full-name", "-z"],
        output_limit=max_bytes,
    )
    error = _error(result)
    if error:
        return (), error, False
    if "output truncated by evaluator" in _decode(result.stderr):
        return (), "Git index listing exceeded the bounded output limit", True

    records: list[tuple[str, str, int, int, int]] = []
    if not result.stdout:
        return (), None, False
    chunks = result.stdout.split(b"\0")
    if chunks[-1] != b"":
        return (), "incomplete Git index listing record", False
    for chunk in chunks[:-1]:
        if not chunk:
            return (), "invalid empty Git index listing record", False
        try:
            raw_header, raw_path = chunk.split(b"\t", 1)
            header = raw_header.decode("ascii").split()
            if len(header) != 4:
                raise ValueError("expected status, mode, object ID, and stage fields")
            tag, mode_text, oid, stage_text = header
            try:
                flags = _INDEX_TAG_FLAGS[tag]
            except KeyError as exc:
                raise ValueError(f"unsupported Git index status tag {tag!r}") from exc
            path = _decode(raw_path)
            mode = int(mode_text, 8)
            stage = int(stage_text, 10)
        except (UnicodeDecodeError, ValueError) as exc:
            return tuple(records), f"invalid Git index listing record ({exc})", False
        if len(oid) != object_id_bytes * 2:
            return tuple(records), f"invalid Git object ID for {path!r}", False
        if not validate_relative_path(path):
            return tuple(records), f"invalid Git index path {path!r}", False
        if len(records) >= max_paths:
            return tuple(records), None, True
        records.append((path, oid, mode, stage, flags))
    return tuple(records), None, False


def _object_blob(
    root: Path,
    relative: str,
    oid: str,
    max_bytes: int,
    *,
    label: str,
) -> tuple[str, bool, str | None]:
    """Render a bounded Git object without filters, attributes, or hooks."""

    if not validate_relative_path(relative) or _sensitive(relative):
        reason = "path-boundary" if not validate_relative_path(relative) else "sensitive-omitted"
        return f"{label} FILE {relative}: content omitted ({reason})", False, reason
    object_boundary_error = _validate_object_path(root, oid)
    if object_boundary_error:
        return (
            f"{label} FILE {relative}: unreadable ({object_boundary_error})",
            False,
            "unreadable",
        )
    result = _git(root, ["cat-file", "blob", oid], output_limit=max_bytes)
    error = _error(result)
    if error:
        return f"{label} FILE {relative}: unreadable ({error})", False, "unreadable"
    raw = result.stdout
    if len(raw) > max_bytes or "output truncated by evaluator" in _decode(result.stderr):
        return f"{label} FILE {relative}: content truncated (limit={max_bytes})", False, "truncated"
    if b"\0" in raw:
        return f"{label} FILE {relative}: binary content omitted (size={len(raw)})", False, "binary"
    return f"{label} FILE {relative}:\n{_redact_text(_decode(raw))}", True, None


def _index_blob(
    root: Path,
    relative: str,
    oid: str,
    max_bytes: int,
) -> tuple[str, bool, str | None]:
    """Render a bounded index blob via plumbing that does not apply filters."""

    return _object_blob(root, relative, oid, max_bytes, label="INDEX")


def _committed_entries(
    root: Path,
    baseline_revision: str,
    final_revision: str,
    *,
    max_paths: int,
    max_bytes: int,
) -> tuple[tuple[tuple[str, str | None], ...], str | None, bool]:
    """Return baseline-to-HEAD paths and final blob IDs from Git plumbing."""

    if baseline_revision == final_revision:
        return (), None, False
    result = _git(
        root,
        [
            "diff-tree",
            "--no-commit-id",
            "--raw",
            "-r",
            "-z",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            baseline_revision,
            final_revision,
        ],
        output_limit=max_bytes,
    )
    error = _error(result)
    stderr = _decode(result.stderr)
    if error:
        return (), error, False
    if "output truncated by evaluator" in stderr:
        return (), "committed diff exceeded the bounded output limit", True

    fields = result.stdout.split(b"\0")
    entries: list[tuple[str, str | None]] = []
    index = 0
    while index < len(fields):
        header = fields[index]
        index += 1
        if not header:
            continue
        if not header.startswith(b":") or index >= len(fields):
            return tuple(entries), "invalid Git raw diff record", False
        header_fields = header[1:].split()
        if len(header_fields) < 5:
            return tuple(entries), "incomplete Git raw diff record", False
        path = _decode(fields[index])
        index += 1
        if not validate_relative_path(path):
            return tuple(entries), f"invalid committed path {path!r}", False
        if len(entries) >= max_paths:
            return tuple(entries), f"committed path limit exceeded: {max_paths}", True
        new_oid = _decode(header_fields[3])
        entries.append((path, None if not new_oid.strip("0") else new_oid))
    return tuple(entries), None, False


def _path_boundary_records(
    root: Path,
    required: Sequence[str],
    max_bytes: int,
) -> tuple[list[str], list[str], bool]:
    content: list[str] = []
    omissions: list[str] = []
    truncated = False
    for relative in required:
        if not validate_relative_path(relative):
            content.append(f"REQUIRED PATH {relative}: rejected (must be workspace-relative)")
            omissions.append(f"{relative}: path-boundary")
            continue
        parts = PurePosixPath(relative).parts
        if parts and parts[0] == ".git":
            content.append(
                f"REQUIRED PATH {relative}: content omitted (Git metadata boundary)"
            )
            omissions.append(f"{relative}: git-boundary")
            continue
        current = root
        symlink = False
        for part in PurePosixPath(relative).parts:
            current = current / part
            try:
                if current.is_symlink():
                    symlink = True
                    break
            except OSError:
                break
        if symlink:
            try:
                target = os.readlink(current)
            except OSError as exc:
                target = f"unreadable ({exc})"
            content.append(f"SYMLINK REQUIRED PATH {relative} -> {target}; content not followed")
            omissions.append(f"{relative}: symlink-boundary")
            continue
        rendered, readable, reason = _read_bounded(root, relative, max_bytes, required=True)
        content.append(rendered)
        if not readable:
            omissions.append(f"{relative}: {reason}")
            truncated = truncated or reason in {"truncated", "binary"}
    return content, omissions, truncated


def _object_id_bytes(root: Path) -> tuple[int, str | None]:
    """Read the repository object format before candidate metadata is mutable."""

    result = _git(root, ["rev-parse", "--show-object-format"])
    error = _error(result)
    if error:
        return 0, error
    object_format = _decode(result.stdout).strip()
    if object_format == "sha1":
        return 20, None
    if object_format == "sha256":
        return 32, None
    return 0, f"unsupported Git object format: {object_format or 'empty'}"


def capture_baseline(
    workspace: Path | str,
    *,
    max_paths: int = DEFAULT_MAX_PATHS,
    snapshot_max_bytes: int = DEFAULT_SNAPSHOT_MAX_BYTES,
) -> Baseline:
    """Capture a clean disposable starting revision and filesystem snapshot."""

    root = Path(workspace).resolve()
    preflight_error = bwrap_preflight(root)
    if preflight_error:
        return Baseline(status="unavailable", reason=preflight_error)
    git_boundary, boundary_error = _capture_git_boundary(root)
    if boundary_error:
        return Baseline(status="unavailable", reason=boundary_error)
    revision = _git(root, ["rev-parse", "HEAD"])
    revision_error = _error(revision)
    if revision_error:
        return Baseline(
            status="unavailable",
            git_boundary=git_boundary,
            reason=revision_error,
        )
    revision_text = _decode(revision.stdout).strip() or None
    if revision_text is None:
        return Baseline(
            status="unavailable",
            git_boundary=git_boundary,
            reason="baseline revision was empty",
        )

    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    status_error = _error(status)
    if status_error:
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            reason=status_error,
        )
    initial_paths, initial_overflow = _bounded_unique(_nul_paths(status.stdout), max_paths)
    if initial_paths or initial_overflow:
        reason = "initial workspace is dirty; clean disposable fixtures are required"
        if initial_overflow:
            reason += f" (path limit exceeded: {max_paths})"
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            initial_paths=initial_paths,
            reason=reason,
        )

    tracked_result = _git(root, ["ls-files", "--cached", "-z"], output_limit=max_paths * 4096)
    tracked_paths, tracked_error, tracked_overflow = _git_paths(
        tracked_result, max_paths=max_paths
    )
    if tracked_error or tracked_overflow:
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            tracked_paths=tracked_paths,
            reason=tracked_error or f"tracked path limit exceeded: {max_paths}",
        )
    object_id_bytes, object_format_error = _object_id_bytes(root)
    if object_format_error:
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            tracked_paths=tracked_paths,
            reason=object_format_error,
        )
    index_entries, index_error, index_overflow = _read_index_entries(
        root,
        object_id_bytes=object_id_bytes,
        max_paths=max_paths,
        max_bytes=max(snapshot_max_bytes, max_paths * 128),
    )
    if index_error or index_overflow:
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            tracked_paths=tracked_paths,
            index_entries=index_entries,
            object_id_bytes=object_id_bytes,
            reason=index_error or f"index path limit exceeded: {max_paths}",
        )

    snapshot, snapshot_omissions, snapshot_truncated = _snapshot_workspace(
        root,
        max_bytes=snapshot_max_bytes,
        max_paths=max_paths,
    )
    git_control, control_omissions, control_truncated = _control_snapshot(
        root,
        max_bytes=snapshot_max_bytes,
        max_paths=max_paths,
        allow_missing_index=not tracked_paths and not index_entries,
    )
    omissions = (*snapshot_omissions, *control_omissions)
    if omissions or snapshot_truncated or control_truncated:
        return Baseline(
            status="unavailable",
            revision=revision_text,
            git_boundary=git_boundary,
            tracked_paths=tracked_paths,
            index_entries=index_entries,
            object_id_bytes=object_id_bytes,
            snapshot=snapshot,
            git_control=git_control,
            snapshot_omissions=omissions,
            reason="baseline snapshot incomplete: " + "; ".join(omissions),
        )
    return Baseline(
        status="available",
        revision=revision_text,
        git_boundary=git_boundary,
        tracked_paths=tracked_paths,
        index_entries=index_entries,
        object_id_bytes=object_id_bytes,
        snapshot=snapshot,
        git_control=git_control,
    )


def _entry_map(
    entries: Sequence[tuple[str, str, int | None, str | None, str | None]],
) -> dict[str, tuple[str, str, int | None, str | None, str | None]]:
    result: dict[str, tuple[str, str, int | None, str | None, str | None]] = {}
    for entry in entries:
        if entry[0]:
            result[entry[0]] = entry
    return result


def _control_map(
    entries: Sequence[tuple[str, str, int | None, str | None]],
) -> dict[str, tuple[str, str, int | None, str | None]]:
    result: dict[str, tuple[str, str, int | None, str | None]] = {}
    for entry in entries:
        if entry[0]:
            result[entry[0]] = entry
    return result


def _bound_content(
    content: Sequence[str],
    *,
    max_bytes: int = DEFAULT_EVIDENCE_MAX_BYTES,
) -> tuple[tuple[str, ...], bool]:
    """Keep serialized evidence bounded even when many files change."""

    kept: list[str] = []
    used = 0
    truncated = False
    for item in content:
        size = len(item.encode("utf-8", errors="replace"))
        if used + size > max_bytes:
            truncated = True
            break
        kept.append(item)
        used += size
    if truncated:
        kept.append(
            f"EVIDENCE CONTENT TRUNCATED: limit={max_bytes} bytes; omitted remaining records"
        )
    return tuple(kept), truncated


def collect_evidence(
    workspace: Path | str,
    baseline: Baseline,
    *,
    required_paths: Sequence[str] = (),
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_paths: int = DEFAULT_MAX_PATHS,
) -> Evidence:
    """Compare runner snapshots and render bounded, non-secret evidence."""

    root = Path(workspace).resolve()
    required = tuple(required_paths)
    if max_bytes <= 0 or max_paths <= 0:
        return Evidence(
            status="unavailable",
            available=False,
            baseline_revision=baseline.revision,
            required_paths=required,
            reason="evidence limits must be positive",
        )

    snapshot_limit = max(DEFAULT_SNAPSHOT_MAX_BYTES, max_bytes)
    current_snapshot, snapshot_omissions, snapshot_truncated = _snapshot_workspace(
        root,
        max_bytes=snapshot_limit,
        max_paths=max_paths,
        protected_git_identity=(
            (int(baseline.git_boundary[1]), int(baseline.git_boundary[2]))
            if len(baseline.git_boundary) >= 3
            else None
        ),
    )
    required_content, required_omissions, required_truncated = _path_boundary_records(
        root, required, max_bytes
    )

    if not baseline.available:
        # An unavailable starting state is not a candidate trial.  Do not run
        # Git plumbing (including control/ref reads) against a possibly
        # malformed or candidate-controlled metadata path merely to render an
        # observation that cannot be scored.
        content: list[str] = []
        omissions = ["baseline"]
        current_map = _entry_map(current_snapshot)
        for relative in sorted(current_map):
            rendered, readable, reason = _read_bounded(
                root, relative, max_bytes, label="UNTRACKED"
            )
            content.append(rendered)
            if not readable:
                omissions.append(f"{relative}: {reason}")
        content.extend(required_content)
        omissions.extend((*snapshot_omissions, *required_omissions))
        bounded_content, content_truncated = _bound_content(content)
        if content_truncated:
            omissions.append("evidence content budget exceeded")
        return Evidence(
            status="unavailable",
            available=False,
            baseline_revision=baseline.revision,
            required_paths=required,
            current_untracked_paths=tuple(sorted(current_map)),
            untracked_paths=tuple(sorted(current_map)),
            content=bounded_content,
            omissions=tuple(omissions),
            truncated=(
                snapshot_truncated
                or required_truncated
                or content_truncated
            ),
            reason=baseline.reason or "baseline unavailable",
            outcome="unavailable",
        )

    # Validate the complete authorized .git boundary before any operation that
    # could dereference it.  In particular, do not let _control_snapshot or
    # rev-parse inspect a redirected repository and only report the redirect
    # afterwards.
    baseline_control = _control_map(baseline.git_control)
    baseline_index_control = baseline_control.get(".git/index")
    empty_initial_repository = (
        not baseline.tracked_paths
        and not baseline.index_entries
        and baseline_index_control is not None
        and baseline_index_control[1] == "missing"
    )
    git_boundary_error = _validate_git_boundary(
        root,
        baseline.git_boundary,
        allow_missing_index=empty_initial_repository,
    )
    if git_boundary_error:
        return Evidence(
            status="unavailable",
            available=False,
            baseline_revision=baseline.revision,
            required_paths=required,
            content=tuple(required_content),
            omissions=(git_boundary_error, *required_omissions, *snapshot_omissions),
            truncated=(snapshot_truncated or required_truncated),
            reason=git_boundary_error,
            outcome="unavailable",
        )

    current_control, control_omissions, control_truncated = _control_snapshot(
        root,
        max_bytes=snapshot_limit,
        max_paths=max_paths,
        allow_missing_index=empty_initial_repository,
    )
    errors: list[str] = []

    # Control snapshots are runner-owned, non-following observations. If
    # their traversal is incomplete, stop before Git can interpret a
    # candidate-controlled metadata path.
    git_plumbing_available = (
        not git_boundary_error and not control_omissions and not control_truncated
    )
    final_revision: str | None = None
    final_index_entries: tuple[tuple[str, str, int, int, int], ...] = ()
    if git_plumbing_available:
        final = _git(root, ["rev-parse", "HEAD"])
        final_error = _error(final)
        final_revision = _decode(final.stdout).strip() if not final_error else None
        if final_error:
            errors.append(f"final revision: {final_error}")
        elif not final_revision:
            errors.append("final revision was empty")
        if final_revision:
            final_index_entries, index_error, index_overflow = _read_index_entries(
                root,
                object_id_bytes=baseline.object_id_bytes,
                max_paths=max_paths,
                max_bytes=max(DEFAULT_SNAPSHOT_MAX_BYTES, max_bytes, max_paths * 128),
            )
            if index_error:
                errors.append(f"final index: {index_error}")
            if index_overflow:
                errors.append(f"final index path limit exceeded: {max_paths}")
    errors.extend(snapshot_omissions)
    errors.extend(control_omissions)
    errors.extend(required_omissions)
    truncated = snapshot_truncated or control_truncated or required_truncated

    baseline_map = _entry_map(baseline.snapshot)
    current_map = _entry_map(current_snapshot)
    all_paths = sorted(set(baseline_map) | set(current_map))
    changed_paths = tuple(
        path for path in all_paths if baseline_map.get(path) != current_map.get(path)
    )
    tracked_set = set(baseline.tracked_paths)
    worktree_paths = tuple(path for path in changed_paths if path in tracked_set)
    current_control_map = _control_map(current_control)
    # The index file contains both semantic entries and Git's mutable stat
    # cache.  Compare all other runner-owned control paths here; semantic index
    # changes are determined from parsed entries below.
    git_metadata_changed = {
        path: value for path, value in baseline_control.items() if path != ".git/index"
    } != {
        path: value for path, value in current_control_map.items() if path != ".git/index"
    }
    def index_map(
        entries: Sequence[tuple[str, str, int, int, int]],
    ) -> dict[str, tuple[tuple[str, int, int, int], ...]]:
        grouped: dict[str, list[tuple[str, int, int, int]]] = {}
        for path, oid, mode, stage, flags in entries:
            grouped.setdefault(path, []).append((oid, mode, stage, flags))
        return {
            path: tuple(sorted(values))
            for path, values in grouped.items()
        }

    baseline_index_map = index_map(baseline.index_entries)
    final_index_map = index_map(final_index_entries)
    index_paths = tuple(
        sorted(
            path
            for path in set(baseline_index_map) | set(final_index_map)
            if baseline_index_map.get(path) != final_index_map.get(path)
        )
    )
    index_changed = bool(index_paths)
    head_changed = bool(final_revision and baseline.revision and final_revision != baseline.revision)
    committed_entries: tuple[tuple[str, str | None], ...] = ()
    if head_changed and git_plumbing_available and final_revision and baseline.revision:
        committed_entries, committed_error, committed_overflow = _committed_entries(
            root,
            baseline.revision,
            final_revision,
            max_paths=max_paths,
            max_bytes=max(DEFAULT_SNAPSHOT_MAX_BYTES, max_bytes, max_paths * 256),
        )
        if committed_error:
            errors.append(f"committed diff: {committed_error}")
        if committed_overflow:
            truncated = True
    committed_paths = tuple(path for path, _ in committed_entries)
    if index_changed and not index_paths:
        # Exact index path attribution is intentionally not delegated to the
        # candidate-controlled index. The clean baseline inventory is the
        # trusted upper bound, so a changed index remains observable.
        index_paths = tuple(baseline.tracked_paths)
    committed_set = set(committed_paths)
    final_index_set = set(final_index_map)
    baseline_untracked_paths = tuple(
        sorted(path for path in baseline_map if path not in tracked_set)
    )
    current_untracked_paths = tuple(
        sorted(path for path in current_map if path not in final_index_set)
    )
    # This is a baseline-relative change channel, not an inventory. An
    # ignored file that predated the candidate therefore does not count as a
    # new read-only mutation merely because Git does not track it.
    untracked_paths = tuple(
        sorted(
            path
            for path in changed_paths
            if path not in tracked_set
            and path not in committed_set
            and path not in final_index_set
        )
    )
    tracked_paths = tuple(sorted(set(worktree_paths) | set(index_paths) | set(committed_paths)))

    content: list[str] = []
    required_set = set(required)
    auxiliary_binary_paths: set[str] = set()
    if changed_paths:
        content.append(
            "GIT DIFF AGAINST BASELINE (runner-owned filesystem snapshot):"
        )
    for relative in tuple(sorted(set(changed_paths) | set(untracked_paths))):
        if relative not in current_map:
            content.append(f"CHANGED PATH {relative}: missing from final workspace")
            continue
        rendered, readable, reason = _read_bounded(root, relative, max_bytes, label="CHANGED")
        # Untracked binary runtime products (for example Python's ignored
        # __pycache__ bytecode) are auxiliary unless the task explicitly asks
        # for that path.  Keep a bounded identity record, but do not make a
        # successful read-only candidate unavailable or dirty merely because
        # its interpreter wrote a cache file.
        if (
            reason == "binary"
            and relative not in tracked_set
            and relative not in required_set
            and _is_auxiliary_binary(relative)
        ):
            entry = current_map.get(relative)
            if entry is not None and entry[1] == "file" and entry[3] is not None:
                rendered = (
                    f"CHANGED FILE {relative}: binary content omitted "
                    f"(size={entry[2]}, sha256={entry[3]})"
                )
                readable = True
                reason = None
                auxiliary_binary_paths.add(relative)
        content.append(rendered)
        if not readable:
            errors.append(f"{relative}: {reason}")
            truncated = truncated or reason in {"truncated", "binary"}
    index_content_added = False
    for relative, oid, *_ in final_index_entries:
        if relative not in index_paths:
            continue
        if not index_content_added:
            content.append(
                "GIT INDEX DIFF AGAINST BASELINE (runner-owned index plumbing):"
            )
            index_content_added = True
        rendered, readable, reason = _index_blob(root, relative, oid, max_bytes)
        content.append(rendered)
        if not readable:
            errors.append(f"index {relative}: {reason}")
            truncated = truncated or reason in {"truncated", "binary"}
    if committed_entries:
        content.append(
            "GIT COMMITTED DIFF AGAINST BASELINE (runner-owned Git object plumbing):"
        )
    for relative, oid in committed_entries:
        if oid is None:
            content.append(f"COMMITTED FILE {relative}: deleted in final revision")
            continue
        rendered, readable, reason = _object_blob(
            root,
            relative,
            oid,
            max_bytes,
            label="COMMITTED",
        )
        content.append(rendered)
        if not readable:
            errors.append(f"committed {relative}: {reason}")
            truncated = truncated or reason in {"truncated", "binary"}
    content.extend(required_content)

    if git_metadata_changed:
        content.append("GIT CONTROL METADATA CHANGED: .git control snapshot differs")
    if index_changed:
        content.append("GIT INDEX CHANGED: semantic index entries differ from baseline")
    if head_changed:
        content.append("GIT HEAD CHANGED: final revision differs from baseline")

    bounded_content, content_truncated = _bound_content(content)
    truncated = truncated or content_truncated
    unavailable = bool(errors) or truncated
    untracked_paths = tuple(
        path for path in untracked_paths if path not in auxiliary_binary_paths
    )
    semantic_changed_paths = tuple(
        path for path in changed_paths if path not in auxiliary_binary_paths
    )
    has_changes = bool(
        semantic_changed_paths or index_changed or head_changed or git_metadata_changed
    )
    return Evidence(
        status="unavailable" if unavailable else "available",
        available=not unavailable,
        baseline_revision=baseline.revision,
        final_revision=final_revision,
        tracked_worktree_paths=worktree_paths,
        tracked_index_paths=index_paths,
        tracked_paths=tracked_paths,
        committed_paths=committed_paths,
        baseline_untracked_paths=baseline_untracked_paths,
        current_untracked_paths=current_untracked_paths,
        untracked_paths=untracked_paths,
        required_paths=required,
        content=bounded_content,
        omissions=tuple(errors),
        truncated=truncated,
        index_changed=index_changed,
        git_metadata_changed=git_metadata_changed,
        has_changes=has_changes,
        outcome="unavailable" if unavailable else ("changed" if has_changes else "unchanged observed outcome"),
        reason="; ".join(errors) if errors else None,
    )
