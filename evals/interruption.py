"""Runner-owned real subprocess interruption for Inspect's resume control.

No provider protocol: observe a fixture marker, retain the checkpoint digest,
and interrupt the owned process group. Expectations stay in Inspect.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def interrupt(command, marker: Path, checkpoint: Path, record: Path, stdin: bytes, timeout=180, absent: Path | None = None):
    if marker.exists() or record.exists():
        raise ValueError("interruption controls must be fresh")
    process = subprocess.Popen(command, stdin=subprocess.PIPE, start_new_session=True)
    try:
        process.stdin.write(stdin)
        process.stdin.close()
        deadline = time.monotonic() + timeout
        while not marker.is_file():
            if process.poll() is not None:
                raise RuntimeError("agent exited before interruption marker")
            if time.monotonic() >= deadline:
                raise TimeoutError("agent did not reach the declared interruption point")
            time.sleep(.05)
        if marker.is_symlink() or checkpoint.is_symlink():
            raise ValueError("interruption input must not be a symlink")
        raw = checkpoint.read_bytes()
        saved = json.loads(raw)
        if not saved.get("task", {}).get("objective"):
            raise ValueError("checkpoint has no active objective")
        task = saved["task"]
        if absent is not None:
            if absent.exists() or absent.is_symlink():
                raise ValueError("required output was produced before interruption")
            requirements = task.get("requirements")
            if not isinstance(requirements, list) or not requirements or any(r.get("status") != "pending" for r in requirements):
                raise ValueError("checkpoint must retain pending requirements before interruption")
        if process.poll() is not None:
            raise RuntimeError("agent exited before it could be interrupted")
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
        with record.open("x") as output:
            json.dump({"interrupted": True, "checkpoint_sha256": hashlib.sha256(raw).hexdigest(),
                       "task_before": task, "exit_code": process.returncode}, output)
        return 130
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--absent", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        sys.exit(interrupt(command, args.marker, args.checkpoint, args.record, sys.stdin.buffer.read(), absent=args.absent))
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(124)
