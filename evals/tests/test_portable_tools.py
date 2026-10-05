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
            result = profile.run({"version": 1, "source_paths": ["source.py"], "steps": steps}, root)
            self.assertFalse(result["passed"])
            self.assertEqual([s["status"] for s in result["checks"]], ["accepted", "accepted", "failed", "not-run", "accepted"])
            self.assertEqual((root / "operations").read_text(), "start\ndoctor\ndrive\ncleanup\n")
            steps[2] = step("drive")
            self.assertTrue(profile.run({"version": 1, "source_paths": ["source.py"], "steps": steps}, root)["passed"])

    def test_green_command_cannot_hide_source_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.py").write_text("before")
            step = {"id": "change", "phase": "drive", "argv": [sys.executable, "-c", "from pathlib import Path; Path('source.py').write_text('after'); print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}}
            result = profile.run({"version": 1, "source_paths": ["source.py"], "steps": [step]}, root)
            self.assertFalse(result["passed"])
            self.assertEqual(result["checks"][0]["status"], "failed")

    def test_cleanup_restoring_source_cannot_hide_an_intermediate_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source").write_text("before")
            steps = []
            for phase, code in [("start", ""), ("doctor", ""), ("drive", "Path('source').write_text('after');"), ("cleanup", "Path('source').write_text('before');")]:
                steps.append({"id": phase, "phase": phase, "argv": [sys.executable, "-c", "from pathlib import Path; " + code + "print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}})
            result = profile.run({"version": 1, "source_paths": ["source"], "steps": steps}, root)
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
            result = profile.run({"version": 1, "source_paths": ["source"], "steps": steps}, root)
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
            config = {"version": 1, "source_paths": ["source"], "steps": [{"id": "check", "phase": "drive", "argv": [sys.executable, "-c", "print('{\"ok\":true}')"], "timeout": 2, "expect": {"/ok": True}}]}
            path = root / "profile.json"
            path.write_text(json.dumps(config))
            receipt = root / "receipt.json"
            argv = [sys.executable, str(ROOT / "skills/verify-work/scripts/check_profile.py"), "--profile", str(path), "--workspace", str(app), "--receipt", str(receipt)]
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 0)
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            original = receipt.read_bytes()
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 2)
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
