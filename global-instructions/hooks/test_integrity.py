#!/usr/bin/env python3
"""Detect changes that weaken a repository's own checks.

Compares two git trees: a base revision, and HEAD or a snapshot of the working
tree. It reports:

- tests removed: fewer test declarations than the base, totalled per language
  across changed files, so moving or renaming tests is not a removal;
- skip markers added: more skip/only/todo/fixme/xfail markers than the base;
- gates changed: lint, type, test-runner or verify configuration, including
  the recipe or scripts the repository's verify command runs;
- CI changed: workflow edits, reported for review without failing.

Only paths git reports as changed are read, so line endings, symlinks and
sparse checkouts behave as git sees them. Counting is a line-based heuristic for
JS/TS, Python and Go; it makes a weakened check visible to a reviewer and does
not prove the remaining tests are good. Standard library only.

Exit status: 0 when nothing unapproved was found, 1 when something was,
2 on usage or git errors.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

WORKTREE = "WORKTREE"

JS_TEST_FILE = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$")
PY_TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]*|[^/]*_test|tests)\.py$")
PY_TEST_DIR = re.compile(r"(?:^|/)tests?/(?:[^/]+/)*[^/]+\.py$")
GO_TEST_FILE = re.compile(r"_test\.go$")

DECLARATIONS = {
    # it(...), test.only(...), it.concurrent(...), and each table counted once.
    "js": re.compile(r"^\s*(?:it|test)(?:\.[A-Za-z]+)*\s*(?:\(|`)", re.MULTILINE),
    "py": re.compile(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", re.MULTILINE),
    "go": re.compile(r"^func\s+Test\w*\s*\(", re.MULTILINE),
}
MARKERS = {
    "js": re.compile(
        r"\b(?:it|test|describe)(?:\.[A-Za-z]+)*\.(?:skip|only|todo|fixme|skipIf|runIf)\b"
        r"|\b[xf](?:it|describe|test)\s*\("
    ),
    "py": re.compile(
        r"@pytest\.mark\.(?:skip|skipif|xfail)\b|\bpytest\.skip\s*\("
        r"|\bpytestmark\s*=.*\b(?:skip|skipif|xfail)\b"
        r"|@(?:unittest\.)?skip(?:If|Unless)?\b|\.skipTest\s*\("
    ),
    "go": re.compile(r"\bt\.Skip(?:Now|f)?\s*\(|^//go:build\s+ignore", re.MULTILINE),
}

# Files whose edits change what "passing" means, matched against the basename
# and the full path. Workflows are reported separately as CI changes.
GATE_PATTERNS = (
    "eslint.config.*",
    ".eslintrc",
    ".eslintrc.*",
    ".eslintignore",
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
    "mypy.ini",
    "pyrightconfig.json",
    ".flake8",
    ".golangci.yml",
    ".golangci.yaml",
    ".golangci.toml",
    ".semgrep.yml",
    ".pre-commit-config.yaml",
    "lefthook.yml",
    "scripts/check-*",
    "scripts/check_*",
)
# Only these parts of mixed-purpose files define checks.
SECTION_FILTERED = {
    "pyproject.toml": re.compile(
        r"^\[\[?tool\.(?:ruff|pytest|mypy|pyright|coverage)\b"
    ),
    "setup.cfg": re.compile(
        r"^\[(?:flake8|mypy|tool:pytest|pytest|coverage:|isort|pycodestyle)"
    ),
    "tox.ini": re.compile(
        r"^\[(?:flake8|mypy|pytest|testenv|coverage:|isort|pycodestyle)"
    ),
}
LINE_FILTERED = {
    "conftest.py": re.compile(r"collect_ignore|pytest_collection_modifyitems|addopts"),
    "vite.config.*": re.compile(r"\btest\b|exclude|include"),
}
MAKEFILES = ("Makefile", "makefile", "GNUmakefile", "justfile", "Justfile")
ROOT_SCRIPTS = ("verify", "test", "lint", "typecheck", "check", "format:check")
SCRIPT_REFERENCE = re.compile(
    r"\b(?:npm\s+run|pnpm(?:\s+run)?|yarn(?:\s+run)?|bun\s+run)\s+([\w:.@/-]+)"
)
# Dependency bots repin actions constantly; a new ref is not a weaker check.
# The integrity workflow itself keeps its ref, so repinning it stays visible.
USES_REF = re.compile(
    r"^(\s*-?\s*uses:\s*(?![^@\s]*test-integrity\.yml)[^@\s]+)@\S+.*$", re.MULTILINE
)
WEAKENING_KEYS = ("tests_removed", "markers_added", "gates_changed")


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

    def digest(self) -> str:
        """Identify the weakening findings, independent of unrelated edits."""
        weakening = {key: self.as_dict()[key] for key in WEAKENING_KEYS}
        encoded = json.dumps(weakening, sort_keys=True).encode(
            "utf-8", "surrogateescape"
        )
        return hashlib.sha256(encoded).hexdigest()[:24]


def git(repo: Path, *args: str, env: dict | None = None, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, env=env, check=False
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)}: {message}")
    return result.stdout.decode("utf-8", "surrogateescape")


def snapshot_tree(repo: Path) -> str:
    """Hash the working tree, including untracked files, without touching the index."""
    index = Path(git(repo, "rev-parse", "--git-path", "index").strip())
    if not index.is_absolute():
        index = repo / index
    handle, temporary = tempfile.mkstemp(prefix="agent-gates-index-")
    os.close(handle)
    try:
        if index.exists():
            # Copying keeps skip-worktree bits, so sparse paths are not "deleted".
            shutil.copyfile(index, temporary)
        else:
            os.unlink(temporary)
        env = {**os.environ, "GIT_INDEX_FILE": temporary}
        git(repo, "add", "-A", env=env)
        return git(repo, "write-tree", env=env).strip()
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def resolve(repo: Path, rev: str) -> str:
    if rev == WORKTREE:
        return snapshot_tree(repo)
    return git(repo, "rev-parse", "--verify", f"{rev}^{{tree}}").strip()


def blob(repo: Path, tree: str, path: str) -> str:
    return git(repo, "cat-file", "blob", f"{tree}:{path}", check=False)


def language(path: str) -> str | None:
    if not path:
        return None
    if JS_TEST_FILE.search(path) or (
        "/__tests__/" in f"/{path}" and re.search(r"\.[cm]?[jt]sx?$", path)
    ):
        return "js"
    if PY_TEST_FILE.search(path) or (
        PY_TEST_DIR.search(path)
        and Path(path).name not in ("__init__.py", "conftest.py")
    ):
        return "py"
    if GO_TEST_FILE.search(path):
        return "go"
    return None


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(Path(path).name, pattern) or fnmatch.fnmatch(path, pattern)


def sections(text: str, header: re.Pattern) -> str:
    kept, keep = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("["):
            keep = bool(header.match(line.strip()))
        if keep:
            kept.append(line)
    return "\n".join(kept)


def watched_scripts(text: str) -> dict:
    """Root check scripts plus every script they run, transitively."""
    try:
        scripts = json.loads(text).get("scripts", {})
    except (ValueError, AttributeError):
        return {}
    if not isinstance(scripts, dict):
        return {}
    seen: dict = {}
    pending = [name for name in ROOT_SCRIPTS if name in scripts]
    while pending:
        name = pending.pop()
        if name in seen or not isinstance(scripts.get(name), str):
            continue
        seen[name] = scripts[name]
        pending.extend(SCRIPT_REFERENCE.findall(scripts[name]))
        pending.extend(
            hook for hook in (f"pre{name}", f"post{name}") if hook in scripts
        )
    return seen


def recipe(text: str, target: str = "verify") -> str:
    """A make/just target's recipe plus the recipes of its prerequisites."""
    blocks: dict[str, tuple[str, str]] = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        header = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?!=)(.*)$", line)
        if not header:
            continue
        body = []
        for following in lines[index + 1 :]:
            if following.startswith(("\t", "    ")) or not following.strip():
                body.append(following)
            else:
                break
        blocks[header.group(1)] = (header.group(2), "\n".join(body).rstrip())
    seen: set[str] = set()
    pending, parts = [target], []
    while pending:
        name = pending.pop()
        if name in seen or name not in blocks:
            continue
        seen.add(name)
        prerequisites, body = blocks[name]
        parts.append(f"{name}:{prerequisites}\n{body}")
        pending.extend(re.findall(r"[A-Za-z0-9_.-]+", prerequisites.split("#")[0]))
    return "\n".join(sorted(parts))


def workflow_shape(text: str) -> str:
    return USES_REF.sub(r"\1", text)


def kind(old: str, new: str) -> str:
    return "added" if not old else "deleted" if not new else "changed"


def changed_paths(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    """(old_path, new_path) pairs for changed files; '' marks an absent side."""
    raw = git(repo, "diff-tree", "-r", "-z", "-M", "--name-status", base, head).split(
        "\0"
    )
    pairs, index = [], 0
    while index < len(raw) - 1 and raw[index]:
        status = raw[index]
        if status[0] in "RC":
            pairs.append((raw[index + 1], raw[index + 2]))
            index += 3
        else:
            path = raw[index + 1]
            pairs.append(
                ("" if status[0] == "A" else path, "" if status[0] == "D" else path)
            )
            index += 2
    return pairs


def compare(repo: Path, base: str, head: str) -> Report:
    """Compare two tree-ish revisions (commits or tree hashes)."""
    report = Report()
    declarations: dict[str, list[int]] = {}
    markers: dict[str, list[int]] = {}
    details: dict[str, list[str]] = {}
    for old_path, new_path in changed_paths(repo, base, head):
        path = new_path or old_path
        old = blob(repo, base, old_path) if old_path else ""
        new = blob(repo, head, new_path) if new_path else ""
        old_lang, new_lang = language(old_path), language(new_path)
        name = Path(path).name
        if old_lang or new_lang:
            lang = old_lang or new_lang
            report.tests_touched.append(path)
            before = len(DECLARATIONS[lang].findall(old)) if old_lang else 0
            after = len(DECLARATIONS[lang].findall(new)) if new_lang else 0
            counts = declarations.setdefault(lang, [0, 0])
            counts[0] += before
            counts[1] += after
            # A new test file that skips itself (for example, integration tests
            # gated on an environment variable) adds coverage; only skips in
            # files that already existed can hide a test that used to run.
            if old_lang:
                marks = markers.setdefault(lang, [0, 0])
                marks[0] += len(MARKERS[lang].findall(old))
                marks[1] += len(MARKERS[lang].findall(new)) if new_lang else 0
            if before != after:
                details.setdefault(lang, []).append(f"{path}: {before} -> {after}")
        elif name == "package.json":
            old_scripts, new_scripts = watched_scripts(old), watched_scripts(new)
            for key in sorted(set(old_scripts) | set(new_scripts)):
                if old_scripts.get(key) != new_scripts.get(key):
                    state = kind(old_scripts.get(key, ""), new_scripts.get(key, ""))
                    report.gates_changed.append(f"{path}: scripts.{key} {state}")
        elif name in MAKEFILES:
            if recipe(old) != recipe(new):
                report.gates_changed.append(
                    f"{path}: verify recipe {kind(recipe(old), recipe(new))}"
                )
        elif name in SECTION_FILTERED:
            if sections(old, SECTION_FILTERED[name]) != sections(
                new, SECTION_FILTERED[name]
            ):
                report.gates_changed.append(f"{path}: checker configuration changed")
        elif path.startswith(".github/workflows/"):
            if not (old and new and workflow_shape(old) == workflow_shape(new)):
                report.ci_changed.append(f"{path}: {kind(old, new)}")
        elif any(matches(path, pattern) for pattern in GATE_PATTERNS):
            report.gates_changed.append(f"{path}: {kind(old, new)}")
        else:
            for pattern, watched in LINE_FILTERED.items():
                if matches(path, pattern):
                    old_lines = [
                        line for line in old.splitlines() if watched.search(line)
                    ]
                    new_lines = [
                        line for line in new.splitlines() if watched.search(line)
                    ]
                    if old_lines != new_lines:
                        report.gates_changed.append(f"{path}: test selection changed")
    for lang, (before, after) in sorted(declarations.items()):
        if after < before:
            changes = "; ".join(details.get(lang, []))
            report.tests_removed.append(
                f"{lang}: {before - after} fewer test declaration(s) ({changes})"
            )
    for lang, (before, after) in sorted(markers.items()):
        if after > before:
            report.markers_added.append(
                f"{lang}: {after - before} new skip/only/todo marker(s)"
            )
    return report


def render(report: Report, failures: list[str]) -> str:
    lines = []
    groups = (
        ("Tests removed", report.tests_removed),
        ("Skip markers added", report.markers_added),
        ("Check configuration changed", report.gates_changed),
        ("CI workflows changed (review, not blocking)", report.ci_changed),
    )
    for title, items in groups:
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
            "(CI labels: tests-ok:<full-head-sha>, gates-ok:<full-head-sha>)."
        )
    return "\n".join(lines) if lines else "No test or check weakening found."


def approvals(events: list, head: str, approvers: set[str]) -> set[str]:
    """Human label approvals bound to the exact full head SHA, never its date."""
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        return set()
    labels = {f"tests-ok:{head}": "tests", f"gates-ok:{head}": "gates"}
    granted: dict[str, bool] = {}
    for event in sorted(events, key=lambda item: item.get("id", 0)):
        name = (event.get("label") or {}).get("name")
        if name not in labels:
            continue
        if event.get("event") == "unlabeled":
            granted[name] = False
            continue
        if event.get("event") != "labeled":
            continue
        actor = event.get("actor") or {}
        human = actor.get("type") == "User" and not actor.get("login", "").endswith(
            "[bot]"
        )
        granted[name] = bool(
            human and (not approvers or actor.get("login") in approvers)
        )
    return {labels[name] for name, ok in granted.items() if ok}


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
    parser.add_argument("--approval-events", help="JSON file of GitHub issue events")
    parser.add_argument(
        "--approval-head",
        default="",
        help="full head SHA that human approval labels must name",
    )
    parser.add_argument(
        "--approvers", default="", help="comma-separated logins allowed to approve"
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    allow = set(args.allow)
    try:
        if args.approval_events:
            if (
                args.approval_head
                != git(repo, "rev-parse", "--verify", f"{args.head}^{{commit}}").strip()
            ):
                raise ValueError("approval head must match the compared commit")
            events = json.loads(Path(args.approval_events).read_text() or "[]")
            approvers = {
                name.strip() for name in args.approvers.split(",") if name.strip()
            }
            allow |= approvals(events, args.approval_head, approvers)
        report = compare(repo, resolve(repo, args.base), resolve(repo, args.head))
    except (RuntimeError, OSError, ValueError) as error:
        print(f"test_integrity: {error}", file=sys.stderr)
        return 2
    failures = report.failures(allow)
    if args.json:
        payload = {**report.as_dict(), "failures": failures, "approved": sorted(allow)}
        print(json.dumps(payload, indent=2))
    else:
        print(render(report, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
