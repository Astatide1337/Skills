"""Real file/subprocess contract controls, not application efficacy evidence."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from evals.interruption import interrupt

ROOT = Path(__file__).resolve().parents[2]


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


profile = load("skills/verify-work/scripts/check_profile.py")
checkpoint = load("skills/follow-instructions/scripts/checkpoint.py")
boundary = load("skills/verify-work/scripts/boundary_checks.py")


class PortableToolsTests(unittest.TestCase):
    def git_workspace(self, root):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "package.json").write_text("{}")
        (root / "logic.py").write_text("VALUE = 1\n")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c",
                        "user.email=test@example.invalid", "commit", "-qm", "baseline"], check=True)

    def receipt_profile(self, code="", **options):
        return {"version": 1, "source_paths": ["package.json"],
                "workspace_identity": options,
                "steps": [{"id": "check", "phase": "drive", "timeout": 2,
                           "argv": [sys.executable, "-c", "from pathlib import Path; " + code + "print('{\"ok\":true}')"],
                           "expect": {"/ok": True}}]}

    def test_undeclared_tracked_and_dirty_source_changes_reject(self):
        for dirty in (False, True):
            with self.subTest(dirty=dirty), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); self.git_workspace(root)
                if dirty:
                    (root / "logic.py").write_text("VALUE = 2\n")
                spec = self.receipt_profile("Path('logic.py').write_text('VALUE = 3\\n'); ")
                result = profile.run(spec, root)
                self.assertFalse(result["passed"])
                self.assertIn("logic.py", result["workspace_before"]["sources"])

    def test_index_only_change_rejects_and_dirty_start_is_supported(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); self.git_workspace(root)
            (root / "logic.py").write_text("VALUE = 2\n")
            spec = self.receipt_profile()
            clean = profile.run(spec, root)
            self.assertTrue(clean["passed"])
            self.assertTrue(profile.check_freshness(clean, spec, root)["fresh"])
            subprocess.run(["git", "-C", raw, "add", "logic.py"], check=True)
            self.assertFalse(profile.check_freshness(clean, spec, root)["fresh"])
            staged = profile.run(spec, root)
            self.assertTrue(staged["passed"])
            (root / "logic.py").write_text("VALUE = 4\n")
            self.assertFalse(profile.check_freshness(staged, spec, root)["fresh"])

    def test_broken_git_discovery_never_silently_downgrades(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'package.json').write_text('{}')
            (root / '.git').write_text('gitdir: /definitely/missing/repository\n')
            spec = self.receipt_profile("Path('logic.py').write_text('changed'); ")
            with self.assertRaisesRegex(ValueError, 'Git discovery failed'):
                profile.run(spec, root)
            self.assertFalse((root / 'logic.py').exists())
            spec['workspace_identity']['mode'] = 'artifact'
            bounded = profile.run(spec, root)
            self.assertTrue(bounded['passed'])
            self.assertEqual(bounded['workspace_after']['mode'], 'artifact')

    def test_executable_mode_change_fails_run_and_freshness(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); self.git_workspace(root)
            spec = self.receipt_profile()
            receipt = profile.run(spec, root)
            self.assertTrue(receipt['passed'])
            (root / 'logic.py').chmod(0o755)
            self.assertFalse(profile.check_freshness(receipt, spec, root)['fresh'])
            changed = profile.run(self.receipt_profile("Path('logic.py').chmod(0o644); "), root)
            self.assertFalse(changed['passed'])

    def test_new_and_existing_untracked_sources_reject(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); self.git_workspace(root)
                if existing:
                    (root / "helper.py").write_text("VALUE = 1\n")
                result = profile.run(self.receipt_profile("Path('helper.py').write_text('VALUE = 2\\n'); "), root)
                self.assertFalse(result["passed"])

    def test_generated_untracked_output_supported_but_tracked_source_not_excluded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); self.git_workspace(root)
            spec = self.receipt_profile("Path('generated').mkdir(exist_ok=True); Path('generated/bundle.js').write_text('output'); ",
                                       generated_paths=["generated", "logic.py"])
            self.assertTrue(profile.run(spec, root)["passed"])
            spec["steps"][0]["argv"][-1] = "from pathlib import Path; Path('logic.py').write_text('changed'); print('{\"ok\":true}')"
            self.assertFalse(profile.run(spec, root)["passed"])
            spec["workspace_identity"]["generated_paths"] = ["package.json"]
            with self.assertRaisesRegex(ValueError, "declared sources"):
                profile.run(spec, root)

    def test_artifact_modes_and_old_failed_or_profile_changed_receipts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / "package.json").write_text("{}")
            spec = self.receipt_profile(mode="artifact")
            receipt = profile.run(spec, root)
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["workspace_after"]["mode"], "artifact")
            self.assertTrue(profile.check_freshness(receipt, spec, root)["fresh"])
            for bad in ({**receipt, "version": 1}, {**receipt, "passed": False}):
                self.assertFalse(profile.check_freshness(bad, spec, root)["fresh"])
            spec["steps"][0]["expect"]["/ok"] = False
            self.assertFalse(profile.check_freshness(receipt, spec, root)["fresh"])
            spec["workspace_identity"] = {"mode": "git"}
            with self.assertRaisesRegex(ValueError, "repository root"):
                profile.run(spec, root)
            self.git_workspace(root)
            spec = self.receipt_profile(mode="artifact")
            receipt = profile.run(spec, root)
            self.assertEqual(receipt["workspace_after"]["coverage"], "declared source_paths only")

    def test_auto_git_discovery_ignores_an_inherited_checkout_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.git_workspace(root)
            spec = self.receipt_profile()
            inherited = {
                "GIT_DIR": str(ROOT / ".git"),
                "GIT_WORK_TREE": str(ROOT),
                "GIT_INDEX_FILE": str(ROOT / ".git" / "index"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_VALUE_0": str(ROOT),
            }
            from unittest.mock import patch
            with patch.dict(os.environ, inherited, clear=False):
                receipt = profile.run(spec, root)
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["workspace_after"]["mode"], "git")
            self.assertEqual(
                receipt["workspace_after"]["revision"],
                subprocess.run(
                    ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                    check=True, capture_output=True, text=True,
                ).stdout.strip(),
            )

    def test_receipt_cli_ignores_an_inherited_checkout_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app = root / "app"
            app.mkdir()
            self.git_workspace(app)
            config = {
                "version": 1,
                "source_paths": ["package.json"],
                "steps": [{
                    "id": "check",
                    "phase": "drive",
                    "argv": [sys.executable, "-c", "print('{\"ok\":true}')"],
                    "timeout": 2,
                    "expect": {"/ok": True},
                }],
            }
            profile_path = root / "profile.json"
            profile_path.write_text(json.dumps(config))
            receipt_path = root / "receipt.json"
            argv = [
                sys.executable,
                str(ROOT / "skills/verify-work/scripts/check_profile.py"),
                "--profile", str(profile_path),
                "--workspace", str(app),
                "--receipt", str(receipt_path),
            ]
            inherited = os.environ.copy()
            inherited.update({
                "GIT_DIR": str(ROOT / ".git"),
                "GIT_WORK_TREE": str(ROOT),
                "GIT_INDEX_FILE": str(ROOT / ".git" / "index"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_VALUE_0": str(ROOT),
            })

            result = subprocess.run(argv, capture_output=True, text=True, env=inherited)
            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            receipt = json.loads(receipt_path.read_text())
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["workspace_after"]["mode"], "git")

    def test_credentials_and_symlink_targets_are_never_content_inputs(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); self.git_workspace(root)
            (root / ".env").write_text("dummy private data")
            (root / "credential.py").write_text("dummy private data")
            (root / "helper.py").symlink_to(root / ".env")
            from unittest.mock import patch
            original = profile.digest
            def guarded(path):
                self.assertNotIn(path.name, {".env", "credential.py", "helper.py"})
                return original(path)
            with patch.object(profile, "digest", guarded):
                result = profile.run(self.receipt_profile(), root)
            self.assertTrue(result["passed"])
            self.assertIn(".env", result["workspace_after"]["metadata_only"])
            for name in ("credential.py", "helper.py"):
                spec = self.receipt_profile(); spec["source_paths"] = [name]
                with self.assertRaises(ValueError):
                    profile.run(spec, root)

    def test_process_resume_artifact_profile_and_freshness_cli_in_git_subdirectory(self):
        from evals import skills
        sample = next(s for s in skills.workflows_dataset() if s.id == 'workflow-native-process-resume')
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); app = root / 'app'; app.mkdir()
            for name, text in sample.files.items():
                (root / name).write_text(text)
            subprocess.run(['git', 'init', '-q', raw], check=True)
            subprocess.run(['git', '-C', raw, 'add', '.'], check=True)
            (app / 'RESULT.txt').write_text(sample.metadata['fixture_contract']['write_content'])
            spec = json.loads((root / 'profile.json').read_text())
            self.assertEqual(spec['workspace_identity']['mode'], 'artifact')
            spec['steps'][0]['argv'][0] = sys.executable
            (root / 'profile.json').write_text(json.dumps(spec))
            argv = [sys.executable, str(root / 'check_profile.py'), '--profile', str(root / 'profile.json'),
                    '--workspace', str(app)]
            run = subprocess.run([*argv, '--receipt', str(root / 'receipt.json')], capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            record = json.loads((root / 'receipt.json').read_text())
            self.assertTrue(record['passed'])
            self.assertEqual(record['workspace_after']['mode'], 'artifact')
            reuse = subprocess.run([*argv, '--check-receipt', str(root / 'receipt.json')], capture_output=True)
            self.assertEqual(reuse.returncode, 0, reuse.stderr)
            (app / 'RESULT.txt').write_text('stale')
            stale = subprocess.run([*argv, '--check-receipt', str(root / 'receipt.json')], capture_output=True)
            self.assertEqual(stale.returncode, 3, stale.stderr)
            self.assertFalse(json.loads(stale.stdout)['fresh'])

    def test_actual_process_interruption_retains_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker, state, record = (root / p for p in ["marker", "state", "record"])
            state.write_text(json.dumps({"task": {"objective": "Finish the retained objective"}}))
            code = f"from pathlib import Path; import time; Path({str(marker)!r}).write_text('ready'); time.sleep(30)"
            self.assertEqual(interrupt([sys.executable, "-c", code], marker, state, record, b"", timeout=2), 130)
            result = json.loads(record.read_text())
            self.assertTrue(result["interrupted"])
            self.assertNotEqual(result["exit_code"], 0)
            self.assertEqual(json.loads(state.read_text())["task"]["objective"], "Finish the retained objective")

    def test_normal_exit_cannot_count_as_interruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "exited"):
                interrupt([sys.executable, "-c", "pass"], root / "marker", root / "state", root / "record", b"", timeout=2)
            self.assertFalse((root / "record").exists())

    def test_pause_without_checkpoint_fails_without_resume_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = f"from pathlib import Path; import time; Path({str(root / 'marker')!r}).write_text('ready'); time.sleep(30)"
            with self.assertRaises(FileNotFoundError):
                interrupt([sys.executable, "-c", code], root / "marker", root / "state", root / "record", b"", timeout=2)
            self.assertFalse((root / "record").exists())

    def test_owned_descendant_ignoring_term_cannot_survive_parent_exit(self):
        for mode in ("profile", "interruption"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                child = "import signal,os,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path('child.pid').write_text(str(os.getpid())); time.sleep(30)"
                code = f"import subprocess,sys,time; from pathlib import Path; subprocess.Popen([sys.executable,'-c',{child!r}]);\nwhile not Path('child.pid').exists(): time.sleep(.01)\nPath('marker').write_text('ready'); time.sleep(30)"
                if mode == "profile":
                    step = {"id": "wait", "phase": "drive", "argv": [sys.executable, "-c", code], "timeout": .5, "expect": {"/ok": True}}
                    self.assertEqual(profile.execute(step, root)["status"], "failed")
                else:
                    (root / "state").write_text(json.dumps({"task": {"objective": "Finish"}}))
                    argv = [sys.executable, "-c", "import os; os.chdir(" + repr(str(root)) + "); " + code]
                    self.assertEqual(interrupt(argv, root / "marker", root / "state", root / "record", b"", timeout=2), 130)
                pid = int((root / "child.pid").read_text())
                status = Path(f"/proc/{pid}/stat")
                for _ in range(100):
                    if not status.exists() or status.read_text().split()[2] == "Z":
                        break
                    time.sleep(.01)
                else:
                    os.kill(pid, 9)
                    self.fail("owned descendant survived invocation cleanup")

    def test_failed_drive_stops_later_work_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.py").write_text("VALUE = 1\n")
            def step(phase, ok=True):
                code = f"from pathlib import Path; import json; p=Path('operations'); p.write_text((p.read_text() if p.exists() else '')+'{phase}\\n'); print(json.dumps({{'ok': {ok}}}))"
                return {"id": phase, "phase": phase, "argv": [sys.executable, "-c", code], "timeout": 2, "expect": {"/ok": True}}
            steps = [step("start"), step("doctor"), step("drive", False), step("drive"), step("cleanup")]
            steps[3]["id"] = "later"
            result = profile.run({"version": 1, "source_paths": ["source.py"], "workspace_identity": {"mode": "artifact"}, "steps": steps}, root)
            self.assertFalse(result["passed"])
            self.assertEqual([s["status"] for s in result["checks"]], ["accepted", "accepted", "failed", "not-run", "accepted"])
            self.assertEqual((root / "operations").read_text(), "start\ndoctor\ndrive\ncleanup\n")
            steps[2] = step("drive")
            self.assertTrue(profile.run({"version": 1, "source_paths": ["source.py"], "workspace_identity": {"mode": "artifact"}, "steps": steps}, root)["passed"])

    def test_green_command_cannot_hide_source_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.py").write_text("before")
            step = {"id": "change", "phase": "drive", "argv": [sys.executable, "-c", "from pathlib import Path; Path('source.py').write_text('after'); print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}}
            result = profile.run({"version": 1, "source_paths": ["source.py"], "workspace_identity": {"mode": "artifact"}, "steps": [step]}, root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["checks"][0]["status"], "failed")

    def test_cleanup_restoring_source_cannot_hide_an_intermediate_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source").write_text("before")
            steps = []
            for phase, code in [("start", ""), ("doctor", ""), ("drive", "Path('source').write_text('after');"), ("cleanup", "Path('source').write_text('before');")]:
                steps.append({"id": phase, "phase": phase, "argv": [sys.executable, "-c", "from pathlib import Path; " + code + "print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}})
            result = profile.run({"version": 1, "source_paths": ["source"], "workspace_identity": {"mode": "artifact"}, "steps": steps}, root)
            self.assertEqual((root / "source").read_text(), "before")
            self.assertFalse(result["passed"])
            self.assertEqual(result["checks"][2]["status"], "failed")

    def test_missing_check_and_type_confusion_reject(self):
        step = {"id": "check", "phase": "drive", "argv": [sys.executable, "-c", "print('{\"ok\":1}')"], "timeout": 2, "expect": {"/ok": True}}
        self.assertEqual(profile.execute(step, ROOT)["status"], "failed")
        step["expect"] = {"/checks/0/status": "accepted"}
        self.assertEqual(profile.execute(step, ROOT)["status"], "failed")
        step["expect"] = {"": {"ok": True}}
        self.assertEqual(profile.execute(step, ROOT)["status"], "failed")

    def test_failed_start_still_attempts_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source").write_text("known")
            steps = [{"id": phase, "phase": phase, "argv": [sys.executable, "-c", "raise SystemExit(4)" if phase == "start" else "print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}} for phase in ["start", "doctor", "drive", "cleanup"]]
            result = profile.run({"version": 1, "source_paths": ["source"], "workspace_identity": {"mode": "artifact"}, "steps": steps}, root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["checks"][-1]["status"], "accepted")

    def test_timeout_rejects_and_terminates_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = "import os,time; from pathlib import Path; Path('pid').write_text(str(os.getpid())); time.sleep(30)"
            step = {"id": "wait", "phase": "drive", "argv": [sys.executable, "-c", command], "timeout": .1, "expect": {"/ok": True}}
            self.assertEqual(profile.execute(step, root)["status"], "failed")
            with self.assertRaises(ProcessLookupError):
                os.kill(int((root / "pid").read_text()), 0)

    def test_fresh_private_receipt_is_required_before_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "app"
            app.mkdir()
            (app / "source").write_text("known")
            config = {"version": 1, "source_paths": ["source"], "workspace_identity": {"mode": "artifact"}, "steps": [{"id": "check", "phase": "drive", "argv": [sys.executable, "-c", "print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}}]}
            path = root / "profile.json"
            path.write_text(json.dumps(config))
            receipt = root / "receipt.json"
            argv = [sys.executable, str(ROOT / "skills/verify-work/scripts/check_profile.py"), "--profile", str(path), "--workspace", str(app), "--receipt", str(receipt)]
            created = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, (created.stdout, created.stderr))
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            original = receipt.read_bytes()
            repeated = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2, (repeated.stdout, repeated.stderr))
            self.assertEqual(receipt.read_bytes(), original)

    def test_source_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                profile.source_identity(root, ["../outside"])

    def test_checkpoint_preserves_objective_and_rejects_stale_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "checkpoint.json"
            task = {"objective": "Finish the parser", "requirements": [{"id": "quoted", "description": "Preserve quoted commas", "status": "pending"}], "decisions": ["Keep csv.DictReader"], "next_action": "Run the original check", "blockers": []}
            identity = checkpoint.save(path, root, task, None)
            read, returned = checkpoint.read(path)
            self.assertEqual(identity, returned)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            updated = {**task, "next_action": "Inspect the failure"}
            new_identity = checkpoint.save(path, root, updated, identity)
            self.assertNotEqual(identity, new_identity)
            with self.assertRaisesRegex(ValueError, "changed"):
                checkpoint.save(path, root, task, identity)
            with self.assertRaisesRegex(ValueError, "discard"):
                checkpoint.save(path, root, {**updated, "requirements": [{"id": "other", "description": "Other", "status": "pending"}]}, new_identity)
            with self.assertRaisesRegex(ValueError, "decisions"):
                checkpoint.save(path, root, {**updated, "decisions": []}, new_identity)
            self.assertEqual(checkpoint.read(path)[0]["sequence"], 2)

    def test_checkpoint_refuses_empty_or_foreign_task(self):
        with self.assertRaises(ValueError):
            checkpoint.validate({})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "checkpoint"
            path.write_text(json.dumps({"version": True, "sequence": 1, "workspace": {}, "task": {}}))
            with self.assertRaisesRegex(ValueError, "unsupported"):
                checkpoint.read(path)

    def test_approved_plan_continuation_uses_existing_fields_and_linked_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'checkpoint.json'
            task = {
                'objective': 'Finish the approved parser behavior',
                'requirements': [{'id': 'quoted', 'description': 'Preserve quoted commas', 'status': 'pending'}],
                'decisions': ['Plan plan-v1.html sha256=' + 'a' * 64,
                              'User confirmed plan-v1; source transcript remains approval provenance'],
                'next_action': 'Run held-out parser checks',
                'blockers': ['Independent review pending'],
            }
            identity = checkpoint.save(path, root, task, None)
            continued = {**task, 'decisions': task['decisions'] + ['Equivalent dependency repair preserves approved interfaces'],
                         'next_action': 'Resume affected checks'}
            checkpoint.save(path, root, continued, identity)
            resumed, _ = checkpoint.read(path)
            self.assertEqual(resumed['version'], 1)
            self.assertEqual(resumed['task']['requirements'], task['requirements'])
            self.assertEqual(resumed['task']['decisions'], continued['decisions'])
            changed = {**continued, 'requirements': [{'id': 'quoted', 'description': 'Preserve quoted commas and new delimiter', 'status': 'pending'}],
                       'decisions': continued['decisions'] + ['Plan-v2 supersedes plan-v1; linked previous checkpoint.json']}
            new_path = root / 'checkpoint-v2.json'
            checkpoint.save(new_path, root, changed, None)
            self.assertEqual(checkpoint.read(path)[0]['task']['requirements'], task['requirements'])
            self.assertEqual(checkpoint.read(new_path)[0]['task']['requirements'], changed['requirements'])

    def test_exact_json_rejects_extra_keys_and_boolean_number_confusion(self):
        boundary.check_json({"allowed": True}, {"allowed": True})
        for value in [{"allowed": 1}, {"allowed": True, "extra": "unexpected"}]:
            with self.assertRaises(ValueError):
                boundary.check_json(value, {"allowed": True})

    def test_ci_invalid_reference_optional_near_miss_and_cycle(self):
        boundary.check_ci({"jobs": {"build": {}, "test": {"needs": "build"}}}, "github")
        with self.assertRaisesRegex(ValueError, "undefined"):
            boundary.check_ci({"backend-test": {"dependencies": ["backend"]}}, "gitlab")
        boundary.check_ci({"test": {"needs": [{"job": "omitted", "optional": True}]}}, "gitlab")
        with self.assertRaisesRegex(ValueError, "cyclic"):
            boundary.check_ci({"jobs": {"a": {"needs": "b"}, "b": {"needs": "a"}}}, "github")
        with self.assertRaisesRegex(ValueError, "merged"):
            boundary.check_ci({"include": "external.yml", "test": {}}, "gitlab")
        with self.assertRaisesRegex(ValueError, "booleans"):
            boundary.check_ci({"test": {"needs": [{"job": "omitted", "optional": "true"}]}}, "gitlab")


if __name__ == "__main__":
    unittest.main()
