#!/usr/bin/env python3
"""Plan pinned Harbor comparisons without copying auth or executing model calls."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals/benchmarks.json"


def load_manifest():
    return json.loads(MANIFEST.read_text())


def command():
    runner = load_manifest()["runner"]
    return [
        "env",
        "-u",
        "CODEX_AUTH_JSON_PATH",
        "-u",
        "CODEX_FORCE_AUTH_JSON",
        "uvx",
        "--from",
        f"harbor=={runner['version']}",
        "harbor",
    ]


def digest(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Symlinks are not accepted: {path}")
    files = sorted(path.rglob("*")) if path.is_dir() else [path]
    hashes = {}
    for file in files:
        if file.is_symlink():
            raise ValueError(f"Symlinks are not accepted: {file}")
        if file.is_file():
            name = file.relative_to(path).as_posix() if path.is_dir() else file.name
            hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest()
    return hashes


def output_path(path):
    target = Path(path).expanduser().resolve()
    allowed = [(ROOT / "evals/results").resolve(), (Path.home() / ".cache").resolve()]
    if not any(target != base and target.is_relative_to(base) for base in allowed):
        raise ValueError(
            "Output must be a new directory under evals/results or ~/.cache"
        )
    if target.exists():
        raise ValueError(
            "Output already exists; use a new directory to preserve prior evidence"
        )
    return target


def plan(args):
    manifest = load_manifest()
    dataset = next((d for d in manifest["datasets"] if d["name"] == args.dataset), None)
    if dataset is None:
        raise ValueError("Unknown dataset")
    names = [task["name"] for task in dataset["tasks"]]
    if not args.task or any(task not in names for task in args.task):
        raise ValueError(
            "Select explicit task names from list; no unbounded dataset runs"
        )
    if len(set(args.task)) != len(args.task) or len(args.task) > 4:
        raise ValueError("Choose at most four unique tasks")
    if not 1 <= args.attempts <= 5:
        raise ValueError("Attempts must be between 1 and 5")
    source_paths = [Path(args.old_skills).resolve(), Path(args.new_skills).resolve()]
    for source in source_paths:
        if not source.is_dir() or not list(source.glob("*/SKILL.md")):
            raise ValueError(f"Not a catalog directory: {source}")
    global_source = Path(args.globals).resolve()
    globals_hash = digest(global_source)
    skill_hashes = [digest(source) for source in source_paths]
    target = output_path(args.output)
    if any(target.is_relative_to(source) for source in source_paths):
        raise ValueError("Output cannot be inside a catalog")
    target.mkdir(parents=True)
    globals_copy = target / "global-instructions.txt"
    shutil.copyfile(global_source, globals_copy)
    if hashlib.sha256(globals_copy.read_bytes()).hexdigest() != next(
        iter(globals_hash.values())
    ):
        raise ValueError(
            "Global instructions changed during snapshot; discard plan and retry"
        )
    registry = dict(dataset)
    registry["tasks"] = [t for t in dataset["tasks"] if t["name"] in args.task]
    registry_path = target / "registry.json"
    registry_path.write_text(json.dumps([registry], indent=2) + "\n")
    runs = []
    for index, arm in enumerate(["old", "new"]):
        snapshot = target / arm / "skills"
        shutil.copytree(source_paths[index], snapshot)
        if digest(snapshot) != skill_hashes[index]:
            raise ValueError("Catalog changed during snapshot; discard plan and retry")
        config = {
            "job_name": f"{arm}-catalog",
            "jobs_dir": str(target / "jobs"),
            "n_attempts": args.attempts,
            "n_concurrent_trials": 1,
            "environment": {"type": "docker", "delete": True},
            "agents": [
                {
                    "name": "codex",
                    "model_name": args.model,
                    "skills": [
                        str(p)
                        for p in sorted(snapshot.iterdir())
                        if (p / "SKILL.md").is_file()
                    ],
                    "override_timeout_sec": args.timeout,
                    "kwargs": {
                        "version": manifest["codex_version"],
                        "reasoning_effort": args.effort,
                        "config": {"developer_instructions": globals_copy.read_text()},
                    },
                }
            ],
            "datasets": [
                {
                    "name": dataset["name"],
                    "version": dataset["version"],
                    "registry_path": str(registry_path),
                    "task_names": args.task,
                }
            ],
        }
        config_path = target / f"{arm}.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        runs.append(
            {
                "arm": arm,
                "argv": command() + ["run", "--config", str(config_path)],
                "validate_argv": command()
                + ["run", "--config", str(config_path), "--print-config"],
                "catalog_hashes": skill_hashes[index],
            }
        )
    result = {
        "status": "planned-not-executed",
        "manifest": manifest["runner"],
        "model": args.model,
        "effort": args.effort,
        "global_hashes": globals_hash,
        "candidate_calls": len(args.task) * args.attempts * 2,
        "auth": "Explicit OPENAI_API_KEY environment only; no host auth.json copied.",
        "scope": "Published seed subset; Harbor Docker is separate from trusted local Inspect isolation.",
        "runs": runs,
    }
    (target / "plan.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def doctor():
    checks = {
        "uv": shutil.which("uvx") is not None,
        "docker": False,
        "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    }
    if shutil.which("docker"):
        checks["docker"] = (
            subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                timeout=20,
                check=False,
            ).returncode
            == 0
        )
    return {
        "checks": checks,
        "runner": load_manifest()["runner"],
        "candidate_execution": "Requires explicit API key; plans never launch model calls.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor")
    sub.add_parser("list")
    p = sub.add_parser(
        "plan", help="Freeze catalogs and emit bounded paired upstream configs"
    )
    for flag in ["dataset", "old-skills", "new-skills", "globals", "model", "output"]:
        p.add_argument("--" + flag, required=True)
    p.add_argument("--task", action="append", required=True)
    p.add_argument(
        "--effort", choices=["low", "medium", "high", "xhigh"], required=True
    )
    p.add_argument("--attempts", type=int, default=2)
    p.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    try:
        if args.action == "plan":
            if not 30 <= args.timeout <= 3600:
                raise ValueError("Timeout must be between 30 and 3600 seconds")
            result = plan(args)
        elif args.action == "doctor":
            result = doctor()
        else:
            result = load_manifest()
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
