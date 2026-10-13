"""Local skill lifecycle and recovery tests; no global targets."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('skill_install', ROOT / 'scripts/skill_install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SkillInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'installed'
        self.source = self.root / 'repo'
        (self.source / 'skills').mkdir(parents=True)
        self.patch = patch.object(installer, 'ROOT', self.source)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.write_skill('example', 'first')

    def write_skill(self, name, text):
        folder = self.source / 'skills' / name
        folder.mkdir(exist_ok=True)
        (folder / 'SKILL.md').write_text(text)

    def run_install(self, *args):
        with patch('sys.argv', ['install', '--target', str(self.target), *args]):
            installer.main()

    def test_install_update_idempotence_and_rollback(self):
        self.run_install('--skill', 'example')
        first = (self.target / installer.RECEIPT).read_bytes()
        self.run_install('--skill', 'example')
        self.assertEqual(first, (self.target / installer.RECEIPT).read_bytes())
        self.write_skill('example', 'second')
        self.run_install('--skill', 'example')
        self.run_install('--rollback')
        self.assertEqual((self.target / 'example/SKILL.md').read_text(), 'first')
        self.run_install('--uninstall', '--skill', 'example')
        self.assertFalse((self.target / 'example').exists())
        self.run_install('--rollback')
        self.assertEqual((self.target / 'example/SKILL.md').read_text(), 'first')

    def test_divergent_and_unowned_preserved(self):
        self.run_install('--skill', 'example')
        (self.target / 'example/SKILL.md').write_text('local edit')
        for options in [('--skill', 'example'), ('--uninstall', '--skill', 'example'), ('--rollback',)]:
            with self.assertRaisesRegex(ValueError, 'divergent'):
                self.run_install(*options)
        self.run_install('--skill', 'example', '--preserve-existing')
        receipt = json.loads((self.target / installer.RECEIPT).read_text())
        backup = Path(receipt['last_transaction']['backup'])
        self.assertEqual((backup / 'example/SKILL.md').read_text(), 'local edit')

    def test_full_staging_before_mutation(self):
        self.write_skill('broken', '')
        with self.assertRaisesRegex(ValueError, 'Empty'):
            self.run_install('--all')
        self.assertFalse(self.target.exists())

    def test_multi_package_failure_restores_prior_install(self):
        self.run_install('--skill', 'example')
        old = (self.target / installer.RECEIPT).read_bytes()
        self.write_skill('example', 'second')
        self.write_skill('other', 'other')
        real_copy = installer.shutil.copytree
        def copy(source, destination, **kwargs):
            if Path(destination) == self.target / 'other':
                Path(destination).mkdir()
                raise OSError('simulated copy failure')
            return real_copy(source, destination, **kwargs)
        with patch.object(installer.shutil, 'copytree', side_effect=copy), self.assertRaisesRegex(OSError, 'simulated'):
            self.run_install('--all')
        self.assertEqual((self.target / 'example/SKILL.md').read_text(), 'first')
        self.assertFalse((self.target / 'other').exists())
        self.assertEqual((self.target / installer.RECEIPT).read_bytes(), old)

    def test_target_alias_ancestor_and_package_symlinks_rejected(self):
        alias = self.root / 'alias'; alias.symlink_to(self.source / 'skills')
        for target in [alias, self.source, self.source / 'skills/example']:
            with self.assertRaises(ValueError):
                installer.safe_target(str(target))
        (self.source / 'skills/example/link').symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.run_install('--all')
        self.assertFalse(self.target.exists())

    def test_guidance_dependencies_close_without_route_table_fanout(self):
        self.write_skill('teach', 'Explain with ../follow-instructions/SKILL.md')
        self.write_skill('how', 'Trace')
        self.write_skill('why', 'Rationale')
        self.write_skill('follow-instructions', 'Optional ../example/SKILL.md')
        self.run_install('--skill', 'teach')
        packages = json.loads((self.target / installer.RECEIPT).read_text())['packages']
        self.assertEqual(set(packages), {'teach', 'how', 'why', 'follow-instructions'})

    def test_uninstall_preserves_installed_dependency_graph(self):
        for name, text in [('teach', '../follow-instructions/SKILL.md'), ('how', 'Trace'),
                           ('why', 'Rationale'), ('follow-instructions', 'Route'),
                           ('code-review-and-quality', 'Review'), ('verify-work', 'Verify')]:
            self.write_skill(name, text)
        self.run_install('--skill', 'teach', '--skill', 'code-review-and-quality')
        for name in ['how', 'verify-work', 'follow-instructions']:
            with self.assertRaisesRegex(ValueError, 'requires'):
                self.run_install('--uninstall', '--skill', name)
            self.assertTrue((self.target / name).exists())
        self.run_install('--uninstall', '--skill', 'teach', '--skill', 'why', '--skill', 'how', '--skill', 'follow-instructions')
        self.assertTrue((self.target / 'code-review-and-quality').exists())
        self.run_install('--uninstall', '--all')
        self.assertEqual(json.loads((self.target / installer.RECEIPT).read_text())['packages'], {})

    def test_receipt_failure_restores_files_and_removes_temporary(self):
        self.run_install('--skill', 'example')
        previous = (self.target / installer.RECEIPT).read_bytes()
        self.write_skill('example', 'second')
        with patch.object(installer, 'replace_receipt', side_effect=OSError('receipt failure')), self.assertRaisesRegex(OSError, 'receipt failure'):
            self.run_install('--skill', 'example')
        self.assertEqual((self.target / 'example/SKILL.md').read_text(), 'first')
        self.assertEqual((self.target / installer.RECEIPT).read_bytes(), previous)

    def test_no_implicit_target_and_no_bytecode(self):
        with patch('sys.argv', ['install', '--all']), self.assertRaisesRegex(ValueError, '--target'):
            installer.main()
        cache = self.source / 'skills/example/__pycache__'; cache.mkdir()
        (cache / 'junk.pyc').write_text('junk')
        self.run_install('--all')
        self.assertFalse((self.target / 'example/__pycache__').exists())


if __name__ == '__main__':
    unittest.main()
