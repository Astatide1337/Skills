"""Runner-owned, bounded evidence for Inspect workspaces.

The candidate runs in a workspace it can mutate, including the workspace's
``.git`` metadata.  This module therefore captures a filesystem snapshot
before candidate execution and compares it with a second snapshot afterwards.
Git is used only for trusted pre-candidate inventory and a post-candidate
revision *identity*; post-candidate ``git diff`` is deliberately avoided
because repository filters, attributes, replacement refs, and index flags are
candidate-controlled inputs.  No evidence path is followed through a symlink,
hardlink, or filesystem mount boundary.
"""

from __future__ import annotations

import hashlib
import os
import re
import selectors
import stat
import struct
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


DEFAULT_MAX_BYTES = 20_000
DEFAULT_MAX_PATHS = 10_000
DEFAULT_SNAPSHOT_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_SNAPSHOT_TOTAL_BYTES = 64 * 1024 * 1024
DEFAULT_EVIDENCE_MAX_BYTES = 512 * 1024
_SENSITIVE_NAME_PARTS = (
    ".env",
    "secret",
    "credential",
    "password",
    "private",
    "token",
    ".pem",
    ".key",
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^(\s*(?:[A-Z0-9_.-]*(?:secret|token|password|private[_ -]?key|api[_ -]?key)"
    r"[A-Z0-9_.-]*)\s*[:=]\s*)([^\s#]+)(.*)$"
)
_PEM_BLOCK = re.compile(
    r"(?s)-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----"
)


@dataclass(frozen=True)
class Baseline:
    """Trusted state captured immediately before candidate execution."""

    status: str
    revision: str | None = None
    initial_paths: tuple[str, ...] = ()
    tracked_paths: tuple[str, ...] = ()
    index_entries: tuple[tuple[str, str], ...] = ()
    object_id_bytes: int = 20
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


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
        }
    )
    return env


def _git(
    workspace: Path,
    args: Sequence[str],
    *,
    output_limit: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run fixed Git argv with a finite timeout and bounded output."""

    command = ["git", *args]
    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=_git_env(),
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
    lowered = path.lower()
    return any(part in lowered for part in _SENSITIVE_NAME_PARTS)


def _redact_text(raw: str) -> str:
    """Redact common secret assignments before evidence reaches a grader."""

    raw = _PEM_BLOCK.sub("[REDACTED PRIVATE KEY]", raw)
    return _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]\3", raw)


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


def _control_snapshot(
    root: Path,
    *,
    max_bytes: int = DEFAULT_SNAPSHOT_MAX_BYTES,
    max_paths: int = DEFAULT_MAX_PATHS,
) -> tuple[tuple[tuple[str, str, int | None, str | None], ...], tuple[str, ...], bool]:
    """Hash Git control files without reading objects, logs, or attributes."""

    git_path = root / ".git"
    try:
        info = git_path.lstat()
    except OSError as exc:
        return (), (f".git: unavailable ({exc})",), False
    if stat.S_ISLNK(info.st_mode):
        return ((".git", "symlink", None, os.readlink(git_path)),), (), False
    if not stat.S_ISDIR(info.st_mode):
        opened = _safe_open(git_path, root.stat().st_dev)
        if opened is None:
            return ((".git", "other", None, "unsafe"),), (".git: unsafe gitfile",), False
        descriptor, opened_info = opened
        try:
            digest = _digest_descriptor(descriptor, opened_info.st_size, max_bytes)
        finally:
            os.close(descriptor)
        if digest is None:
            return ((".git", "file", opened_info.st_size, "omitted"),), (".git: gitfile omitted",), True
        return ((".git", "file", opened_info.st_size, digest),), (), False

    entries: list[tuple[str, str, int | None, str | None]] = []
    omissions: list[str] = []
    stack: list[tuple[Path, str]] = [(git_path, ".git")]
    root_dev = root.stat().st_dev
    while stack:
        directory, prefix = stack.pop()
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            omissions.append(f"{prefix}: directory enumeration failed ({exc})")
            continue
        for child in children:
            relative = f"{prefix}/{child.name}"
            # Object payloads and reflogs are not control inputs for the
            # outcome, and may be large. Refs, HEAD, index, and config are.
            if prefix == ".git" and child.name in {"objects", "logs"}:
                continue
            if len(entries) >= max_paths:
                omissions.append(f"Git control path limit exceeded ({max_paths})")
                return tuple(entries), tuple(omissions), True
            try:
                info = child.stat(follow_symlinks=False)
            except OSError as exc:
                omissions.append(f"{relative}: stat failed ({exc})")
                continue
            mode = info.st_mode
            if stat.S_ISLNK(mode):
                try:
                    target = os.readlink(child.path)
                except OSError as exc:
                    target = f"unreadable ({exc})"
                entries.append((relative, "symlink", None, target))
            elif stat.S_ISDIR(mode):
                if info.st_dev != root_dev:
                    omissions.append(f"{relative}: mount boundary not traversed")
                else:
                    stack.append((Path(child.path), relative))
            elif stat.S_ISREG(mode):
                opened = _safe_open(Path(child.path), root_dev)
                if opened is None:
                    entries.append((relative, "file", info.st_size, "omitted"))
                    omissions.append(f"{relative}: unsafe or hardlinked control file")
                    continue
                descriptor, opened_info = opened
                try:
                    digest = _digest_descriptor(descriptor, opened_info.st_size, max_bytes)
                finally:
                    os.close(descriptor)
                if digest is None:
                    digest = "omitted"
                    omissions.append(f"{relative}: control file exceeds snapshot limit")
                entries.append((relative, "file", opened_info.st_size, digest))
            else:
                entries.append((relative, "other", None, "unsupported"))
                omissions.append(f"{relative}: unsupported control file")
    entries.sort(key=lambda item: item[0])
    return tuple(entries), tuple(omissions), False


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


def _read_limited(path: Path, root_dev: int, max_bytes: int) -> tuple[bytes, str | None]:
    opened = _safe_open(path, root_dev)
    if opened is None:
        return b"", "file could not be safely opened"
    descriptor, info = opened
    try:
        if info.st_size > max_bytes:
            return b"", f"file exceeds limit {max_bytes}"
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > max_bytes:
            return raw[: max_bytes + 1], f"file exceeds limit {max_bytes}"
        return raw, None
    except OSError as exc:
        return b"", f"file could not be read ({exc})"
    finally:
        os.close(descriptor)


def _parse_index(
    raw: bytes,
    *,
    object_id_bytes: int,
    max_paths: int,
) -> tuple[tuple[tuple[str, str], ...], str | None, bool]:
    """Parse v2/v3 index identities without asking Git to interpret the index."""

    if len(raw) < 12 or raw[:4] != b"DIRC":
        return (), "invalid Git index header", False
    version, count = struct.unpack(">II", raw[4:12])
    if version not in {2, 3}:
        return (), f"unsupported Git index version {version}", False
    offset = 12
    records: list[tuple[str, str]] = []
    overflow = False
    for _ in range(count):
        entry_start = offset
        fixed = 62 + (object_id_bytes - 20)
        if offset + fixed > len(raw):
            return (), "truncated Git index entry", False
        flags_offset = offset + 60 + (object_id_bytes - 20)
        flags = struct.unpack(">H", raw[flags_offset : flags_offset + 2])[0]
        offset += fixed
        if flags & 0x4000:
            if offset + 2 > len(raw):
                return (), "truncated Git index extension flags", False
            offset += 2
        try:
            path_end = raw.index(b"\0", offset)
        except ValueError:
            return (), "unterminated Git index path", False
        path = _decode(raw[offset:path_end])
        oid_start = entry_start + 40
        oid = raw[oid_start : oid_start + object_id_bytes].hex()
        offset = path_end + 1
        while (offset - entry_start) % 8:
            offset += 1
        if not validate_relative_path(path):
            return (), f"invalid Git index path {path!r}", False
        if len(records) >= max_paths:
            overflow = True
            continue
        records.append((path, oid))
    return tuple(records), None, overflow


def _read_index_entries(
    root: Path,
    *,
    object_id_bytes: int,
    max_paths: int,
    max_bytes: int,
) -> tuple[tuple[tuple[str, str], ...], str | None, bool]:
    raw, read_error = _read_limited(root / ".git" / "index", root.stat().st_dev, max_bytes)
    if read_error:
        return (), read_error, False
    return _parse_index(
        raw,
        object_id_bytes=object_id_bytes,
        max_paths=max_paths,
    )


def _index_blob(
    root: Path,
    relative: str,
    oid: str,
    max_bytes: int,
) -> tuple[str, bool, str | None]:
    """Render a bounded index blob via plumbing that does not apply filters."""

    if not validate_relative_path(relative) or _sensitive(relative):
        reason = "path-boundary" if not validate_relative_path(relative) else "sensitive-omitted"
        return f"INDEX FILE {relative}: content omitted ({reason})", False, reason
    result = _git(root, ["cat-file", "blob", oid], output_limit=max_bytes)
    error = _error(result)
    if error:
        return f"INDEX FILE {relative}: unreadable ({error})", False, "unreadable"
    raw = result.stdout
    if len(raw) > max_bytes or "output truncated by evaluator" in _decode(result.stderr):
        return f"INDEX FILE {relative}: content truncated (limit={max_bytes})", False, "truncated"
    if b"\0" in raw:
        return f"INDEX FILE {relative}: binary content omitted (size={len(raw)})", False, "binary"
    return f"INDEX FILE {relative}:\n{_redact_text(_decode(raw))}", True, None


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
    revision = _git(root, ["rev-parse", "HEAD"])
    revision_error = _error(revision)
    if revision_error:
        return Baseline(status="unavailable", reason=revision_error)
    revision_text = _decode(revision.stdout).strip() or None
    if revision_text is None:
        return Baseline(status="unavailable", reason="baseline revision was empty")

    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    status_error = _error(status)
    if status_error:
        return Baseline(status="unavailable", revision=revision_text, reason=status_error)
    initial_paths, initial_overflow = _bounded_unique(_nul_paths(status.stdout), max_paths)
    if initial_paths or initial_overflow:
        reason = "initial workspace is dirty; clean disposable fixtures are required"
        if initial_overflow:
            reason += f" (path limit exceeded: {max_paths})"
        return Baseline(
            status="unavailable",
            revision=revision_text,
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
            tracked_paths=tracked_paths,
            reason=tracked_error or f"tracked path limit exceeded: {max_paths}",
        )
    object_id_bytes, object_format_error = _object_id_bytes(root)
    if object_format_error:
        return Baseline(
            status="unavailable",
            revision=revision_text,
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
    )
    omissions = (*snapshot_omissions, *control_omissions)
    if omissions or snapshot_truncated or control_truncated:
        return Baseline(
            status="unavailable",
            revision=revision_text,
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
        tracked_paths=tracked_paths,
        index_entries=index_entries,
        object_id_bytes=object_id_bytes,
        snapshot=snapshot,
        git_control=git_control,
    )


def _entry_map(
    entries: Sequence[tuple[str, str, int | None, str | None, str | None]] | Sequence[Any],
) -> dict[str, tuple[Any, ...]]:
    result: dict[str, tuple[Any, ...]] = {}
    for entry in entries:
        if isinstance(entry, dict):
            path = str(entry.get("path", ""))
            value = (
                path,
                entry.get("kind"),
                entry.get("size"),
                entry.get("digest"),
                entry.get("target_or_note"),
            )
        else:
            values = tuple(entry)
            if not values:
                continue
            path = str(values[0])
            value = values
        if path:
            result[path] = value
    return result


def _control_map(entries: Sequence[Any]) -> dict[str, tuple[Any, ...]]:
    result: dict[str, tuple[Any, ...]] = {}
    for entry in entries:
        values = tuple(entry.values()) if isinstance(entry, dict) else tuple(entry)
        if values:
            result[str(values[0])] = values
    return result


def _index_digest(control: dict[str, tuple[Any, ...]]) -> Any:
    entry = control.get(".git/index")
    return entry[3] if entry and len(entry) > 3 else None


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
    )
    current_control, control_omissions, control_truncated = _control_snapshot(
        root,
        max_bytes=snapshot_limit,
        max_paths=max_paths,
    )
    required_content, required_omissions, required_truncated = _path_boundary_records(
        root, required, max_bytes
    )

    if not baseline.available:
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
        omissions.extend((*snapshot_omissions, *control_omissions, *required_omissions))
        bounded_content, content_truncated = _bound_content(content)
        if content_truncated:
            omissions.append("evidence content budget exceeded")
        return Evidence(
            status="unavailable",
            available=False,
            baseline_revision=baseline.revision,
            required_paths=required,
            untracked_paths=tuple(sorted(current_map)),
            content=bounded_content,
            omissions=tuple(omissions),
            truncated=(
                snapshot_truncated
                or control_truncated
                or required_truncated
                or content_truncated
            ),
            reason=baseline.reason or "baseline unavailable",
        )

    final = _git(root, ["rev-parse", "HEAD"])
    final_error = _error(final)
    final_revision = _decode(final.stdout).strip() if not final_error else None
    errors: list[str] = []
    if final_error:
        errors.append(f"final revision: {final_error}")
    elif not final_revision:
        errors.append("final revision was empty")
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
    untracked_paths = tuple(path for path in current_map if path not in tracked_set)
    baseline_control = _control_map(baseline.git_control)
    current_control_map = _control_map(current_control)
    git_metadata_changed = baseline_control != current_control_map
    baseline_index_map = dict(baseline.index_entries)
    final_index_map = dict(final_index_entries)
    index_paths = tuple(
        sorted(
            path
            for path in set(baseline_index_map) | set(final_index_map)
            if baseline_index_map.get(path) != final_index_map.get(path)
        )
    )
    index_changed = (
        _index_digest(baseline_control) != _index_digest(current_control_map)
        or bool(index_paths)
    )
    head_changed = bool(final_revision and baseline.revision and final_revision != baseline.revision)
    committed_paths = changed_paths if head_changed else ()
    if index_changed and not index_paths:
        # Exact index path attribution is intentionally not delegated to the
        # candidate-controlled index. The clean baseline inventory is the
        # trusted upper bound, so a changed index remains observable.
        index_paths = tuple(baseline.tracked_paths)
    tracked_paths = tuple(sorted(set(worktree_paths) | set(index_paths) | set(committed_paths)))
    has_changes = bool(changed_paths or index_changed or head_changed or git_metadata_changed)

    content: list[str] = []
    if changed_paths:
        content.append(
            "GIT DIFF AGAINST BASELINE (runner-owned filesystem snapshot):"
        )
    for relative in tuple(sorted(set(changed_paths) | set(untracked_paths))):
        if relative not in current_map:
            content.append(f"CHANGED PATH {relative}: missing from final workspace")
            continue
        rendered, readable, reason = _read_bounded(root, relative, max_bytes, label="CHANGED")
        content.append(rendered)
        if not readable:
            errors.append(f"{relative}: {reason}")
            truncated = truncated or reason in {"truncated", "binary"}
    index_content_added = False
    for relative, oid in final_index_entries:
        if relative not in index_paths:
            continue
        if relative in changed_paths:
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
    content.extend(required_content)

    if git_metadata_changed:
        content.append("GIT CONTROL METADATA CHANGED: .git control snapshot differs")
    if index_changed:
        content.append("GIT INDEX CHANGED: index digest differs from baseline")
    if head_changed:
        content.append("GIT HEAD CHANGED: final revision differs from baseline")

    bounded_content, content_truncated = _bound_content(content)
    truncated = truncated or content_truncated
    unavailable = bool(errors) or truncated
    return Evidence(
        status="unavailable" if unavailable else "available",
        available=not unavailable,
        baseline_revision=baseline.revision,
        final_revision=final_revision,
        tracked_worktree_paths=worktree_paths,
        tracked_index_paths=index_paths,
        tracked_paths=tracked_paths,
        committed_paths=committed_paths,
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


def evidence_record(value: Baseline | Evidence) -> dict[str, Any]:
    """Return a JSON-safe record for Inspect's state store."""

    return asdict(value)
