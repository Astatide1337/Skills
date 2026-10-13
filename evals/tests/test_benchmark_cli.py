import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "benchmark_cli", ROOT / "scripts/benchmark-cli.py"
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class BenchmarkCLI(unittest.TestCase):
    def test_flags_discoverable(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/benchmark-cli.py"), "plan", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        for flag in ["--old-skills", "--new-skills", "--model", "--effort", "--task"]:
            self.assertIn(flag, result.stdout)

    def test_auth_file_selection_unset_in_command(self):
        argv = cli.command()
        self.assertEqual(
            argv[:5],
            ["env", "-u", "CODEX_AUTH_JSON_PATH", "-u", "CODEX_FORCE_AUTH_JSON"],
        )

    def test_pinned_sources(self):
        manifest = cli.load_manifest()
        self.assertEqual(manifest["runner"]["version"], "0.24.0")
        for dataset in manifest["datasets"]:
            self.assertLessEqual(len(dataset["tasks"]), 4)
            for task in dataset["tasks"]:
                self.assertEqual(len(task["git_commit_id"]), 40)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "real").write_text("x")
            (root / "alias").symlink_to(root / "real")
            with self.assertRaises(ValueError):
                cli.digest(root)

    def test_output_refused_outside_ignored_paths(self):
        with self.assertRaises(ValueError):
            cli.output_path(ROOT / "reports/new-report")

    def test_existing_output_refused(self):
        with self.assertRaises(ValueError):
            cli.output_path(ROOT / "evals/results")

    def test_paired_frozen_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for arm in ["old", "new"]:
                skill = root / arm / "example"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(arm)
            globals_path = root / "AGENTS.md"
            globals_path.write_text("shared rules")
            args = argparse.Namespace(
                dataset="terminal-bench",
                task=["adaptive-rejection-sampler"],
                old_skills=str(root / "old"),
                new_skills=str(root / "new"),
                globals=str(globals_path),
                output=str(root / "plan"),
                model="literal; $(no shell)",
                effort="low",
                attempts=2,
                timeout=600,
            )
            with patch.object(cli, "output_path", return_value=root / "plan"):
                result = cli.plan(args)
            self.assertEqual(result["candidate_calls"], 4)
            old = json.loads((root / "plan/old.json").read_text())
            new = json.loads((root / "plan/new.json").read_text())
            self.assertEqual(old["agents"][0]["kwargs"], new["agents"][0]["kwargs"])
            self.assertEqual(old["agents"][0]["model_name"], args.model)
            self.assertEqual(old["environment"]["type"], "docker")
            (root / "old/example/SKILL.md").write_text("changed")
            self.assertEqual(
                (root / "plan/old/skills/example/SKILL.md").read_text(), "old"
            )
            self.assertFalse(list((root / "plan").rglob("auth.json")))
            self.assertIsInstance(result["runs"][0]["argv"], list)

    def test_unknown_task_refused_before_writes(self):
        args = argparse.Namespace(dataset="terminal-bench", task=["unknown"])
        with self.assertRaises(ValueError):
            cli.plan(args)

class CatalogAblationTests(unittest.TestCase):
    def test_removes_only_frozen_component_preserves_source_and_globals(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; source.mkdir()
            for name in ["review", "router"]:
                (source / name).mkdir()
                (source / name / "SKILL.md").write_text(name)
                (source / name / "reference.py").write_text("content")
            globals_path = base / "AGENTS.md"; globals_path.write_text("shared rules")
            output = base / "frozen"
            args = argparse.Namespace(skills_root=str(source), component="review",
                globals=str(globals_path), output=str(output))
            before = cli.digest(source)
            with patch.object(cli, "output_path", return_value=output):
                result = cli.ablate(args)
            self.assertEqual(cli.digest(source), before)
            self.assertEqual(cli.digest(Path(result["full_skills_root"])), before)
            self.assertFalse((Path(result["ablated_skills_root"]) / "review").exists())
            self.assertEqual((Path(result["ablated_skills_root"]) / "router/SKILL.md").read_text(), "router")
            self.assertEqual(Path(result["global_instructions"]).read_text(), "shared rules")
            self.assertEqual(json.loads((output / "ablation.json").read_text())["status"], "frozen-not-executed")

    def test_rejects_component_traversal_and_source_links_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; (source / "review").mkdir(parents=True)
            (source / "review/SKILL.md").write_text("review")
            globals_path = base / "AGENTS.md"; globals_path.write_text("shared")
            args = argparse.Namespace(skills_root=str(source), component="../review", globals=str(globals_path), output=str(base / "out"))
            with self.assertRaises(ValueError): cli.ablate(args)
            args.component = "review"
            (source / "review/outside").symlink_to(globals_path)
            with self.assertRaises(ValueError): cli.ablate(args)
            self.assertFalse((base / "out").exists())


if __name__ == "__main__":
    unittest.main()
