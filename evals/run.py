"""Run each case autonomously in a fresh container and save what happened.

    python evals/run.py --token-file F --out DIR --arm none --arm current=HEAD [--case ID ...]

An arm is `none` (no skills or global instructions) or `NAME=GIT_REF` (the
catalog and global instructions at that ref). Results use the agentskills.io
layout: DIR/<case>/<arm>/run-<n>/{trace-*.jsonl, final.md, diff.patch, checks.json, timing.json}.
Only the case's `repo/` enters the container before the run; the brief arrives
as the user's message and hidden `checks/` are copied in after the agent stops.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases"
IMAGE = "skills-autonomous-eval"
HOME = "/home/node"


def sh(
    *args: str, check: bool = True, timeout: int = 120
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=check
    )


def build_image() -> None:
    subprocess.run(
        ["docker", "build", "-q", "-t", IMAGE, str(ROOT / "evals")],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def load_case(case_dir: Path) -> dict:
    case = yaml.safe_load((case_dir / "case.yaml").read_text())
    case["id"] = case_dir.name
    case["dir"] = case_dir
    return case


def export_arm(ref: str, dest: Path) -> None:
    """Materialize skills/ and global instructions from a git ref."""
    archive = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            ref,
            "skills",
            "global-instructions/AGENTS.md",
        ],
        check=True,
        capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def run_one(case: dict, arm: str, catalog: Path | None, n: int, args) -> None:
    out = args.out / case["id"] / arm / f"run-{n}"
    if (out / "timing.json").exists():
        return  # finished earlier; rerunning would overwrite evidence
    out.mkdir(parents=True, exist_ok=True)
    name = f"skills-eval-{uuid.uuid4().hex[:10]}"
    project = f"{HOME}/{case['project']}"
    exec_ = ["docker", "exec", "-w", project, name]
    sh(
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-e",
        "CLAUDE_CODE_OAUTH_TOKEN",
        IMAGE,
        "sleep",
        "infinity",
    )
    try:
        sh("docker", "cp", f"{case['dir']}/repo/.", f"{name}:{project}")
        if catalog is not None:
            sh("docker", "exec", name, "mkdir", "-p", f"{HOME}/.claude")
            sh("docker", "cp", f"{catalog}/skills", f"{name}:{HOME}/.claude/skills")
            sh(
                "docker",
                "cp",
                f"{catalog}/global-instructions/AGENTS.md",
                f"{name}:{HOME}/.claude/CLAUDE.md",
            )
        sh("docker", "exec", "-u", "root", name, "chown", "-R", "node:node", HOME)
        setup = case.get("setup", "")
        sh(
            *exec_,
            "bash",
            "-c",
            f"{setup}\ngit init -q && git add -A && git commit -qm 'initial import'",
            timeout=300,
        )

        session, totals = (
            None,
            {
                "cost_usd": 0.0,
                "turns": 0,
                "duration_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
        messages = [case["brief"], *case.get("turns", [])]
        final = []
        for i, message in enumerate(messages):
            cmd = [
                "docker",
                "exec",
                "-i",
                "-w",
                project,
                name,
                "claude",
                "-p",
                "--model",
                args.model,
                "--output-format",
                "stream-json",
                "--verbose",
                "--dangerously-skip-permissions",
            ]
            if session:
                cmd += ["--resume", session]
            proc = subprocess.run(
                cmd,
                input=message,
                capture_output=True,
                text=True,
                timeout=args.turn_timeout,
                check=False,
            )
            (out / f"trace-{i}.jsonl").write_text(proc.stdout)
            if proc.stderr.strip():
                (out / f"stderr-{i}.txt").write_text(proc.stderr)
            for line in proc.stdout.splitlines():
                event = json.loads(line) if line.startswith("{") else {}
                session = event.get("session_id", session)
                if event.get("type") == "result":
                    if event.get("api_error") or event.get("api_error_status"):
                        # Infrastructure (usage limit, outage), not agent behaviour:
                        # leave no timing.json so a rerun repeats this run.
                        raise RuntimeError(
                            f"API error in turn {i}: {event.get('result')}"
                        )
                    final.append(f"## Turn {i}\n\n{event.get('result', '')}")
                    totals["cost_usd"] += event.get("total_cost_usd") or 0
                    totals["turns"] += event.get("num_turns") or 0
                    totals["duration_ms"] += event.get("duration_ms") or 0
                    usage = event.get("usage") or {}
                    for key in ("input_tokens", "output_tokens"):
                        totals[key] += usage.get(key) or 0
                    totals["input_tokens"] += (
                        usage.get("cache_read_input_tokens") or 0
                    ) + (usage.get("cache_creation_input_tokens") or 0)
        (out / "final.md").write_text("\n\n".join(final))

        diff = sh(
            *exec_,
            "bash",
            "-c",
            "git add -A && git diff --cached $(git rev-list --max-parents=0 HEAD) "
            "&& git log --oneline $(git rev-list --max-parents=0 HEAD)..HEAD && git status --short",
        )
        (out / "diff.patch").write_text(diff.stdout)
        checks = []
        if (case["dir"] / "checks").is_dir():
            sh("docker", "cp", f"{case['dir']}/checks/.", f"{name}:{HOME}/.grader")
            sh(
                "docker",
                "exec",
                "-u",
                "root",
                name,
                "chown",
                "-R",
                "node:node",
                f"{HOME}/.grader",
            )
        for check in case.get("checks", []):
            result = sh(*exec_, "bash", "-c", check["run"], check=False, timeout=300)
            checks.append(
                {
                    "name": check["name"],
                    "passed": result.returncode == 0,
                    "output": (result.stdout + result.stderr)[-2000:],
                }
            )
        (out / "checks.json").write_text(json.dumps(checks, indent=2))
        totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]
        (out / "timing.json").write_text(json.dumps(totals, indent=2))
    finally:
        sh("docker", "rm", "-f", name, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        required=True,
        help="file holding a `claude setup-token` token",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--arm", action="append", required=True, help="none, or NAME=GIT_REF"
    )
    parser.add_argument("--case", action="append", help="case id (default: all)")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--turn-timeout", type=int, default=1800)
    args = parser.parse_args()

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = args.token_file.read_text().strip()
    build_image()
    cases = (
        [load_case(CASES / c) for c in args.case]
        if args.case
        else [
            load_case(d) for d in sorted(CASES.iterdir()) if (d / "case.yaml").is_file()
        ]
    )
    staging = Path(tempfile.mkdtemp(prefix="skills-eval-arms-"))
    try:
        arms: dict[str, Path | None] = {}
        for spec in args.arm:
            if spec == "none":
                arms["none"] = None
            else:
                arm, ref = spec.split("=", 1)
                (staging / arm).mkdir()
                export_arm(ref, staging / arm)
                arms[arm] = staging / arm
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(
            json.dumps(
                {
                    "model": args.model,
                    "arms": args.arm,
                    "samples": args.samples,
                    "cases": [c["id"] for c in cases],
                    "image": IMAGE,
                },
                indent=2,
            )
        )
        jobs = [
            (c, a, p, n)
            for c in cases
            for a, p in arms.items()
            for n in range(1, args.samples + 1)
        ]
        with ThreadPoolExecutor(args.jobs) as pool:
            futures = {pool.submit(run_one, *job, args): job for job in jobs}
            for future, (case, arm, _, n) in futures.items():
                try:
                    future.result()
                    print(f"done {case['id']}/{arm}/run-{n}", flush=True)
                except (
                    OSError,
                    subprocess.SubprocessError,
                    ValueError,
                ) as exc:  # a rerun resumes missing runs
                    print(f"FAILED {case['id']}/{arm}/run-{n}: {exc!r}", flush=True)
    finally:
        shutil.rmtree(staging)


if __name__ == "__main__":
    main()
