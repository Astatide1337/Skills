#!/usr/bin/env python3
"""Read-only JSON Lines inventory of registered Git worktrees.

Unknown observations are objects {"unknown": "reason"}, including a detached
branch or existence that cannot be checked. exists is otherwise a boolean
indicating whether the registered path is a directory. Registration metadata is
separate from directory observations; primary and locked describe the
registration (Git lists the primary worktree first).
tracked_changes counts status entries, once per renamed or unmerged path;
untracked_paths and ignored_by_top_level count paths reported by Git (-uall),
not bytes. Known ignored entries use {"counts": {top_level: count}}; unknown
observations use {"unknown": "reason"}.

commits_not_in_local_remote_refs uses rev-list HEAD --not --remotes: it is
relative only to remote-tracking refs present locally at the last fetch, never
live remote state. With no local remote refs the count is unknown. These are non-atomic observations, not an authoritative inventory.
No fetch, cleanup, index refresh or other repository writes are performed.
"""

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def git(repo, *args, reject_stderr=False):
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
    ):
        env.pop(key, None)
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", os.fspath(repo), *args],
        env=env,
        capture_output=True,
        check=True,
    )
    if reject_stderr and result.stderr:
        raise ValueError("incomplete Git observation: " + os.fsdecode(result.stderr).strip())
    return result.stdout


def unknown(reason):
    return {"unknown": reason}


def registrations(repo):
    records = []
    record = {}
    for field in git(repo, "worktree", "list", "--porcelain", "-z").split(b"\0"):
        if not field:
            if record:
                records.append(record)
                record = {}
            continue
        key, _, value = field.partition(b" ")
        record[os.fsdecode(key)] = os.fsdecode(value)
    return records


def status_counts(data):
    tracked = untracked = 0
    ignored = {}
    entries = iter(data.split(b"\0"))
    for entry in entries:
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code == b"??":
            untracked += 1
        elif code == b"!!":
            top = os.fsdecode(path.split(b"/", 1)[0])
            ignored[top] = ignored.get(top, 0) + 1
        else:
            tracked += 1
            if b"R" in code or b"C" in code:
                next(entries)  # -z rename/copy source is a separate NUL field.
    return tracked, untracked, {"counts": ignored}


def audit(repo):
    common = Path(os.fsdecode(git(repo, "rev-parse", "--git-common-dir")[:-1]))
    if not common.is_absolute():
        common = Path(repo) / common
    common = common.resolve()
    for index, registration in enumerate(registrations(repo)):
        path = Path(registration["worktree"])
        try:
            exists = stat.S_ISDIR(path.stat().st_mode)
            reason = "directory not observable" if exists else "path is not a directory"
        except (FileNotFoundError, NotADirectoryError):
            exists = False
            reason = "directory missing"
        except OSError as exc:
            reason = f"directory existence not observable: {exc}"
            exists = unknown(reason)
        row = {
            "path": str(path),
            "exists": exists,
            "primary": index == 0,
            "locked": "locked" in registration,
            "registration": registration,
        }
        if "locked" in registration:
            row["lock_reason"] = registration["locked"]
        fields = (
            "branch",
            "head",
            "tracked_changes",
            "untracked_paths",
            "ignored_by_top_level",
            "commits_not_in_local_remote_refs",
        )
        row.update({key: unknown(reason) for key in fields})
        if exists is True:
            try:
                top = Path(os.fsdecode(git(path, "rev-parse", "--show-toplevel")[:-1]))
                actual_common = Path(
                    os.fsdecode(git(path, "rev-parse", "--git-common-dir")[:-1])
                )
                if not actual_common.is_absolute():
                    actual_common = path / actual_common
                if top.resolve() != path.resolve() or actual_common.resolve() != common:
                    raise ValueError("directory is not the registered repository")
                try:
                    branch = git(path, "symbolic-ref", "--quiet", "HEAD")[:-1]
                    row["branch"] = os.fsdecode(branch.removeprefix(b"refs/heads/"))
                except subprocess.CalledProcessError as exc:
                    if exc.returncode != 1:
                        raise
                    row["branch"] = unknown("detached HEAD")
                row["head"] = git(path, "rev-parse", "--verify", "HEAD")[:-1].decode(
                    "ascii"
                )
                counts = status_counts(
                    git(
                        path,
                        "status",
                        "--porcelain=v1",
                        "-z",
                        "--untracked-files=all",
                        "--ignored=traditional",
                        reject_stderr=True,
                    )
                )
                row.update(zip(fields[2:5], counts))
                if git(path, "for-each-ref", "--format=%(refname)", "refs/remotes"):
                    row[fields[5]] = int(
                        git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
                    )
                else:
                    row[fields[5]] = unknown("no local remote-tracking refs")
            except (OSError, subprocess.CalledProcessError, ValueError) as exc:
                # Preserve earlier successful observations, explain remaining unknowns.
                for key in fields:
                    if row[key] == unknown(reason):
                        row[key] = unknown(f"observation failed: {exc}")
        yield row


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="repository path (default: current directory)",
    )
    args = parser.parse_args()
    try:
        for row in audit(args.repo.absolute()):
            print(json.dumps(row, ensure_ascii=True))
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"workspace audit: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
