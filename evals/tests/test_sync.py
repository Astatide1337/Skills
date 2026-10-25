"""Resync preserves custom data, is repeatable, and rolls back failed writes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('skills_sync', ROOT / 'scripts/sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def test_instructions_preserve_custom_text_and_update_once(self):
        first = sync.instructions('My custom policy.\n', 'Old managed policy.\n')
        updated = sync.instructions(first + '\nMy other policy.\n', 'New managed policy.\n')
        self.assertIn('My custom policy.', updated)
        self.assertIn('My other policy.', updated)
        self.assertNotIn('Old managed policy.', updated)
        self.assertEqual(updated.count(sync.BEGIN), 1)
        self.assertEqual(sync.instructions(updated, 'New managed policy.\n'), updated)
        with self.assertRaises(ValueError):
            sync.instructions(sync.BEGIN, 'New')

    def test_settings_preserve_subagent_hook_and_custom_values(self):
        old = {'env': {'OTHER': 'keep'}, 'hooks': {'SubagentStop': [{'hooks': [{'type': 'command', 'command': 'custom'}]}]}, 'custom': True}
        example = json.loads((ROOT / 'global-instructions/hooks/claude-settings.example.json').read_text())
        new = sync.settings(old, example, Path('/snapshot'))
        self.assertEqual(new['hooks']['SubagentStop'], old['hooks']['SubagentStop'])
        self.assertEqual(new['env']['OTHER'], 'keep')
        self.assertTrue(new['custom'])
        self.assertNotIn('SKILLS_DIR', old['env'])
        self.assertEqual(sync.settings(new, example, Path('/snapshot')), new)

    def test_apply_readback_backup_and_rollback(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source, target = root / 'source', root / 'target'
            source.write_text('new'); target.write_text('custom old')
            backup = sync.apply([(source, target)], root)
            self.assertEqual(target.read_text(), 'new')
            self.assertEqual((backup / '0').read_text(), 'custom old')
            target.write_text('custom old')
            with patch.object(sync.shutil, 'copy2', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    sync.apply([(source, target)], root)
            self.assertEqual(target.read_text(), 'custom old')

    def test_preview_apply_and_rerun(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            targets = root / 'skills'; targets.mkdir()
            package = targets / 'architect'; package.mkdir(); (package / 'custom').write_text('old')
            unrelated = targets / 'personal'; unrelated.mkdir(); (unrelated / 'SKILL.md').write_text('mine')
            source = root / 'instructions-source'; source.write_text('My portable rules.\n')
            target = root / 'AGENTS.md'; target.write_text('My local rules.\n')
            config = root / 'settings.json'; config.write_text('{"hooks":{"SubagentStop":[]}}')
            argv = ['--target', str(targets), '--claude-settings', str(config), '--instructions', str(source), str(target)]
            with patch.object(sync.Path, 'home', return_value=root):
                before = sync.identity(root)
                self.assertEqual(sync.main(argv), 0)
                self.assertEqual(sync.identity(root), before)
                self.assertEqual(sync.main(argv + ['--apply']), 0)
                self.assertTrue((package / 'SKILL.md').exists())
                self.assertFalse((package / 'custom').exists())
                self.assertFalse((targets / 'verify-work').exists())
                self.assertEqual((unrelated / 'SKILL.md').read_text(), 'mine')
                self.assertIn('My local rules.', target.read_text())
                after = sync.identity(root)
                self.assertEqual(sync.main(argv + ['--apply']), 0)
                self.assertEqual(sync.identity(root), after)

    def test_invalid_input_fails_before_writes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); source = root / 'rules'; source.write_text('new')
            target = root / 'AGENTS.md'; target.write_text(sync.BEGIN)
            before = sync.identity(root)
            with patch.object(sync.Path, 'home', return_value=root), self.assertRaises(ValueError):
                sync.main(['--claude-settings', str(root / 'settings.json'), '--instructions', str(source), str(target), '--apply'])
            self.assertEqual(sync.identity(root), before)
