#!/usr/bin/env python3
"""Private, revisioned task checkpoints. Author state is not verification proof."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("save", "resume"))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--expect")
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if args.mode == "save":
        if args.input is None:
            raise ValueError("save requires --input")
        identity = save(args.state, workspace, json.loads(args.input.read_text()), args.expect)
        print(json.dumps({"sha256": identity}))
    else:
        value, identity = read(args.state)
        if value["workspace"] != source(workspace):
            raise ValueError("checkpoint belongs to another workspace")
        print(json.dumps({"sha256": identity, "checkpoint": value,
                          "evidence_status": "unverified; recheck current revision and capabilities"}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
