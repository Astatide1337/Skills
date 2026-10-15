#!/usr/bin/env python3
"""Prepare immutable-by-convention comparison inputs, without activating skills.

This is a local Git snapshot operation, not a sandbox, installer, evaluator or
model launcher. Its manifest detects drift, not maliciously forged evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile

ROOTS = ("skills", "scripts", "catalog.yaml", "global-instructions/AGENTS.md")
REQUIRED = ("skills/follow-instructions/SKILL.md", "scripts/install.sh",
            "catalog.yaml", "global-instructions/AGENTS.md")
MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 10000


class PreviewError(Exception):
    """A preparation or package-integrity failure with no implied acceptance."""


def git(repo: Path, *args: str) -> bytes:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects",
         "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
         "-C", str(repo), *args], env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=60, check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[-1500:]
        raise PreviewError(f"Git operation failed: {detail or result.returncode}")
    return result.stdout


def resolve_commit(repo: Path, ref: str) -> str:
    value = git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    return value.decode("ascii").strip()


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "\\" in name:
        raise PreviewError(f"Unsafe archive path: {name!r}")
    if not any(path == PurePosixPath(root) or
               path.is_relative_to(PurePosixPath(root)) for root in ROOTS):
        raise PreviewError(f"Unexpected snapshot path: {name!r}")
    return path


def snapshot(repo: Path, commit: str, destination: Path) -> None:
    # Use committed blobs directly: archive export-ignore/export-subst attributes
    # must not omit or rewrite a skill, example or policy in a comparison arm.
    records = git(repo, "ls-tree", "-r", "-z", "-l", "--full-tree", commit, "--", *ROOTS)
    entries = []
    total = 0
    for record in records.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, sha, raw_size = metadata.split()
        name = os.fsdecode(raw_path)
        relative = safe_relative(name)
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise PreviewError(f"Snapshot rejects links and special files: {name}")
        size = int(raw_size)
        total += size
        if total > MAX_BYTES or len(entries) >= MAX_FILES:
            raise PreviewError("Snapshot exceeds the bounded file/size limit")
        entries.append((relative, mode, sha.decode("ascii"), size))
    names = {str(entry[0]) for entry in entries}
    for required in REQUIRED:
        if required not in names:
            raise PreviewError(f"Commit omitted required input: {required}")
    destination.mkdir()
    for relative, mode, sha, size in entries:
        data = git(repo, "cat-file", "blob", sha)
        if len(data) != size:
            raise PreviewError(f"Committed object size changed: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(data)
        target.chmod(0o755 if mode == b"100755" else 0o644)


def inventory(root: Path) -> dict[str, dict[str, object]]:
    if root.is_symlink() or not root.is_dir():
        raise PreviewError(f"Snapshot root is missing or linked: {root.name}")
    entries: dict[str, dict[str, object]] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise PreviewError(f"Linked or special snapshot entry: {path.relative_to(root)}")
        total += info.st_size
        if total > MAX_BYTES or len(entries) >= MAX_FILES:
            raise PreviewError("Snapshot exceeds the bounded file/size limit")
        data = path.read_bytes()
        entries[path.relative_to(root).as_posix()] = {
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "executable": bool(info.st_mode & 0o111),
        }
    return entries


def prepare(repo: Path, candidate: str, baseline: str, output: Path) -> dict:
    repo = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    # This operation snapshots commits, never an ambiguous dirty candidate.
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *ROOTS):
        raise PreviewError("Relevant source files are dirty. Commit the intended preview first")
    candidate_sha, baseline_sha = resolve_commit(repo, candidate), resolve_commit(repo, baseline)
    output = output.expanduser().absolute()
    if output.name in {"", ".", ".."}:
        raise PreviewError("Choose a named fresh output directory")
    parent = output.parent.resolve(strict=True)
    output = parent / output.name
    if os.path.lexists(output):
        raise PreviewError("Output already exists. It will not be replaced or merged")
    blocked = [repo, *(Path.home() / name for name in
                      (".agents", ".codex", ".claude", ".config/opencode"))]
    if any(output.is_relative_to(path.resolve()) for path in blocked):
        raise PreviewError("Output must be outside the source repository and installed-agent directories")
    manifest = {"version": 1, "kind": "skills-preview-inputs", "arms": {}}
    with tempfile.TemporaryDirectory(prefix=".skills-preview-", dir=parent) as temp:
        stage = Path(temp)
        for arm, commit in (("baseline", baseline_sha), ("candidate", candidate_sha)):
            snapshot(repo, commit, stage / arm)
            manifest["arms"][arm] = {"commit": commit, "files": inventory(stage / arm)}
        (stage / "preview.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (stage / "TRIAL.md").write_text(
            "# Prepared Skills comparison\n\n"
            "These are frozen source inputs, not activated skills or an execution sandbox.\n"
            "No model, application, installer, login, network operation or global change ran.\n\n"
            f"Baseline commit: `{baseline_sha}`\n\nCandidate commit: `{candidate_sha}`\n\n"
            "Select only one arm per fresh session. Use its `skills/follow-instructions/SKILL.md`\n"
            "with the same actual user policy in both arms, preserving application instructions.\n"
            "Use the existing runtime to enforce permissions and isolate acceptance. Do not mix\n"
            "same-named installed baseline skills into a candidate run. If routing isolation is\n"
            "not established, report an exploratory trial rather than a controlled comparison.\n\n"
            "Start with one actual requested application task and an explicit budget. Keep the\n"
            "same application inputs, model/settings, tools and acceptance in both arms.\n"
            "Retain ordinary cases, a valid alternative and a genuinely new transfer case.\n"
            "See the preview branch's PREVIEW.md and the existing evaluation procedure for\n"
            "exact supported native-evaluation commands and Linktree prerequisites.\n\n"
            "Recheck this package before a trial with `prepare-preview.py verify PATH`.\n"
            "Checksums detect drift relative to this manifest, not hostile edits to both.\n"
            "Rollback means stop the candidate session and select the baseline. No installed\n"
            "configuration needs restoration because preparation did not change it.\n",
            encoding="utf-8",
        )
        # Reserve the final name only after all inputs are successfully prepared.
        output.mkdir(mode=0o700)
        try:
            for path in stage.iterdir():
                path.rename(output / path.name)
        except BaseException:
            # Never delete an output another process might have touched.
            print(f"Incomplete output retained at {output}. Do not use it without verify.", file=sys.stderr)
            raise
    return {"status": "prepared", "output": str(output),
            "baseline": baseline_sha, "candidate": candidate_sha,
            "activated": False, "runtime_verified": False}


def verify(output: Path) -> dict:
    output = output.expanduser().absolute()
    if output.is_symlink() or not output.is_dir():
        raise PreviewError("Preview directory is missing or linked")
    path = output / "preview.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise PreviewError("Preview manifest is missing, linked or too large")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or \
       manifest.get("kind") != "skills-preview-inputs":
        raise PreviewError("Unsupported preview manifest")
    arms = manifest.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"baseline", "candidate"}:
        raise PreviewError("Manifest must contain exactly baseline and candidate")
    for arm, expected in arms.items():
        if not isinstance(expected, dict) or not isinstance(expected.get("commit"), str):
            raise PreviewError(f"Invalid {arm} identity")
        commit = expected["commit"]
        if len(commit) not in (40, 64) or any(c not in "0123456789abcdef" for c in commit):
            raise PreviewError(f"Invalid {arm} commit")
        actual = inventory(output / arm)
        if not actual or actual != expected.get("files"):
            raise PreviewError(f"{arm} content or executable modes differ from the manifest")
    return {"status": "matches-manifest", "output": str(output),
            "activated": False, "runtime_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare", help="Snapshot committed baseline and candidate into a fresh directory")
    create.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    create.add_argument("--candidate", default="HEAD")
    create.add_argument("--baseline", required=True, help="Explicit accepted source ref, not an inferred installed baseline")
    create.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify", help="Detect package drift, not verify engineering outcomes")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result = (verify(args.directory) if args.command == "verify" else
                  prepare(args.repo, args.candidate, args.baseline, args.output))
    except (PreviewError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc),
                          "activated": False, "runtime_verified": False}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Preparation interrupted. No installed skills were changed.", file=sys.stderr)
        return 130
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
