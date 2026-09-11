"""Regression coverage for the runner-owned workspace evidence contract.

These tests deliberately exercise real disposable Git repositories.  They do
not copy the collector implementation: the production module is the system
under test and must report unavailable evidence instead of treating a failed
or incomplete observation as an unchanged workspace.

The evidence module exposes these two entry points:

    baseline = capture_baseline(workspace)
    evidence = collect_evidence(
        workspace, baseline, required_paths=(...), max_bytes=...
    )

They return typed ``Baseline`` and ``Evidence`` records whose semantic fields
are asserted below (availability, baseline/final identity, tracked
worktree/index paths, recursive untracked paths, required-path evidence, and
bounded/truncated status).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable


try:
    from evals.workspace_evidence import (
        _read_index_entries,
        capture_baseline,
        collect_evidence,
    )
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


def _field(value: object, name: str) -> object:
    return getattr(value, name)


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(item) for item in value]
    return [str(value)]


def _text(value: object) -> str:
    return value.as_text() if hasattr(value, "as_text") else repr(value)


def _assert_available(test: unittest.TestCase, value: object) -> None:
    test.assertTrue(getattr(value, "available"), _text(value))


def _assert_outcome(test: unittest.TestCase, value: object, expected: str) -> None:
    test.assertEqual(
        getattr(value, "outcome"), expected, f"unexpected evidence: {_text(value)!r}"
    )


def _assert_unavailable(test: unittest.TestCase, value: object) -> None:
    test.assertFalse(getattr(value, "available"), _text(value))


def _assert_path(test: unittest.TestCase, value: object, path: str) -> None:
    test.assertIn(path, _text(value), f"evidence did not preserve path {path!r}")


def _assert_marker(test: unittest.TestCase, value: object) -> None:
    test.assertIn(MARKER, _text(value))


def _category_paths(value: object, category: str) -> list[str]:
    names = {
        "worktree": "tracked_worktree_paths",
        "index": "tracked_index_paths",
        "untracked": "untracked_paths",
    }
    try:
        name = names[category]
    except KeyError as exc:  # pragma: no cover - test authoring guard
        raise AssertionError(category) from exc
    return _strings(_field(value, name))


class WorkspaceEvidenceTests(unittest.TestCase):
    def test_empty_index_listing_is_valid_including_missing_index_for_empty_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-empty-index-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "deleted")
            baseline = capture_baseline(repo)
            _assert_available(self, baseline)
            _git(repo, "rm", "-q", "--", "module.py")

            entries, error, overflow = _read_index_entries(
                repo,
                object_id_bytes=baseline.object_id_bytes,
                max_paths=100,
                max_bytes=100_000,
            )
            self.assertEqual(entries, ())
            self.assertIsNone(error)
            self.assertFalse(overflow)
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_outcome(self, evidence, "changed")
            _assert_path(self, evidence, "module.py")

            empty = parent / "empty"
            empty.mkdir()
            _git(empty, "init", "-q")
            _git(empty, "commit", "--allow-empty", "-qm", "empty baseline")
            index = empty / ".git" / "index"
            index.unlink()
            empty_baseline = capture_baseline(empty)
            _assert_available(self, empty_baseline)
            empty_evidence = collect_evidence(empty, empty_baseline)
            _assert_available(self, empty_evidence)
            _assert_outcome(self, empty_evidence, "unchanged observed outcome")

    def test_machine_index_fields_and_tags_preserve_modes_stages_and_semantic_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-index-fields-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            self.assertEqual(len(baseline.index_entries), 1)
            path, object_id, mode, stage, flags = baseline.index_entries[0]
            self.assertEqual(path, "module.py")
            self.assertEqual(len(object_id), baseline.object_id_bytes * 2)
            self.assertEqual(mode, 0o100644)
            self.assertEqual(stage, 0)
            self.assertEqual(flags, 0)

            _git(repo, "update-index", "--assume-unchanged", "--", "module.py")
            _git(repo, "update-index", "--skip-worktree", "--", "module.py")
            entries, error, overflow = _read_index_entries(
                repo,
                object_id_bytes=baseline.object_id_bytes,
                max_paths=100,
                max_bytes=100_000,
            )
            self.assertIsNone(error)
            self.assertFalse(overflow)
            self.assertEqual(entries[0][0], "module.py")
            self.assertEqual(entries[0][3], 0)
            self.assertEqual(entries[0][4], 0xC000)

    def test_nine_audited_fixtures(self) -> None:
        fixtures: tuple[
            tuple[str, Callable[[Path], None], tuple[str, ...], str | None, str], ...
        ] = (
            ("clean", _setup_clean, (), None, "unchanged observed outcome"),
            ("unstaged", _setup_unstaged, (), "module.py", "changed"),
            ("staged", _setup_staged, (), "module.py", "changed"),
            ("untracked_root", _setup_untracked_root, (), "new.py", "changed"),
            ("untracked_nested", _setup_untracked_nested, (), "new_feature/main.py", "changed"),
            (
                "required_nested",
                _setup_untracked_nested,
                ("new_feature/main.py",),
                "new_feature/main.py",
                "changed",
            ),
            ("committed", _setup_committed, (), "module.py", "changed"),
            ("index_only", _setup_index_only, (), "module.py", "changed"),
            (
                "untracked_unusual_name",
                _setup_unusual_untracked,
                (),
                'space "quote"\nline.py',
                "changed",
            ),
        )

        with tempfile.TemporaryDirectory(prefix="workspace-evidence-fixtures-") as raw:
            parent = Path(raw)
            for name, setup, required, expected_path, expected_outcome in fixtures:
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
                    _assert_outcome(self, evidence, expected_outcome)
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
            missing_baseline = capture_baseline(missing)
            _assert_unavailable(self, missing_baseline)

            repo = _new_repo(parent / "valid")
            baseline = capture_baseline(repo)
            shutil.rmtree(repo / ".git")
            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            _assert_outcome(self, evidence, "unavailable")
            self.assertNotIn("unchanged", _text(evidence).lower())

    def test_corrupt_or_truncated_index_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-index-corrupt-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            index = repo / ".git" / "index"
            original = index.read_bytes()
            self.assertGreater(len(original), 12)
            index.write_bytes(original[:12])

            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            _assert_outcome(self, evidence, "unavailable")
            rendered = _text(evidence).lower()
            self.assertIn("index", rendered)
            self.assertNotIn("unchanged", rendered)

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
            _assert_outcome(self, traversal, "unavailable")
            self.assertNotIn("OUTSIDE_SECRET", _text(traversal))
            _assert_path(self, traversal, "../outside.txt")

            missing = collect_evidence(
                repo,
                baseline,
                required_paths=("missing/output.txt",),
            )
            _assert_unavailable(self, missing)
            _assert_outcome(self, missing, "unavailable")
            _assert_path(self, missing, "missing/output.txt")
            self.assertNotIn("unchanged", _text(missing).lower())

            metadata = collect_evidence(
                repo,
                baseline,
                required_paths=(".git/config",),
            )
            _assert_unavailable(self, metadata)
            _assert_outcome(self, metadata, "unavailable")
            self.assertIn("git-boundary", _text(metadata).lower())
            self.assertNotIn("[remote", _text(metadata).lower())

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
            _assert_outcome(self, evidence, "unavailable")
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

    def test_redirected_git_boundary_is_unavailable_without_foreign_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-git-boundary-") as raw:
            parent = Path(raw)
            repo_a = _new_repo(parent / "repo-a")
            repo_b = _new_repo(parent / "repo-b")
            (repo_b / "module.py").write_text("FOREIGN_REPOSITORY_PAYLOAD\n", encoding="utf-8")
            _git(repo_b, "add", "--", "module.py")
            _git(repo_b, "commit", "-qm", "foreign candidate")
            baseline = capture_baseline(repo_a)
            self.assertEqual(baseline.status, "available")

            original_git = repo_a / ".git"
            saved_git = repo_a / ".git.original"
            original_git.rename(saved_git)
            original_git.symlink_to(repo_b / ".git", target_is_directory=True)

            evidence = collect_evidence(repo_a, baseline)
            _assert_unavailable(self, evidence)
            _assert_outcome(self, evidence, "unavailable")
            rendered = _text(evidence)
            self.assertNotIn("FOREIGN_REPOSITORY_PAYLOAD", rendered)
            self.assertIn(".git boundary", rendered.lower())

    def test_object_fanout_directory_symlink_is_unavailable_without_foreign_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-object-dir-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "repo")
            foreign = _new_repo(parent / "foreign")
            (foreign / "module.py").write_text("FOREIGN_OBJECT_PAYLOAD\n", encoding="utf-8")
            oid = _git(foreign, "hash-object", "-w", "--", "module.py").stdout.decode().strip()
            baseline = capture_baseline(repo)
            _git(repo, "update-index", "--add", "--cacheinfo", f"100644,{oid},module.py")

            fanout = repo / ".git" / "objects" / oid[:2]
            if fanout.exists():
                fanout.rename(repo / ".git" / "objects" / f"{oid[:2]}.saved")
            fanout.symlink_to(foreign / ".git" / "objects" / oid[:2], target_is_directory=True)

            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            self.assertIn("unreadable", _text(evidence).lower())
            self.assertNotIn("FOREIGN_OBJECT_PAYLOAD", _text(evidence))

    def test_object_loose_file_symlink_is_unavailable_without_foreign_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-object-file-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "repo")
            foreign = _new_repo(parent / "foreign")
            (foreign / "module.py").write_text("FOREIGN_LOOSE_OBJECT_PAYLOAD\n", encoding="utf-8")
            oid = _git(foreign, "hash-object", "-w", "--", "module.py").stdout.decode().strip()
            baseline = capture_baseline(repo)
            _git(repo, "update-index", "--add", "--cacheinfo", f"100644,{oid},module.py")

            fanout = repo / ".git" / "objects" / oid[:2]
            fanout.mkdir(exist_ok=True)
            (fanout / oid[2:]).symlink_to(
                foreign / ".git" / "objects" / oid[:2] / oid[2:]
            )

            evidence = collect_evidence(repo, baseline)
            _assert_unavailable(self, evidence)
            self.assertIn("unreadable", _text(evidence).lower())
            self.assertNotIn("FOREIGN_LOOSE_OBJECT_PAYLOAD", _text(evidence))

    def test_staged_and_worktree_versions_are_both_rendered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-three-versions-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            (repo / "module.py").write_text("STAGED_ONLY_PAYLOAD\n", encoding="utf-8")
            _git(repo, "add", "--", "module.py")
            (repo / "module.py").write_text("WORKTREE_ONLY_PAYLOAD\n", encoding="utf-8")

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_outcome(self, evidence, "changed")
            rendered = _text(evidence)
            self.assertIn("STAGED_ONLY_PAYLOAD", rendered)
            self.assertIn("WORKTREE_ONLY_PAYLOAD", rendered)
            self.assertIn("GIT INDEX DIFF", rendered)
            self.assertIn("GIT DIFF AGAINST BASELINE", rendered)

    def test_committed_payload_is_rendered_when_final_index_restores_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-committed-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            (repo / "module.py").write_text("COMMITTED_ONLY_PAYLOAD\n", encoding="utf-8")
            _git(repo, "add", "--", "module.py")
            _git(repo, "commit", "-qm", "candidate commit")
            _git(repo, "restore", f"--source={baseline.revision}", "--staged", "--", "module.py")
            (repo / "module.py").write_bytes(BASELINE)

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_outcome(self, evidence, "changed")
            self.assertIn("module.py", _strings(_field(evidence, "committed_paths")))
            rendered = _text(evidence)
            self.assertIn("COMMITTED_ONLY_PAYLOAD", rendered)
            self.assertIn("GIT COMMITTED DIFF", rendered)

    def test_harmless_source_names_do_not_block_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-safe-names-") as raw:
            parent = Path(raw)
            repo = _new_repo(parent / "safe")
            (repo / "tokenizer.py").write_text("def tokenize(value): return value\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src/reset_password.py").write_text("def reset_password(): pass\n", encoding="utf-8")
            (repo / ".env.example").write_text("TOKEN=replace-me\n", encoding="utf-8")
            _git(repo, "add", "--", "tokenizer.py", "src/reset_password.py", ".env.example")
            _git(repo, "commit", "-qm", "safe source names")
            baseline = capture_baseline(repo)
            _assert_available(self, baseline)

            sensitive_repo = _new_repo(parent / "sensitive")
            (sensitive_repo / "credentials.json").write_text("dummy\n", encoding="utf-8")
            _git(sensitive_repo, "add", "--", "credentials.json")
            _git(sensitive_repo, "commit", "-qm", "sensitive fixture")
            sensitive_baseline = capture_baseline(sensitive_repo)
            _assert_unavailable(self, sensitive_baseline)
            self.assertIn("sensitive content omitted", _text(sensitive_baseline).lower())

    def test_tracked_git_prefixed_filenames_are_ordinary_workspace_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-git-prefix-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            path = repo / ".git-blame-ignore-revs"
            path.write_text("0123456789abcdef\n", encoding="utf-8")
            _git(repo, "add", "--", path.name)
            _git(repo, "commit", "-qm", "tracked git-prefixed file")

            baseline = capture_baseline(repo)
            _assert_available(self, baseline)
            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            self.assertFalse(_field(evidence, "has_changes"))
            self.assertNotIn("metadata alias", _text(evidence).lower())

    def test_preexisting_ignored_file_is_inventory_not_a_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-ignored-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            (repo / ".gitignore").write_text("scratch/\n", encoding="utf-8")
            (repo / "scratch").mkdir()
            (repo / "scratch/report.txt").write_text("PREEXISTING_IGNORED\n", encoding="utf-8")
            _git(repo, "add", "--", ".gitignore")
            _git(repo, "commit", "-qm", "ignored fixture")
            baseline = capture_baseline(repo)

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            _assert_outcome(self, evidence, "unchanged observed outcome")
            self.assertFalse(_field(evidence, "has_changes"))
            self.assertIn("scratch/report.txt", _strings(_field(evidence, "baseline_untracked_paths")))
            self.assertIn("scratch/report.txt", _strings(_field(evidence, "current_untracked_paths")))
            self.assertEqual(_strings(_field(evidence, "untracked_paths")), [])

            (repo / "scratch/report.txt").write_text("CHANGED_IGNORED\n", encoding="utf-8")
            changed = collect_evidence(repo, baseline)
            _assert_available(self, changed)
            _assert_outcome(self, changed, "changed")
            self.assertTrue(_field(changed, "has_changes"))
            self.assertIn("scratch/report.txt", _strings(_field(changed, "untracked_paths")))

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

    def test_stat_cache_refresh_is_not_a_semantic_index_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-stat-cache-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            info = (repo / "module.py").stat()
            os.utime(repo / "module.py", (info.st_atime + 10, info.st_mtime + 10))
            _git(repo, "status", "--porcelain")

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            self.assertFalse(_field(evidence, "index_changed"))
            self.assertFalse(_field(evidence, "git_metadata_changed"))
            self.assertFalse(_field(evidence, "has_changes"))
            _assert_outcome(self, evidence, "unchanged observed outcome")
            self.assertEqual(_category_paths(evidence, "index"), [])

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

    def test_semantic_index_flag_changes_are_observable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-index-flag-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            _git(repo, "update-index", "--skip-worktree", "--", "module.py")

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            self.assertTrue(_field(evidence, "index_changed"))
            self.assertTrue(_field(evidence, "has_changes"))
            self.assertIn("module.py", _strings(_field(evidence, "tracked_index_paths")))

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
            _assert_outcome(self, evidence, "unavailable")
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
            _assert_outcome(self, evidence, "unavailable")
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

    def test_auxiliary_python_bytecode_does_not_invalidate_read_only_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-bytecode-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
            _git(repo, "add", "--", ".gitignore")
            _git(repo, "commit", "-qm", "ignore interpreter cache")
            baseline = capture_baseline(repo)

            result = subprocess.run(
                [sys.executable, "-c", "import module; assert module.VALUE == 'baseline'"],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(repo)},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertTrue((repo / "__pycache__").is_dir())

            evidence = collect_evidence(repo, baseline)
            _assert_available(self, evidence)
            self.assertFalse(_field(evidence, "has_changes"))
            _assert_outcome(self, evidence, "unchanged observed outcome")
            self.assertEqual(_strings(_field(evidence, "untracked_paths")), [])
            self.assertIn("sha256=", _text(evidence))

    def test_required_binary_artifact_remains_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workspace-evidence-required-binary-") as raw:
            repo = _new_repo(Path(raw) / "repo")
            baseline = capture_baseline(repo)
            (repo / "artifact.bin").write_bytes(b"\x00required\x00")

            evidence = collect_evidence(repo, baseline, required_paths=("artifact.bin",))
            _assert_unavailable(self, evidence)
            self.assertIn("binary", _text(evidence).lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
