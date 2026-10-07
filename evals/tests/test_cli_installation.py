"""Immutable local CLI receipt boundaries; the real install is exercised separately."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import tarfile
import io
import shutil
import unittest

spec = importlib.util.spec_from_file_location("cli_install", Path(__file__).resolve().parents[2] / "scripts/install-agent-clis.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CLIReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.prefix = Path(self.directory.name) / "installed"
        self.files = {}
        for path in ("node_modules/@agent-clis/core/package.json", "node_modules/@agent-clis/linktree/dist/cli.js"):
            target = self.prefix / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("original")
            self.files[path] = hashlib.sha256(target.read_bytes()).hexdigest()

    def test_intact_receipt_accepts_but_changed_cli_rejects(self):
        installer.validate_receipt(self.prefix, {"installed_files": self.files})
        (self.prefix / "node_modules/@agent-clis/linktree/dist/cli.js").write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            installer.validate_receipt(self.prefix, {"installed_files": self.files})

    def test_empty_receipt_cannot_skip_identity_checks(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            installer.validate_receipt(self.prefix, {"installed_files": {}})

    def test_unfinished_launcher_cannot_be_reported_installed(self):
        launcher = Path(self.directory.name) / "linktree-agent"
        launcher.write_text("#!/usr/bin/env bash\nexit 0\n")
        launcher.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            installer.validate_launcher(launcher, launcher.read_text())
        launcher.chmod(0o755)
        installer.validate_launcher(launcher, launcher.read_text())

    def test_skills_source_alias_is_rejected_without_deleting_source(self):
        repo = Path(self.directory.name) / "skills-repo"
        (repo / "scripts").mkdir(parents=True)
        source = repo / "skills/example/SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text("original skill")
        shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts/install.sh",
                        repo / "scripts/install.sh")
        alias = Path(self.directory.name) / "alias"
        alias.symlink_to(repo / "skills", target_is_directory=True)
        result = subprocess.run(["bash", str(repo / "scripts/install.sh"),
                                 "--skill", "example", "--target", str(alias)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("source skill tree", result.stderr)
        self.assertEqual(source.read_text(), "original skill")

    def test_outside_path_is_rejected_before_any_read(self):
        for path in ("/definitely-not-present", "node_modules/@agent-clis/core/../../../../outside", "node_modules/other/file"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "invalid"):
                installer.validate_receipt(self.prefix, {"installed_files": {**self.files, path: "0" * 64}})

    def test_symlink_escape_is_rejected(self):
        target = self.prefix / "node_modules/@agent-clis/linktree/dist/cli.js"
        target.unlink()
        target.symlink_to(Path(self.directory.name) / "outside-not-present")
        with self.assertRaisesRegex(ValueError, "escapes"):
            installer.validate_receipt(self.prefix, {"installed_files": self.files})

    def test_git_replacement_cannot_substitute_pinned_source(self):
        repo = Path(self.directory.name) / "source"
        repo.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(repo), *args], check=True,
                                  capture_output=True).stdout.strip()
        git("init", "-q")
        for value in ("reviewed", "replacement"):
            (repo / "source.txt").write_text(value)
            git("add", "source.txt")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", value)
            if value == "reviewed":
                pinned = git("rev-parse", "HEAD").decode()
        git("replace", pinned, git("rev-parse", "HEAD").decode())
        substituted = git("show", pinned + ":source.txt")
        self.assertEqual(substituted, b"replacement")
        archive = subprocess.run(installer.git_args(repo, "archive", pinned),
                                 check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
            self.assertEqual(contents.extractfile("source.txt").read(), b"reviewed")
