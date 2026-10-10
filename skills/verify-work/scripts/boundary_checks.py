#!/usr/bin/env python3
"""Bounded contract checks: exact JSON output or static CI job references."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys


def check_json(actual, expected) -> None:
    # JSON true and 1 must not be interchangeable; canonical JSON preserves
    # that distinction, nested types, and extra/missing keys.
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("actual JSON differs from independently supplied contract")


def check_ci(document: dict, dialect: str) -> None:
    if not isinstance(document, dict):
        raise ValueError("CI document must be a mapping")
    if dialect == "github":
        jobs = document.get("jobs")
    else:
        if "include" in document:
            raise ValueError("included GitLab pipelines need an exported merged configuration")
        reserved = {"stages", "variables", "workflow", "default", "image", "services", "before_script", "after_script", "cache"}
        jobs = {k: v for k, v in document.items() if isinstance(k, str) and k not in reserved and not k.startswith(".")}
    if not isinstance(jobs, dict) or not jobs:
        raise ValueError("CI configuration has no static jobs")
    edges = {}
    for name, job in jobs.items():
        if not isinstance(name, str) or not name:
            raise ValueError("job names must be nonempty strings")
        if not isinstance(job, dict) or "extends" in job:
            raise ValueError("resolve job templates before checking references")
        edges[name] = []
        for field in (("needs",) if dialect == "github" else ("needs", "dependencies")):
            refs = job.get(field, [])
            refs = [refs] if isinstance(refs, str) else refs
            if not isinstance(refs, list):
                raise ValueError(f"{name}.{field} must be a static list")
            for ref in refs:
                optional = False
                if dialect == "gitlab" and field == "needs" and isinstance(ref, dict):
                    if set(ref) - {"job", "optional", "artifacts"}:
                        raise ValueError("cross-project or dynamic needs require platform validation")
                    if any(type(ref[k]) is not bool for k in ("optional", "artifacts") if k in ref):
                        raise ValueError("optional/artifacts flags must be booleans")
                    optional = ref.get("optional", False) is True
                    ref = ref.get("job")
                if not isinstance(ref, str) or not ref:
                    raise ValueError(f"{name}.{field} has an invalid job reference")
                if ref not in jobs:
                    if optional:
                        continue
                    raise ValueError(f"{name}.{field}: undefined job {ref}")
                edges[name].append(ref)
    visiting, done = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError(f"cyclic job dependency at {name}")
        if name in done:
            return
        visiting.add(name)
        for dependency in edges[name]:
            visit(dependency)
        visiting.remove(name)
        done.add(name)
    for name in jobs:
        visit(name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    js = sub.add_parser("json")
    js.add_argument("--actual", type=Path, required=True)
    js.add_argument("--expected", type=Path, required=True)
    ci = sub.add_parser("ci")
    ci.add_argument("--file", type=Path, required=True)
    ci.add_argument("--dialect", choices=("github", "gitlab"), required=True)
    args = parser.parse_args()
    if args.mode == "json":
        check_json(json.loads(args.actual.read_text()), json.loads(args.expected.read_text()))
    else:
        import yaml  # The repository's frozen environment already owns PyYAML.
        try:
            document = yaml.safe_load(args.file.read_text())
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid CI YAML: {exc}") from exc
        check_ci(document, args.dialect)
    print(json.dumps({"accepted": True, "scope": "exact JSON" if args.mode == "json" else "static job references only"}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
