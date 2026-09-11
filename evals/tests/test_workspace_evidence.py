"""Regression coverage for the runner-owned workspace evidence contract.

These tests deliberately exercise real disposable Git repositories.  They do
not copy the collector implementation: the production module is the system
under test and must report unavailable evidence instead of treating a failed
or incomplete observation as an unchanged workspace.

The first implementation slice defines these two small entry points in
``evals.workspace_evidence``::

    baseline = capture_baseline(workspace)
    evidence = collect_evidence(
        workspace, baseline, required_paths=(...), max_bytes=...
    )

The result may be a dataclass or mapping, but it must expose the semantic
fields asserted below (availability, baseline/final identity, tracked
worktree/index paths, recursive untracked paths, required-path evidence, and
bounded/truncated status).
"""

from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable


try:
    from evals.workspace_evidence import capture_baseline, collect_evidence
except (ImportError, AttributeError) as exc:  # pragma: no cover - contract guard
    raise ImportError(
        "Increment A requires evals.workspace_evidence.capture_baseline and "
        "evals.workspace_evidence.collect_evidence"
    ) from exc


BASELINE = b'VALUE = "baseline"\n'
MARKER = "AUDIT_CHANGED_MARKER"
GIT_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "workspace-evidence-fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "workspace-evidence-fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
}


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """Run Git with fixture-only identity and no ambient configuration."""

    env = os.environ.copy()
    env.update(GIT_ENV)
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode,
            ["git", *args],
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def _new_repo(parent: Path) -> Path:
    repo = parent / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "module.py").write_bytes(BASELINE)
    _git(repo, "add", "--", "module.py")
    _git(repo, "commit", "-qm", "fixture baseline")
    return repo


def _write_marker(path: Path) -> None:
    path.write_text(MARKER + "\n", encoding="utf-8")


def _setup_clean(repo: Path) -> None:
    del repo


def _setup_unstaged(repo: Path) -> None:
    _write_marker(repo / "module.py")


def _setup_staged(repo: Path) -> None:
    _setup_unstaged(repo)
    _git(repo, "add", "--", "module.py")


def _setup_untracked_root(repo: Path) -> None:
    _write_marker(repo / "new.py")


def _setup_untracked_nested(repo: Path) -> None:
    nested = repo / "new_feature"
    nested.mkdir()
    _write_marker(nested / "main.py")


def _setup_committed(repo: Path) -> None:
    _setup_unstaged(repo)
    _git(repo, "add", "--", "module.py")
    _git(repo, "commit", "-qm", "fixture candidate")


def _setup_index_only(repo: Path) -> None:
    _setup_unstaged(repo)
    _git(repo, "add", "--", "module.py")
    (repo / "module.py").write_bytes(BASELINE)


def _setup_unusual_untracked(repo: Path) -> None:
    unusual = repo / 'space "quote"\nline.py'
    _write_marker(unusual)


def _mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if hasattr(value, "__dict__"):
        return vars(value)
    return None


_MISSING = object()


def _field(value: Any, *names: str) -> Any:
    mapping = _mapping(value)
    if mapping is not None:
        for name in names:
            if name in mapping:
                return mapping[name]
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return _MISSING


def _strings(value: Any, seen: set[int] | None = None) -> list[str]:
    """Flatten result metadata without requiring one serialization format."""

    if seen is None:
        seen = set()
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, Path):
        return [str(value)]
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        return [value.decode("utf-8", errors="replace")]
    marker = id(value)
    if marker in seen:
        return []
    seen.add(marker)
    mapping = _mapping(value)
    if mapping is not None:
        output: list[str] = []
        for key, item in mapping.items():
            output.extend(_strings(key, seen))
            output.extend(_strings(item, seen))
        return output
    if isinstance(value, (list, tuple, set, frozenset)):
        output = []
        for item in value:
            output.extend(_strings(item, seen))
        return output
    if isinstance(value, BaseException):
        return [value.__class__.__name__, str(value)]
    return [str(value)]


def _text(value: Any) -> str:
    return "\n".join(_strings(value))


def _status(value: Any) -> str | None:
    raw = _field(value, "status", "state", "outcome", "availability")
    if raw is _MISSING or raw is None:
        return None
    return str(raw).lower()


def _assert_available(test: unittest.TestCase, value: Any) -> None:
    status = _status(value)
    if status is not None:
        test.assertNotIn(status, {"unavailable", "blocked", "error", "failed"})
        return
    available = _field(value, "available", "is_available")
    if available is not _MISSING:
        test.assertTrue(available)
        return
    test.fail("workspace evidence must expose status or availability")


def _assert_unavailable(test: unittest.TestCase, value: Any) -> None:
    status = _status(value)
    if status is not None:
        test.assertIn(status, {"unavailable", "blocked", "error", "failed"})
        return
    available = _field(value, "available", "is_available")
    if available is not _MISSING:
        test.assertFalse(available)
        return
    unavailable = _field(value, "unavailable")
    if unavailable is not _MISSING:
        test.assertTrue(unavailable)
        return
    test.fail("failed evidence must be explicitly unavailable")


def _assert_path(test: unittest.TestCase, value: Any, path: str) -> None:
    test.assertTrue(
        any(path in item for item in _strings(value)),
        f"evidence did not preserve path {path!r}: {_text(value)!r}",
    )


def _assert_marker(test: unittest.TestCase, value: Any) -> None:
    test.assertIn(MARKER, _text(value))


def _category_paths(value: Any, category: str) -> list[str]:
    if category == "worktree":
        names = ("tracked_worktree_paths", "worktree_paths", "working_tree_paths")
    elif category == "index":
        names = ("tracked_index_paths", "index_paths", "cached_paths")
    elif category == "untracked":
        names = ("untracked_paths", "untracked")
    else:  # pragma: no cover - test authoring guard
        raise AssertionError(category)
    value = _field(value, *names)
    if value is _MISSING:
        raise AssertionError(f"evidence missing {category} path field: {names}")
    return _strings(value)


class WorkspaceEvidenceTests(unittest.TestCase):
    def test_nine_audited_fixtures(self) -> None:
        fixtures: tuple[tuple[str, Callable[[Path], None], tuple[str, ...], str | None], ...] = (
            ("clean", _setup_clean, (), None),
            ("unstaged", _setup_unstaged, (), "module.py"),
            ("staged", _setup_staged, (), "module.py"),
            ("untracked_root", _setup_untracked_root, (), "new.py"),
            ("untracked_nested", _setup_untracked_nested, (), "new_feature/main.py"),
            (
                "required_nested",
                _setup_untracked_nested,
                ("new_feature/main.py",),
                "new_feature/main.py",
            ),
            ("committed", _setup_committed, (), "module.py"),
            ("index_only", _setup_index_only, (), "module.py"),
            (
                "untracked_unusual_name",
                _setup_unusual_untracked,
                (),
                'space "quote"\nline.py',
            ),
        )

        with tempfile.TemporaryDirectory(prefix="workspace-evidence-fixtures-") as raw:
            parent = Path(raw)
            for name, setup, required, expected_path in fixtures:
                with self.subTest(fixture=name):
                    repo = _new_repo(parent / name)
                    baseline = capture_baseline(repo)
                    _assert_available(self, baseline)
                    setup(repo)
                    evidence = collect_evidence(
                        repo,
                        baseline,
                        required_paths=required,
                    )
                    _assert_available(self, evidence)
                    if expected_path is None:
                        self.assertNotIn(MARKER, _text(evidence))
                    else:
                        _assert_path(self, evidence, expected_path)
                        _assert_marker(self, evidence)

            # Category-specific assertions ensure staged and index-only edits
            # cannot be flattened into a single final-status observation.
            staged_repo = _new_repo(parent / "category-staged")
            staged_baseline = capture_baseline(staged_repo)
            _setup_staged(staged_repo)
            staged = collect_evidence(staged_repo, staged_baseline)
            self.assertTrue(any("module.py" in p for p in _category_paths(staged, "index")))

            unstaged_repo = _new_repo(parent / "category-unstaged")
            unstaged_baseline = capture_baseline(unstaged_repo)
            _setup_unstaged(unstaged_repo)
            unstaged = collect_evidence(unstaged_repo, unstaged_baseline)
            self.assertTrue(any("module.py" in p for p in _category_paths(unstaged, "worktree")))

            untracked_repo = _new_repo(parent / "category-untracked")
            untracked_baseline = capture_baseline(untracked_repo)
            _setup_untracked_nested(untracked_repo)
            untracked = collect_evidence(untracked_repo, untracked_baseline)
            self.assertIn("new_feature/main.py", _category_paths(untracked, "untracked"))

    def test_missing_or_failed_baseline_and_collection_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-failure-") as raw:
            parent = Path(raw)
            missing = parent / "not-a-git-repository"
            missing.mkdir()
            _assert_unavailable(self, capture_baseline(missing))

            repo = _new_repo(parent / "valid")
            baseline = capture_baseline(repo)
            shutil.rmtree(repo / ".git")
            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            self.assertNotIn("unchanged", _text(evidence).lower())

    def test_required_paths_are_relative_and_missing_paths_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-boundary-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "repo")
            outside = parent / "outside.txt"
            outside.write_text("OUTSIDE_SECRET\n", encoding="utf-8")
            baseline = capture_baseline(repo)

            traversal = collect_evidence(
                repo,
                baseline,
                required_paths=("../outside.txt",),
            )
            _assert_unavailable(self, traversal)
            self.assertNotIn("OUTSIDE_SECRET", _text(traversal))
            _assert_path(self, traversal, "../outside.txt")

            missing = collect_evidence(
                repo,
                baseline,
                required_paths=("missing/output.txt",),
            )
            _assert_unavailable(self, missing)
            _assert_path(self, missing, "missing/output.txt")
            self.assertNotIn("unchanged", _text(missing).lower())

    def test_symlink_required_path_is_reported_without_following_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-symlink-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "repo")
            outside = parent / "outside-secret.txt"
            outside.write_text("SYMLINK_SECRET_CONTENT\n", encoding="utf-8")
            link = repo / "link.txt"
            link.symlink_to(outside)
            baseline = capture_baseline(repo)

            evidence = collect_evidence(repo, baseline, required_paths=("link.txt",))
            _assert_path(self, evidence, "link.txt")
            rendered = _text(evidence).lower()
            self.assertIn("symlink", rendered)
            self.assertNotIn("symlink_secret_content", rendered)

    def test_truncated_evidence_is_bounded_and_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-truncated-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            large = repo / "large.txt"
            large.write_text(MARKER + "\n" + ("x" * 4096), encoding="utf-8")
            baseline = capture_baseline(repo)

            evidence = collect_evidence(repo, baseline, max_bytes=64)
            _assert_unavailable(self, evidence)
            _assert_path(self, evidence, "large.txt")
            rendered = _text(evidence).lower()
            self.assertTrue(
                "truncat" in rendered or "omitted" in rendered,
                f"bounded evidence lacked an omission/truncation reason: {rendered!r}",
            )
            self.assertNotIn("unchanged", rendered)

    def test_two_trials_do_not_share_baseline_or_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-isolation-") as raw:
            parent = Path(raw)
            repo_a = _new_repo(parent / "a")
            repo_b = _new_repo(parent / "b")
            baseline_a = capture_baseline(repo_a)
            baseline_b = capture_baseline(repo_b)

            _setup_untracked_root(repo_a)
            evidence_a = collect_evidence(repo_a, baseline_a)
            evidence_b = collect_evidence(repo_b, baseline_b)

            _assert_available(self, evidence_a)
            _assert_marker(self, evidence_a)
            _assert_available(self, evidence_b)
            self.assertNotIn(MARKER, _text(evidence_b))
            self.assertNotIn("new.py", _text(evidence_b))

    def test_candidate_git_filters_are_never_executed_by_collection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-filter-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            filter_script = repo / "filter.sh"
            filter_script.write_text(
                "#!/bin/sh\n"
                f"touch '{repo / 'filter-ran'}'\n"
                "cat\n",
                encoding="utf-8",
            )
            filter_script.chmod(0o700)
            _git(repo, "config", "filter.attack.process", str(filter_script) + " %f")
            (repo / ".gitattributes").write_text("module.py filter=attack\n", encoding="utf-8")

            evidence = collect_evidence(repo, baseline)
            self.assertFalse((repo / "filter-ran").exists())
            self.assertNotIn("FILTER_EXECUTED", _text(evidence))

    def test_index_flags_cannot_hide_a_worktree_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-index-flags-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            _write_marker(repo / "module.py")
            _git(repo, "update-index", "--skip-worktree", "--", "module.py")
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_marker(self, evidence)
            self.assertTrue(_field(evidence, "has_changes"))

    def test_mode_only_changes_are_observable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-mode-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            (repo / "module.py").chmod(0o755)
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            self.assertTrue(_field(evidence, "has_changes"))
            _assert_path(self, evidence, "module.py")

            _git(repo, "update-index", "--no-skip-worktree", "--", "module.py")
            (repo / "module.py").write_bytes(BASELINE)
            _write_marker(repo / "module.py")
            _git(repo, "update-index", "--assume-unchanged", "--", "module.py")
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_marker(self, evidence)

    def test_replace_refs_do_not_change_the_trusted_comparison(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-replace-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            _write_marker(repo / "module.py")
            _git(repo, "add", "--", "module.py")
            _git(repo, "commit", "-qm", "candidate change")
            _git(repo, "update-ref", f"refs/replace/{baseline.revision}", "HEAD")
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_marker(self, evidence)
            self.assertTrue(_field(evidence, "has_changes"))

    def test_path_limit_overflow_is_explicitly_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-path-limit-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            for index in range(101):
                _write_marker(repo / f"new-{index:03d}.py")
            evidence = collect_evidence(repo, baseline, max_paths=100)
            _assert_unavailable(self, evidence)
            rendered = _text(evidence).lower()
            self.assertIn("path limit", rendered)
            self.assertTrue(_field(evidence, "truncated"))

    def test_hardlink_aliases_are_not_read_into_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-hardlink-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "repo")
            outside = parent / "outside-secret.txt"
            outside.write_text("HARDLINK_SECRET_CONTENT\n", encoding="utf-8")
            baseline = capture_baseline(repo)
            os.link(outside, repo / "alias.txt")
            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            rendered = _text(evidence).lower()
            self.assertIn("hardlink", rendered)
            self.assertNotIn("hardlink_secret_content", rendered)

    def test_secret_content_is_redacted_even_in_a_nonsensitive_filename(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-redaction-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            (repo / "output.txt").write_text(
                "token=TOP_SECRET_VALUE\n-----BEGIN PRIVATE KEY-----\nKEY\n"
                "-----END PRIVATE KEY-----\n",
                encoding="utf-8",
            )
            evidence = collect_evidence(repo, baseline)
            rendered = _text(evidence)
            self.assertNotIn("TOP_SECRET_VALUE", rendered)
            self.assertNotIn("-----BEGIN PRIVATE KEY-----", rendered)
            self.assertIn("REDACTED", rendered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
