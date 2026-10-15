"""Disposable installation boundaries; native CLI manifests stay with their owner."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class InstallationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_selected_review_install_closes_its_helper_dependency(self):
        root = Path(__file__).resolve().parents[2]
        target = self.root / 'selected-skills'
        result = subprocess.run(['bash', str(root / 'scripts/install.sh'), '--skill',
                                 'code-review-and-quality', '--target', str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('including required dependency: verify-work', result.stdout)
        self.assertTrue((target / 'verify-work/scripts/check_profile.py').is_file())
        script = target / 'code-review-and-quality/scripts/portable_lint.py'
        help_result = subprocess.run([os.sys.executable, str(script), '--help'],
                                     capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)

        app = self.root / 'installed-app'
        app.mkdir()
        source = 'print(undefined_name)  # noqa: F821\n'
        (app / 'sample.py').write_text(source)
        receipt = self.root / 'installed-lint.json'
        from evals.tests.test_portable_lint import integration_runtime
        runtime = integration_runtime('python')
        result = subprocess.run([os.sys.executable, str(script), '--workspace', str(app),
                                 '--language', 'python', '--runtime', str(runtime), '--receipt', str(receipt), 'sample.py'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 3, result.stderr)
        evidence = json.loads(receipt.read_text())
        self.assertTrue(evidence['diagnostics_available'])
        self.assertEqual(evidence['diagnostics'][0]['rule'], 'F821')
        self.assertEqual((app / 'sample.py').read_text(), source)

    def test_custom_dependency_is_preserved_until_explicitly_selected(self):
        root = Path(__file__).resolve().parents[2]
        target = self.root / 'custom-skills'
        helper = target / 'verify-work/scripts/check_profile.py'
        helper.parent.mkdir(parents=True)
        helper.write_text('custom helper\n')
        result = subprocess.run(['bash', str(root / 'scripts/install.sh'), '--skill',
                                 'code-review-and-quality', '--target', str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('incompatible', result.stderr)
        self.assertEqual(helper.read_text(), 'custom helper\n')
        self.assertFalse((target / 'code-review-and-quality').exists())

    def test_review_help_works_without_sibling_and_run_records_gap(self):
        root = Path(__file__).resolve().parents[2]
        script = self.root / 'skills/code-review-and-quality/scripts/portable_lint.py'
        script.parent.mkdir(parents=True)
        shutil.copyfile(root / 'skills/code-review-and-quality/scripts/portable_lint.py', script)
        help_result = subprocess.run([os.sys.executable, str(script), '--help'],
                                     capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        app = self.root / 'app'; app.mkdir(); (app / 'sample.py').write_text('x = 1\n')
        receipt = self.root / 'gap.json'
        result = subprocess.run([os.sys.executable, str(script), '--workspace', str(app),
                                 '--language', 'python', '--receipt', str(receipt), 'sample.py'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 3, result.stderr)
        evidence = json.loads(receipt.read_text())
        self.assertFalse(evidence['passed'])
        self.assertIn('verify-work helper', evidence['unavailable'])

    def install(self, *arguments):
        return subprocess.run(['bash', str(ROOT / 'scripts/install.sh'), *arguments],
                              capture_output=True, text=True)

    def retired_package(self, revision='233fb741431a41b22e865d9baaedf62a90bface9'):
        target = self.root / 'skills'
        fixture = ROOT / 'evals/tests/fixtures' / f'retired-internet-reach-{revision[:8]}.tar.gz'
        with tarfile.open(fixture) as archive:
            archive.extractall(self.root, filter='data')
        return target

    def test_retirement_accepts_known_packages_and_is_idempotent(self):
        for revision in ('8f2d963060ceed152168817ab6cc067a0106bdea',
                         '233fb741431a41b22e865d9baaedf62a90bface9'):
            target = self.retired_package(revision)
            unrelated = target / 'my-custom-skill'
            unrelated.mkdir(exist_ok=True)
            (unrelated / 'SKILL.md').write_text('private unchanged content')
            result = self.install('--retire', 'internet-reach', '--target', str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(revision, result.stdout)
            self.assertFalse((target / 'internet-reach').exists())
            self.assertEqual((unrelated / 'SKILL.md').read_text(), 'private unchanged content')
            repeated = self.install('--retire', 'internet-reach', '--target', str(target))
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertIn('already absent', repeated.stdout)

    def test_retirement_preserves_custom_unknown_and_symlinked_content(self):
        for mutation in ('edit', 'extra-file', 'extra-dir', 'symlink', 'package-symlink'):
            with self.subTest(mutation=mutation):
                target = self.retired_package()
                package = target / 'internet-reach'
                if mutation == 'edit':
                    (package / 'SKILL.md').write_text('local customization')
                elif mutation == 'extra-file':
                    (package / 'notes.txt').write_text('local notes')
                elif mutation == 'extra-dir':
                    (package / 'custom').mkdir()
                elif mutation == 'symlink':
                    (package / 'external').symlink_to(self.root / 'private')
                else:
                    moved = self.root / 'preserved-original'
                    package.rename(moved)
                    package.symlink_to(moved, target_is_directory=True)
                result = self.install('--retire', 'internet-reach', '--target', str(target))
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(package.exists())
                if package.is_symlink():
                    package.unlink()
                    shutil.rmtree(moved)
                else:
                    shutil.rmtree(package)

    def test_retirement_requires_explicit_target_and_rejects_other_operations(self):
        for args in (('--retire', 'internet-reach'),
                     ('--retire', 'internet-reach', '--target', str(self.root), '--all'),
                     ('--retire', 'internet-reach', '--target', str(self.root), '--list'),
                     ('--retire', 'verify-work', '--target', str(self.root)),
                     ('--retire', 'internet-reach', '--target', '/'),
                     ('--retire', 'internet-reach', '--target', str(Path.home())),
                     ('--retire', 'internet-reach', '--target', str(ROOT / 'skills'))):
            with self.subTest(args=args):
                self.assertNotEqual(self.install(*args).returncode, 0)

    def test_normal_selected_install_never_prunes_retired_or_unrelated_packages(self):
        target = self.retired_package()
        before = (target / 'internet-reach/SKILL.md').read_bytes()
        result = self.install('--skill', 'verify-work', '--target', str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'internet-reach/SKILL.md').read_bytes(), before)
        self.assertTrue((target / 'verify-work/SKILL.md').is_file())
        self.assertNotIn('internet-reach', self.install('--list').stdout)
        # CLI installation belongs to the CLI project; obsolete coupling rejects.
        result = self.install('--skill', 'verify-work', '--target', str(target),
                              '--agent-clis-source', '/not/a/source')
        self.assertEqual(result.returncode, 2)
