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
import subprocess
import sys
import tempfile


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular, non-symlink file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_identity(workspace: Path, paths: list[str]) -> dict:
    result = {}
    for name in paths:
        path = Path(name)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise ValueError(f"source path must be bounded and relative: {name}")
        target = workspace / path
        if not target.resolve().is_relative_to(workspace):
            raise ValueError(f"source path escapes workspace: {name}")
        result[name] = digest(target)
    return result


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
    if not isinstance(profile, dict) or set(profile) != {"version", "source_paths", "steps"} or type(profile["version"]) is not int or profile["version"] != 1:
        raise ValueError("profile requires version=1, source_paths, steps")
    paths = profile["source_paths"]
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise ValueError("source_paths must name the files relevant to the claim")
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
    results = [{"id": s["id"], "phase": s["phase"], "status": "not-run"} for s in profile["steps"]]
    failed = False
    started = False
    def checked(step, cleanup=False):
        try:
            if not cleanup and source_identity(workspace, profile["source_paths"]) != before:
                raise ValueError("declared source changed before this check")
            result = execute(step, workspace)
            result["source_after"] = source_identity(workspace, profile["source_paths"])
            if result["source_after"] != before:
                result.update(status="failed", reason="declared source changed during this step")
            return result
        except (OSError, ValueError) as exc:
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
        unchanged = before == after
    except (OSError, ValueError) as exc:
        after = {"error": str(exc)}
        unchanged = False
    return {"version": 1, "workspace": str(workspace), "source_before": before,
            "source_after": after, "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
            "checks": results, "passed": unchanged and not failed and all(r["status"] == "accepted" for r in results)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if args.receipt.resolve().is_relative_to(workspace):
        raise ValueError("receipt must be outside the application checkout")
    # Reserve the receipt before any command effects; failed startup/checks
    # remain inspectable, and an existing receipt never causes a repeated run.
    with os.fdopen(os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        try:
            result = run(json.loads(args.profile.read_text()), workspace)
        except (OSError, ValueError) as exc:
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
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
