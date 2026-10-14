"""Exercise preview preparation with real disposable Git histories, no model calls."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare-preview.py"
SPEC = importlib.util.spec_from_file_location("prepare_preview", SCRIPT)
assert SPEC and SPEC.loader
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


class PreviewPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Preview test")
        self.git("config", "user.email", "preview@example.invalid")
        for name, content in {
            "skills/follow-instructions/SKILL.md": "baseline guidance\n",
            "skills/web-interface/assets/example.webp": b"\x00image\xff",
            "scripts/install.sh": "#!/bin/sh\ntouch INSTALLER_WAS_EXECUTED\n",
            "catalog.yaml": "skills: []\n",
            "global-instructions/AGENTS.md": "No production writes.\n",
        }.items():
            self.write(name, content)
        (self.repo / "scripts/install.sh").chmod(0o755)
        self.baseline = self.commit()
        self.write("skills/follow-instructions/SKILL.md", "candidate guidance\n")
        self.write("skills/follow-instructions/references/example.md", "alternative, not mandate\n")
        self.candidate = self.commit()
        self.output = self.root / "comparison"

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", str(self.repo), *args],
            env=env, stderr=subprocess.PIPE,
        ).decode().strip()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def prepare(self):
        return preview.prepare(self.repo, self.candidate, self.baseline, self.output)

    def test_prepares_distinct_complete_snapshots_without_activation(self):
        result = self.prepare()
        self.assertFalse(result["activated"])
        self.assertFalse(result["runtime_verified"])
        for arm, expected in (("baseline", "baseline guidance\n"),
                              ("candidate", "candidate guidance\n")):
            self.assertEqual((self.output / arm / "skills/follow-instructions/SKILL.md").read_text(), expected)
            self.assertEqual((self.output / arm / "skills/web-interface/assets/example.webp").read_bytes(), b"\x00image\xff")
            self.assertTrue(os.access(self.output / arm / "scripts/install.sh", os.X_OK))
        self.assertEqual(preview.verify(self.output)["status"], "matches-manifest")
        self.assertFalse(list(self.root.rglob("INSTALLER_WAS_EXECUTED")))
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_content_deletion_addition_and_mode_drift_are_rejected(self):
        self.prepare()
        path = self.output / "candidate/skills/follow-instructions/SKILL.md"
        original = path.read_bytes()
        for damage in ("edit", "delete", "add", "executable"):
            with self.subTest(damage=damage):
                extra = path.parent / "unexpected.md"
                if damage == "edit":
                    path.write_text("changed")
                elif damage == "delete":
                    path.unlink()
                elif damage == "add":
                    extra.write_text("extra")
                else:
                    path.chmod(0o755)
                with self.assertRaises(preview.PreviewError):
                    preview.verify(self.output)
                path.write_bytes(original)
                path.chmod(0o644)
                extra.unlink(missing_ok=True)
        self.assertEqual(preview.verify(self.output)["status"], "matches-manifest")

    def test_existing_outputs_are_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "user.txt"
        sentinel.write_text("preserve")
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.assertEqual(sentinel.read_text(), "preserve")
        sentinel.unlink()
        self.output.rmdir()
        self.output.write_text("user file")
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.assertEqual(self.output.read_text(), "user file")

    def test_dangling_output_symlink_is_not_followed(self):
        self.output.symlink_to(self.root / "nonexistent", target_is_directory=True)
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.assertTrue(self.output.is_symlink())
        self.assertFalse((self.root / "nonexistent").exists())

    def test_source_and_installed_agent_locations_are_rejected(self):
        with self.assertRaises(preview.PreviewError):
            preview.prepare(self.repo, self.candidate, self.baseline, self.repo / "preview")
        home = self.root / "home"
        home.mkdir()
        (home / ".agents").mkdir()
        with patch.object(preview.Path, "home", return_value=home):
            with self.assertRaises(preview.PreviewError):
                preview.prepare(self.repo, self.candidate, self.baseline, home / ".agents/preview")
        self.assertFalse((home / ".agents/preview").exists())

    def test_relevant_dirty_and_untracked_inputs_are_rejected(self):
        self.write("skills/follow-instructions/SKILL.md", "uncommitted")
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.git("checkout", "--", "skills/follow-instructions/SKILL.md")
        self.write("skills/follow-instructions/new.md", "untracked")
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.assertFalse(self.output.exists())

    def test_missing_required_input_cannot_prepare(self):
        (self.repo / "global-instructions/AGENTS.md").unlink()
        self.candidate = self.commit()
        with self.assertRaisesRegex(preview.PreviewError, "omitted required"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_bad_ref_does_not_create_output(self):
        with self.assertRaises(preview.PreviewError):
            preview.prepare(self.repo, "not-a-ref", self.baseline, self.output)
        self.assertFalse(self.output.exists())

    def test_archive_symlink_is_rejected_and_stage_cleaned(self):
        (self.repo / "skills/follow-instructions/external").symlink_to("/etc/passwd")
        self.candidate = self.commit()
        with self.assertRaises(preview.PreviewError): self.prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".skills-preview-*")))

    def test_export_attributes_cannot_omit_or_rewrite_committed_inputs(self):
        self.write(".gitattributes", "global-instructions/AGENTS.md export-ignore\nskills/** export-subst\n")
        self.write("skills/follow-instructions/references/literal.md", "$Format:%H$\n")
        self.candidate = self.commit()
        self.prepare()
        policy = self.output / "candidate/global-instructions/AGENTS.md"
        self.assertEqual(policy.read_text(), "No production writes.\n")
        literal = self.output / "candidate/skills/follow-instructions/references/literal.md"
        self.assertEqual(literal.read_text(), "$Format:%H$\n")

    def test_interruption_before_publication_leaves_no_output(self):
        original = preview.snapshot
        count = 0
        def interrupt_second(*args):
            nonlocal count
            count += 1
            if count == 2:
                raise KeyboardInterrupt()
            return original(*args)
        with patch.object(preview, "snapshot", side_effect=interrupt_second):
            with self.assertRaises(KeyboardInterrupt): self.prepare()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".skills-preview-*")))

    def test_prepared_snapshots_stay_frozen_when_source_changes(self):
        self.prepare()
        self.write("skills/follow-instructions/SKILL.md", "a later candidate")
        self.commit()
        self.assertEqual(preview.verify(self.output)["status"], "matches-manifest")
        with self.assertRaises(preview.PreviewError): self.prepare()

    def test_verify_rejects_links_missing_manifest_and_invalid_schema(self):
        self.prepare()
        manifest = self.output / "preview.json"
        data = manifest.read_bytes()
        manifest.unlink()
        with self.assertRaises(preview.PreviewError): preview.verify(self.output)
        external = self.root / "external.json"
        external.write_bytes(data)
        manifest.symlink_to(external)
        with self.assertRaises(preview.PreviewError): preview.verify(self.output)
        manifest.unlink()
        manifest.write_text('{"version": 99}')
        with self.assertRaises(preview.PreviewError): preview.verify(self.output)
        manifest.write_bytes(data)
        target = self.output / "candidate/skills/follow-instructions/SKILL.md"
        target.unlink()
        target.symlink_to(external)
        with self.assertRaises(preview.PreviewError): preview.verify(self.output)

    def test_archive_paths_must_stay_in_the_selected_contract(self):
        for path in ("../x", "/root/x", "skills/../../x", "evals/answer-key", "skills\\x"):
            with self.subTest(path=path), self.assertRaises(preview.PreviewError):
                preview.safe_relative(path)

    def test_cli_success_and_failure_exit_codes(self):
        command = [sys.executable, str(SCRIPT), "prepare", "--repo", str(self.repo),
                   "--baseline", self.baseline, "--candidate", self.candidate,
                   "--output", str(self.output)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["candidate"], self.candidate)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["status"], "failed")
        result = subprocess.run([sys.executable, str(SCRIPT), "verify", str(self.output)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["runtime_verified"])


if __name__ == "__main__":
    unittest.main()
