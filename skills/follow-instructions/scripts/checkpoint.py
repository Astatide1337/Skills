#!/usr/bin/env python3
"""Private, revisioned task checkpoints. Author state is not verification proof."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


def validate(task: dict) -> None:
    if not isinstance(task, dict) or set(task) != {"objective", "requirements", "decisions", "next_action", "blockers"}:
        raise ValueError("task requires objective, requirements, decisions, next_action, blockers")
    if not all(isinstance(task[k], str) and task[k].strip() for k in ("objective", "next_action")):
        raise ValueError("objective and next_action cannot be empty")
    for key in ("decisions", "blockers"):
        if not isinstance(task[key], list) or not all(isinstance(t, str) and t.strip() for t in task[key]):
            raise ValueError(f"{key} must be a list of nonempty text")
    requirements = task["requirements"]
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements cannot be empty")
    ids = set()
    for item in requirements:
        if not isinstance(item, dict) or set(item) != {"id", "description", "status"}:
            raise ValueError("requirement requires id, description, status")
        if not all(isinstance(item[k], str) and item[k].strip() for k in ("id", "description")) or item["id"] in ids:
            raise ValueError("requirement IDs must be nonempty and unique")
        ids.add(item["id"])
        if not isinstance(item["status"], str) or item["status"] not in {"pending", "reported-complete", "blocked"}:
            raise ValueError("requirement status is author state, not an accepted check")


def source(workspace: Path) -> dict:
    # Reuse the evaluator's contained collector in evaluations; this portable
    # record only binds to the explicit workspace identity, not its contents.
    stat = workspace.stat()
    return {"path": str(workspace), "device": stat.st_dev, "inode": stat.st_ino}


def read(path: Path) -> tuple[dict, str]:
    if path.is_symlink():
        raise ValueError("checkpoint must not be a symlink")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"version", "sequence", "workspace", "task"} or type(value["version"]) is not int or value["version"] != 1 or type(value["sequence"]) is not int or value["sequence"] < 1:
        raise ValueError("unsupported checkpoint")
    validate(value["task"])
    return value, hashlib.sha256(raw).hexdigest()


def save(path: Path, workspace: Path, task: dict, expected: str | None) -> str:
    validate(task)
    if path.is_symlink():
        raise ValueError("checkpoint must not be a symlink")
    lock = path.with_name(path.name + ".lock")
    with os.fdopen(os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sequence = 1
        if path.exists():
            previous, identity = read(path)
            if expected != identity:
                raise ValueError("checkpoint changed; reread before updating")
            if previous["workspace"] != source(workspace):
                raise ValueError("checkpoint belongs to another workspace")
            old = previous["task"]
            if task["objective"] != old["objective"] or {(r["id"], r["description"]) for r in task["requirements"]} != {(r["id"], r["description"]) for r in old["requirements"]}:
                raise ValueError("update cannot discard or replace the objective/requirements; start a new checkpoint for an explicitly changed objective")
            if not set(old["decisions"]).issubset(task["decisions"]):
                raise ValueError("update cannot silently discard accepted decisions")
            sequence = previous["sequence"] + 1
        elif expected is not None:
            raise ValueError("cannot update a missing checkpoint")
        value = {"version": 1, "sequence": sequence, "workspace": source(workspace), "task": task}
        raw = (json.dumps(value, indent=2) + "\n").encode()
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".checkpoint-")
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return hashlib.sha256(raw).hexdigest()


def origin_pointer(origin: str, *, create: bool = False) -> Path:
    if not re.fullmatch(r"t3-thread://v2/[^/\s<>?#\x00-\x1f\x7f]+/[^/\s<>?#\x00-\x1f\x7f]+", origin):
        raise ValueError("expected the originating T3 thread link")
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    if not base.is_absolute():
        raise ValueError("XDG_STATE_HOME must be absolute")
    directory = base / "skills-parent-tasks"
    if create:
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("origin directory must be private and owned by this user")
    return directory / hashlib.sha256(origin.encode()).hexdigest()


def bind(origin: str, path: Path, previous: Path | None) -> None:
    pointer = origin_pointer(origin, create=True)
    with os.fdopen(os.open(pointer.with_suffix(".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600), "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = pointer.readlink() if pointer.is_symlink() else None
        if current == path:
            return
        if current != previous or pointer.exists() and current is None:
            raise ValueError("this origin already has a different checkpoint; use its previous path for an explicit replacement")
        # Keep readers on one complete pointer, including during explicit replacement.
        with tempfile.TemporaryDirectory(dir=pointer.parent) as scratch:
            new = Path(scratch) / "pointer"
            new.symlink_to(path)
            os.replace(new, pointer)
        directory = os.open(pointer.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("save", "resume", "bind", "check"))
    parser.add_argument("--state", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--origin", help="originating T3 thread link on the coordinator host")
    parser.add_argument("--previous", type=Path, help="previous checkpoint path when explicitly replacing a binding")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--expect")
    args = parser.parse_args()
    if args.previous is not None and args.mode != "bind":
        raise ValueError("--previous applies only to bind")
    if args.mode == "save":
        if args.input is None or args.state is None or args.workspace is None or args.origin is not None:
            raise ValueError("save requires --input, --state and --workspace")
        workspace = args.workspace.resolve(strict=True)
        identity = save(args.state, workspace, json.loads(args.input.read_text()), args.expect)
        print(json.dumps({"sha256": identity}))
    else:
        if args.mode == "bind":
            if not args.origin or args.state is None or args.workspace is None:
                raise ValueError("bind requires --origin, --state and --workspace")
            path = args.state
        elif args.origin and args.state is None:
            path = origin_pointer(args.origin).readlink()
            if not path.is_absolute():
                raise ValueError("origin points to an invalid checkpoint path")
        elif args.state is not None and args.workspace is not None and args.origin is None:
            path = args.state
        else:
            raise ValueError("use --origin or both --state and --workspace")
        value, identity = read(path)
        recorded = value["workspace"]
        if not isinstance(recorded, dict) or not isinstance(recorded.get("path"), str):
            raise ValueError("invalid checkpoint workspace")
        workspace = (args.workspace or Path(recorded["path"])).resolve(strict=True)
        if value["workspace"] != source(workspace):
            raise ValueError("checkpoint belongs to another workspace")
        if args.mode == "bind":
            bind(args.origin, path.resolve(strict=True), args.previous.resolve() if args.previous else None)
        task = value["task"]
        pending = [r["id"] for r in task["requirements"] if r["status"] == "pending"]
        blocked = [r["id"] for r in task["requirements"] if r["status"] == "blocked"]
        print(json.dumps({"sha256": identity, "state": str(path.absolute()), "checkpoint": value,
                          "pending": pending, "blocked": blocked,
                          "evidence_status": "unverified; recheck current revision and capabilities"}))
        if args.mode == "check" and (pending or blocked or task["blockers"]):
            return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
