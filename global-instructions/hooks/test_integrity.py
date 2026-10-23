#!/usr/bin/env python3
"""Detect changes that weaken a repository's own checks.

Compares a base revision with HEAD (or the working tree) and reports:

- tests removed: fewer test declarations than the base;
- skip markers added: more skip/only/todo/xfail markers than the base;
- gates changed: lint, type, test-runner or verify-script configuration;
- CI changed: workflow edits, reported for review but not failing, because
  routine pipeline maintenance would otherwise drown out the real signal.

Counting is a line-based heuristic for JS/TS, Python and Go test files. It is
meant to make a weakened check visible to a human reviewer, not to prove that
the remaining tests are good. Standard library only.

Exit status: 0 when nothing unapproved was found, 1 when something was,
2 on usage or git errors.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WORKTREE = "WORKTREE"

JS_TEST = (
    "*.test.js",
    "*.test.jsx",
    "*.test.ts",
    "*.test.tsx",
    "*.test.mjs",
    "*.test.cjs",
    "*.test.mts",
    "*.test.cts",
    "*.spec.js",
    "*.spec.jsx",
    "*.spec.ts",
    "*.spec.tsx",
    "*.spec.mjs",
    "*.spec.mts",
)
PY_TEST = ("test_*.py", "*_test.py")
GO_TEST = ("*_test.go",)

DECLARATIONS = {
    "js": re.compile(
        r"^\s*(?:it|test)(?:\.(?:skip|only|todo|fails|concurrent|each\(.*?\)))*\s*\(",
        re.MULTILINE,
    ),
    "py": re.compile(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", re.MULTILINE),
    "go": re.compile(r"^func\s+Test\w*\s*\(", re.MULTILINE),
}
MARKERS = {
    "js": re.compile(
        r"\b(?:it|test|describe)\.(?:skip|only|todo)\b|\b[xf](?:it|describe|test)\s*\("
    ),
    "py": re.compile(
        r"@pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.skip\s*\(|@unittest\.skip|\.skipTest\s*\("
    ),
    "go": re.compile(r"\bt\.Skip(?:Now|f)?\s*\("),
}

# Files whose edits change what "passing" means, matched against the basename
# and the full path. Workflows are reported separately as CI changes.
GATE_PATTERNS = (
    "eslint.config.*",
    ".eslintrc",
    ".eslintrc.*",
    "biome.json",
    "biome.jsonc",
    ".prettierrc",
    ".prettierrc.*",
    "prettier.config.*",
    "tsconfig*.json",
    "vitest.config.*",
    "vitest.workspace.*",
    "jest.config.*",
    "playwright.config.*",
    "ruff.toml",
    ".ruff.toml",
    "pytest.ini",
    "setup.cfg",
    "tox.ini",
    "mypy.ini",
    ".golangci.yml",
    ".golangci.yaml",
    ".semgrep.yml",
    ".pre-commit-config.yaml",
    "lefthook.yml",
    "scripts/check-*",
    "scripts/check_*",
)
PACKAGE_SCRIPTS = ("verify", "test", "lint", "typecheck", "check", "format:check")
# Dependency bots repin actions constantly; a new ref is not a weaker check.
USES_REF = re.compile(r"^(\s*-?\s*uses:\s*[^@\s]+)@\S+.*$", re.MULTILINE)
PYPROJECT_SECTIONS = re.compile(
    r"^\[tool\.(?:ruff|pytest|mypy|pyright|coverage)[^\]]*\]$", re.MULTILINE
)


@dataclass
class Report:
    tests_removed: list[str] = field(default_factory=list)
    markers_added: list[str] = field(default_factory=list)
    gates_changed: list[str] = field(default_factory=list)
    ci_changed: list[str] = field(default_factory=list)
    tests_touched: list[str] = field(default_factory=list)

    def failures(self, allow: set[str]) -> list[str]:
        found = []
        if self.tests_removed and "tests" not in allow:
            found.append("tests")
        if self.markers_added and "tests" not in allow:
            found.append("markers")
        if self.gates_changed and "gates" not in allow:
            found.append("gates")
        return found

    def as_dict(self) -> dict:
        return {
            "tests_removed": self.tests_removed,
            "markers_added": self.markers_added,
            "gates_changed": self.gates_changed,
            "ci_changed": self.ci_changed,
            "tests_touched": self.tests_touched,
        }


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def language(path: str) -> str | None:
    name = Path(path).name
    if any(fnmatch.fnmatch(name, pattern) for pattern in JS_TEST) or (
        "/__tests__/" in f"/{path}"
        and Path(path).suffix in {".js", ".jsx", ".ts", ".tsx"}
    ):
        return "js"
    if any(fnmatch.fnmatch(name, pattern) for pattern in PY_TEST):
        return "py"
    if any(fnmatch.fnmatch(name, pattern) for pattern in GO_TEST):
        return "go"
    return None


def is_gate(path: str) -> bool:
    name = Path(path).name
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(path, pattern)
        for pattern in GATE_PATTERNS
    )


def list_files(repo: Path, rev: str) -> set[str]:
    if rev == WORKTREE:
        tracked = git(repo, "ls-files", "-z").split("\0")
        untracked = git(repo, "ls-files", "-z", "--others", "--exclude-standard").split(
            "\0"
        )
        return {
            path for path in tracked + untracked if path and (repo / path).is_file()
        }
    return {
        path
        for path in git(repo, "ls-tree", "-r", "-z", "--name-only", rev).split("\0")
        if path
    }


def read(repo: Path, rev: str, path: str) -> str:
    if rev == WORKTREE:
        try:
            return (repo / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        capture_output=True,
        check=False,
    )
    return (
        result.stdout.decode("utf-8", errors="replace")
        if result.returncode == 0
        else ""
    )


def package_scripts(text: str) -> dict:
    try:
        scripts = json.loads(text).get("scripts", {})
    except (ValueError, AttributeError):
        return {}
    return {
        key: scripts.get(key) for key in PACKAGE_SCRIPTS if isinstance(scripts, dict)
    }


def pyproject_gates(text: str) -> str:
    # Keep only [tool.<checker>] sections so dependency bumps are not flagged.
    kept, keep = [], False
    for line in text.splitlines():
        if line.startswith("["):
            keep = bool(PYPROJECT_SECTIONS.match(line.strip()))
        if keep:
            kept.append(line)
    return "\n".join(kept)


def change_kind(old: str, new: str) -> str:
    return "added" if not old else "deleted" if not new else "changed"


def workflow_shape(text: str) -> str:
    return USES_REF.sub(r"\1", text)


def compare(repo: Path, base: str, head: str) -> Report:
    report = Report()
    before, after = list_files(repo, base), list_files(repo, head)
    for path in sorted(before | after):
        old = read(repo, base, path) if path in before else ""
        new = read(repo, head, path) if path in after else ""
        if old == new:
            continue
        lang = language(path)
        if lang:
            report.tests_touched.append(path)
            lost = len(DECLARATIONS[lang].findall(old)) - len(
                DECLARATIONS[lang].findall(new)
            )
            if lost > 0:
                report.tests_removed.append(f"{path}: {lost} fewer test declaration(s)")
            gained = len(MARKERS[lang].findall(new)) - len(MARKERS[lang].findall(old))
            if gained > 0:
                report.markers_added.append(
                    f"{path}: {gained} new skip/only/todo marker(s)"
                )
        elif Path(path).name == "package.json":
            old_scripts, new_scripts = package_scripts(old), package_scripts(new)
            for key in PACKAGE_SCRIPTS:
                if old_scripts.get(key) != new_scripts.get(key):
                    report.gates_changed.append(f"{path}: scripts.{key} changed")
        elif Path(path).name == "pyproject.toml":
            if pyproject_gates(old) != pyproject_gates(new):
                report.gates_changed.append(f"{path}: checker configuration changed")
        elif path.startswith(".github/workflows/"):
            if not (old and new and workflow_shape(old) == workflow_shape(new)):
                report.ci_changed.append(f"{path}: {change_kind(old, new)}")
        elif is_gate(path):
            report.gates_changed.append(f"{path}: {change_kind(old, new)}")
    return report


def render(report: Report, failures: list[str]) -> str:
    lines = []
    sections = (
        ("Tests removed", report.tests_removed),
        ("Skip markers added", report.markers_added),
        ("Check configuration changed", report.gates_changed),
        ("CI workflows changed (review, not blocking)", report.ci_changed),
    )
    for title, items in sections:
        if items:
            lines.append(f"{title}:")
            lines.extend(f"  - {item}" for item in items)
    if report.tests_touched:
        lines.append(
            "Test files edited (review these): " + ", ".join(report.tests_touched)
        )
    if failures:
        lines.append("")
        lines.append(
            "These changes weaken a check. Restore them, or get explicit human approval "
            "(CI labels: tests-removed-ok, gates-changed-ok)."
        )
    return "\n".join(lines) if lines else "No test or check weakening found."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo", default=".", help="repository root (default: current directory)"
    )
    parser.add_argument("--base", required=True, help="base revision, e.g. origin/main")
    parser.add_argument("--head", default="HEAD", help=f"head revision or {WORKTREE}")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        choices=("tests", "gates"),
        help="approved weakening category; repeatable",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        base = git(repo, "rev-parse", "--verify", f"{args.base}^{{commit}}").strip()
        head = (
            WORKTREE
            if args.head == WORKTREE
            else git(repo, "rev-parse", "--verify", f"{args.head}^{{commit}}").strip()
        )
        report = compare(repo, base, head)
    except RuntimeError as error:
        print(f"test_integrity: {error}", file=sys.stderr)
        return 2
    failures = report.failures(set(args.allow))
    if args.json:
        print(json.dumps({**report.as_dict(), "failures": failures}, indent=2))
    else:
        print(render(report, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
