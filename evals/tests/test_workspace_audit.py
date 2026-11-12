"""Real Git CLI acceptance tests, using disposable repos and linked worktrees."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/workspace_audit.py"


class WorkspaceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "primary"
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_OPTIONAL_LOCKS="0",
        )
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Audit test")
        self.git(self.repo, "config", "user.email", "audit@example.invalid")
        self.odd = 'tracked \n雪".txt'
        (self.repo / self.odd).write_text("baseline\n")
        (self.repo / ".gitignore").write_text("*.sqlite\ncache/\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "baseline")
        self.base = self.git(self.repo, "rev-parse", "HEAD").decode().strip()
        self.remote = self.root / "remote.git"
        self.git(self.repo, "init", "--bare", "-q", str(self.remote))
        self.git(self.repo, "remote", "add", "origin", str(self.remote))
        self.git(self.repo, "push", "-q", "-u", "origin", "main")
        self.paths = {}
        # Only fixture worktrees are allocated here; never the engineering checkout.
        for name in ("clean", "modified", "untracked", "ignored", "missing"):
            path = self.root / (name + " space\n雪")
            self.git(self.repo, "worktree", "add", "-q", "-b", name, str(path))
            self.paths[name] = path
        self.git(self.paths["clean"], "checkout", "-q", "--detach")
        (self.paths["modified"] / self.odd).write_text("modified\n")
        (self.paths["untracked"] / 'note \n雪"').write_text("note")
        ignored = self.paths["ignored"]
        (ignored / "state.sqlite").write_bytes(b"SQLite fixture\0")
        (ignored / "cache").mkdir()
        (ignored / "cache" / "one").write_bytes(b"one")
        (ignored / "cache" / "two\n雪").write_bytes(b"two")
        self.git(
            self.repo, "worktree", "lock", "--reason", "pilot\nretain 雪", str(ignored)
        )
        shutil.rmtree(self.paths["missing"])

    def git(self, path, *args):
        return subprocess.check_output(
            [
                "git",
                "--no-optional-locks",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(path),
                *args,
            ],
            env=self.env,
            stderr=subprocess.PIPE,
        )

    def snapshot(self):
        # Includes .git/worktrees, every index, refs, bare remote and worktree files.
        manifest = {}
        for path in [self.root, *sorted(self.root.rglob("*"))]:
            stat = path.lstat()
            data = path.read_bytes() if path.is_file() else b""
            manifest[str(path.relative_to(self.root))] = (
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(data).hexdigest(),
            )
        return (
            self.git(self.repo, "worktree", "list", "--porcelain"),
            self.git(self.repo, "worktree", "list", "--porcelain", "-z"),
            self.git(self.repo, "show-ref"),
            manifest,
        )

    def run_audit(self, explicit=True):
        before = self.snapshot()
        command = [sys.executable, str(SCRIPT)]
        if explicit:
            command += ["--repo", str(self.repo)]
        result = subprocess.run(
            command,
            cwd=self.repo,
            env={**self.env, "GIT_OPTIONAL_LOCKS": "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(before, self.snapshot(), "audit mutated fixture state")
        self.assertEqual(len(rows), 6)
        return {row["path"]: row for row in rows}

    def test_registered_worktrees_and_no_mutation(self):
        rows = self.run_audit()
        for name, path in {"main": self.repo, **self.paths}.items():
            row = rows[str(path)]
            with self.subTest(worktree=name):
                self.assertEqual(row["exists"], name != "missing")
                self.assertEqual(row["primary"], name == "main")
                self.assertEqual(row["locked"], name == "ignored")
                self.assertEqual(row["registration"]["HEAD"], self.base)
                if name == "missing":
                    self.assertEqual(
                        row["registration"]["branch"], "refs/heads/missing"
                    )
                    for field in (
                        "branch",
                        "head",
                        "tracked_changes",
                        "untracked_paths",
                        "ignored_by_top_level",
                        "commits_not_in_local_remote_refs",
                    ):
                        self.assertEqual(row[field], {"unknown": "directory missing"})
                    continue
                self.assertEqual(
                    row["branch"],
                    {"unknown": "detached HEAD"} if name == "clean" else name,
                )
                self.assertEqual(row["head"], self.base)
                self.assertEqual(row["tracked_changes"], int(name == "modified"))
                self.assertEqual(row["untracked_paths"], int(name == "untracked"))
                self.assertEqual(
                    row["ignored_by_top_level"],
                    {"state.sqlite": 1, "cache": 2} if name == "ignored" else {},
                )
                self.assertEqual(row["commits_not_in_local_remote_refs"], 0)
        self.assertEqual(
            rows[str(self.paths["ignored"])]["lock_reason"], "pilot\nretain 雪"
        )

    def test_local_commit_and_empty_remote_refs(self):
        self.git(self.repo, "commit", "--allow-empty", "-qm", "local only")
        rows = self.run_audit(explicit=False)
        self.assertEqual(rows[str(self.repo)]["commits_not_in_local_remote_refs"], 1)
        self.git(self.repo, "remote", "remove", "origin")
        rows = self.run_audit()
        self.assertEqual(rows[str(self.repo)]["commits_not_in_local_remote_refs"], 2)
        self.assertEqual(
            rows[str(self.paths["clean"])]["commits_not_in_local_remote_refs"], 1
        )

    def test_staged_rename_and_unmerged(self):
        path = self.paths["modified"]
        self.git(path, "mv", self.odd, "renamed\n雪")
        (path / "extra").write_text("new")
        self.git(path, "add", "extra")
        rows = self.run_audit()
        self.assertEqual(rows[str(path)]["tracked_changes"], 2)
        # Build a real conflicting merge on the untracked worktree.
        path = self.paths["untracked"]
        self.git(path, "checkout", "-qb", "other")
        (path / self.odd).write_text("other\n")
        self.git(path, "commit", "-qam", "other")
        self.git(path, "checkout", "-q", "untracked")
        (path / self.odd).write_text("ours\n")
        self.git(path, "commit", "-qam", "ours")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git(path, "merge", "other")
        rows = self.run_audit()
        self.assertEqual(rows[str(path)]["tracked_changes"], 1)
        self.assertEqual(rows[str(path)]["untracked_paths"], 1)


if __name__ == "__main__":
    unittest.main()
