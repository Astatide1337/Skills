"""Immutable local CLI receipt boundaries and the optional real package install."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "cli_install", Path(__file__).resolve().parents[2] / "scripts/install-agent-clis.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CLIReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.prefix = self.root / "installed"
        self.write_installed_package_fixtures()
        self.files = installer.installed_file_digests(self.prefix)
        self.receipt = {
            "schema": 1,
            "source_revision": installer.REVISION,
            "packages": installer.expected_package_receipt(),
            "installed_files": self.files,
            "artifacts": {name: "a" * 64 for name in installer.PACKAGES_BY_NAME},
        }

    def write_installed_package_fixtures(self):
        packages_root = self.prefix / "node_modules/@agent-clis"
        for package in installer.PACKAGE_CONTRACTS:
            package_root = packages_root / package["directory"]
            package_root.mkdir(parents=True, exist_ok=True)
            manifest = {
                "name": package["name"],
                "version": package["version"],
                "private": True,
                "bin": package["bin"],
                "dependencies": dict(package["dependencies"]),
            }
            if "exports" in package:
                manifest["exports"] = package["exports"]
            if package["name"] == "@agent-clis/linktree":
                manifest["dependencies"]["playwright"] = "1.62.1"
            if package["name"] == "@agent-clis/core":
                manifest["dependencies"]["playwright"] = "1.62.1"
            (package_root / "package.json").write_text(json.dumps(manifest))
            for relative in package["required_files"]:
                target = package_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"fixture for {package['name']} {relative}")
        bin_dir = self.prefix / "node_modules/.bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        for package in installer.PACKAGE_CONTRACTS:
            package_root = packages_root / package["directory"]
            for name, relative in package["bin"].items():
                (bin_dir / name).symlink_to(package_root / relative)

    def test_intact_receipt_accepts_but_changed_cli_rejects(self):
        installer.validate_receipt(self.prefix, self.receipt)
        target = self.prefix / "node_modules/@agent-clis/linktree/dist/cli.js"
        target.write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            installer.validate_receipt(self.prefix, self.receipt)

    def test_empty_receipt_cannot_skip_identity_checks(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["installed_files"] = {}
        with self.assertRaisesRegex(ValueError, "incomplete"):
            installer.validate_receipt(self.prefix, receipt)

    def test_receipt_must_include_shrunk_package_files(self):
        receipt = copy.deepcopy(self.receipt)
        receipt["installed_files"].pop(
            "node_modules/@agent-clis/shrunk-cli/support/bootstrap.py"
        )
        with self.assertRaisesRegex(ValueError, "incomplete"):
            installer.validate_receipt(self.prefix, receipt)

    def test_missing_shrunk_package_is_rejected(self):
        shutil.rmtree(self.prefix / "node_modules/@agent-clis/shrunk-cli")
        with self.assertRaisesRegex(ValueError, "@agent-clis/shrunk-cli"):
            installer.validate_receipt(self.prefix, self.receipt)

    def test_linktree_must_depend_on_the_pinned_shrunk_package(self):
        manifest_path = self.prefix / "node_modules/@agent-clis/linktree/package.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["dependencies"].pop("@agent-clis/shrunk-cli")
        manifest_path.write_text(json.dumps(manifest))
        self.receipt["installed_files"][str(manifest_path.relative_to(self.prefix))] = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        )
        with self.assertRaisesRegex(ValueError, "required dependency @agent-clis/shrunk-cli"):
            installer.validate_receipt(self.prefix, self.receipt)

    def test_shrunk_package_must_export_the_linktree_entrypoint(self):
        manifest_path = self.prefix / "node_modules/@agent-clis/shrunk-cli/package.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["exports"] = {}
        manifest_path.write_text(json.dumps(manifest))
        self.receipt["installed_files"][str(manifest_path.relative_to(self.prefix))] = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        )
        with self.assertRaisesRegex(ValueError, "unexpected package exports in @agent-clis/shrunk-cli"):
            installer.validate_receipt(self.prefix, self.receipt)

    def test_receipt_rejects_stale_source_and_incomplete_artifact_set(self):
        stale = copy.deepcopy(self.receipt)
        stale["source_revision"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "differs"):
            installer.validate_receipt(self.prefix, stale)
        incomplete = copy.deepcopy(self.receipt)
        incomplete["artifacts"].pop("@agent-clis/shrunk-cli")
        with self.assertRaisesRegex(ValueError, "artifact set"):
            installer.validate_receipt(self.prefix, incomplete)

    def test_receipt_rejects_boolean_schema_and_non_string_paths(self):
        boolean_schema = copy.deepcopy(self.receipt)
        boolean_schema["schema"] = True
        with self.assertRaisesRegex(ValueError, "receipt"):
            installer.validate_receipt(self.prefix, boolean_schema)
        non_string_path = copy.deepcopy(self.receipt)
        non_string_path["installed_files"][7] = "0" * 64
        with self.assertRaisesRegex(ValueError, "invalid installed-file identity"):
            installer.validate_receipt(self.prefix, non_string_path)

    def test_both_launchers_must_be_executable_and_match_the_prefix(self):
        for name, relative in (
            ("linktree-agent", "node_modules/@agent-clis/linktree/dist/cli.js"),
            ("shrunk-agent", "node_modules/@agent-clis/shrunk-cli/src/cli.mjs"),
        ):
            with self.subTest(name=name):
                launcher = self.root / name
                wrapper = "#!/usr/bin/env bash\nexec node " + str(self.prefix / relative) + ' "$@"\n'
                launcher.write_text(wrapper)
                launcher.chmod(0o644)
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    installer.validate_launcher(launcher, wrapper)
                launcher.chmod(0o755)
                installer.validate_launcher(launcher, wrapper)

    def test_installed_bin_must_resolve_to_the_declared_shrunk_entrypoint(self):
        link = self.prefix / "node_modules/.bin/shrunk-agent"
        link.unlink()
        link.write_text("#!/bin/sh\nexit 0\n")
        link.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "incorrect installed executable shrunk-agent"):
            installer.validate_installed_packages(self.prefix)

    def test_invalid_receipt_paths_are_rejected(self):
        for path in (
            "/definitely-not-present",
            "node_modules/@agent-clis/core/../../../../outside",
            "node_modules/other/file",
        ):
            with self.subTest(path=path):
                receipt = copy.deepcopy(self.receipt)
                receipt["installed_files"][path] = "0" * 64
                with self.assertRaisesRegex(ValueError, "invalid"):
                    installer.validate_receipt(self.prefix, receipt)

    def test_symlink_escape_is_rejected(self):
        target = self.prefix / "node_modules/@agent-clis/linktree/dist/cli.js"
        target.unlink()
        outside = self.root / "outside"
        outside.write_text("outside")
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escapes"):
            installer.validate_receipt(self.prefix, self.receipt)

    def test_skills_source_alias_is_rejected_without_deleting_source(self):
        repo = self.root / "skills-repo"
        (repo / "scripts").mkdir(parents=True)
        source = repo / "skills/example/SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text("original skill")
        shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts/install.sh",
                        repo / "scripts/install.sh")
        alias = self.root / "alias"
        alias.symlink_to(repo / "skills", target_is_directory=True)
        result = subprocess.run(["bash", str(repo / "scripts/install.sh"),
                                 "--skill", "example", "--target", str(alias)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("source skill tree", result.stderr)
        self.assertEqual(source.read_text(), "original skill")

    def test_git_replacement_cannot_substitute_pinned_source(self):
        repo = self.root / "source"
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


@unittest.skipUnless(os.environ.get("AGENT_CLIS_SOURCE"), "set AGENT_CLIS_SOURCE to run the real local package installation")
class RealCLIInstallTests(unittest.TestCase):
    def test_installs_both_executables_with_the_required_dependency(self):
        source = Path(os.environ["AGENT_CLIS_SOURCE"]).resolve()
        root = Path(tempfile.mkdtemp(prefix="skills-real-cli-install-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        prefix = root / "prefix"
        bin_dir = root / "bin"

        linktree = installer.install(source, prefix, bin_dir)
        shrunk = bin_dir / "shrunk-agent"
        self.assertEqual(linktree, bin_dir / "linktree-agent")
        self.assertTrue(shrunk.is_file())
        receipt = json.loads((prefix / "install-receipt.json").read_text())
        self.assertEqual(receipt["source_revision"], installer.REVISION)
        self.assertEqual(set(receipt["packages"]), {"core", "shrunk-cli", "linktree"})
        self.assertEqual(
            json.loads((prefix / "node_modules/@agent-clis/linktree/package.json").read_text())
            ["dependencies"]["@agent-clis/shrunk-cli"],
            "0.1.0",
        )
        resolved_shrunk_cli = subprocess.run(
            ["node", "-e", "console.log(require.resolve('@agent-clis/shrunk-cli/cli'))"],
            cwd=prefix,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(
            Path(resolved_shrunk_cli),
            prefix / "node_modules/@agent-clis/shrunk-cli/src/cli.mjs",
        )

        commands = json.loads(subprocess.run(
            [str(linktree), "commands", "--json"], check=True, capture_output=True, text=True
        ).stdout)
        self.assertIsInstance(commands, list)
        self.assertTrue(commands)
        shrunk_result = subprocess.run([str(shrunk)], capture_output=True, text=True)
        self.assertNotEqual(shrunk_result.returncode, 0)
        self.assertIn("usage: shrunk-agent start", shrunk_result.stderr)

        self.assertEqual(installer.install(source, prefix, bin_dir), linktree)
        shutil.rmtree(prefix / "node_modules/@agent-clis/shrunk-cli")
        with self.assertRaisesRegex(ValueError, "@agent-clis/shrunk-cli"):
            installer.install(source, prefix, bin_dir)
        run_dir = root / "run-missing-shrunk"
        missing = subprocess.run(
            [str(linktree), "start", "--app", str(root / "missing-app"), "--mongod",
             str(root / "missing-mongod"), "--run-dir", str(run_dir)],
            capture_output=True,
            text=True,
        )
        missing_output = missing.stdout + missing.stderr
        self.assertEqual(missing.returncode, 4, missing_output)
        self.assertIn("required dependency @agent-clis/shrunk-cli is missing", missing_output)
        self.assertFalse(run_dir.exists())
