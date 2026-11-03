"""Run real contained grading commands against harmless owned canaries."""
from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals import skills
from evals.workspace_evidence import capture_baseline, read_workspace_file


class RunnerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = LocalSandboxEnvironment()
        self.addCleanup(self.environment.directory.cleanup)
        self.root = Path(self.environment.directory.name)
        self.outside = tempfile.TemporaryDirectory()
        self.addCleanup(self.outside.cleanup)
        self.hidden = Path(self.outside.name) / "owned-marker.txt"
        self.hidden.write_text("owned canary, not a credential")
        self.scope = patch.object(skills, "sandbox", return_value=self.environment)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def state(self, source="VALUE = 3\n", *, supplemental=None, acceptance=None):
        (self.root / "module.py").write_text(source)
        (self.root / "check.py").write_text(supplemental or "from module import VALUE\nassert VALUE == 3\n")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "-qm", "baseline"], cwd=self.root, check=True)
        state = TaskState(model="stub/no-model", sample_id="runner-boundary", epoch=1,
                          input="Verify the owned fixture", messages=[])
        state.metadata = {
            "allow_changes": True, "allowed_paths": ["module.py"],
            "fixture_contract": {
                "kind": "workspace-test", "required_paths": ["module.py"],
                "test_command": ["python", "-B", "check.py"],
                "acceptance_test": acceptance or "from module import VALUE\nassert VALUE == 3\n",
            },
        }
        state.output = ModelOutput.from_content(model="stub/no-model", content="checked")
        state.store.set("workspace_baseline", capture_baseline(self.root))
        return state

    async def score(self, state):
        return await skills.workflow_effects()(state, Target("fixture correctness"))

    async def test_valid_alternatives_and_wrong_behavior_are_distinguished(self):
        state = self.state()
        expected = hashlib.sha256((state.metadata["fixture_contract"]["acceptance_test"] + "\n").encode()).hexdigest()
        for source in ("VALUE = 3\n", "VALUE = sum((1, 2))\n"):
            (self.root / "module.py").write_text(source)
            result = await self.score(state)
            self.assertEqual(result.value, 1, result.explanation)
            receipt = state.store.get("runner_acceptance")
            self.assertTrue(receipt["completed"])
            self.assertEqual(receipt["test_sha256"], expected)
            self.assertEqual(receipt["workspace_sha256"], receipt["final_workspace_sha256"])
            self.assertEqual(receipt["stdout"], "")
        (self.root / "module.py").write_text("VALUE = 4\n")
        self.assertEqual((await self.score(state)).value, 0)
        self.assertIsNone(state.store.get("runner_acceptance"))

    async def test_successful_early_exit_cannot_skip_hidden_assertions(self):
        state = self.state(supplemental="pass\n")
        for source in ("raise SystemExit(0)\n", "import os\nos._exit(0)\n",
                       "print('checks passed')\nraise SystemExit(0)\n"):
            with self.subTest(source=source):
                (self.root / "module.py").write_text(source)
                result = await self.score(state)
                self.assertEqual(result.value, 0, result.explanation)
                receipt = state.store.get("runner_acceptance")
                self.assertFalse(receipt["completed"])
                self.assertNotEqual(receipt["exit_code"], 0)
                if "os._exit" in source:
                    self.assertEqual(receipt["process_exit_code"], 0)
                    self.assertIn("without completing", result.explanation)
                else:
                    self.assertIn("aborted before completion", result.explanation)

    async def test_both_check_phases_cannot_reach_outside_files_or_host_network(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        (self.root / "escape").symlink_to(self.hidden)
        source = f'''from pathlib import Path
import socket

def probe(writable):
    for name in ({str(self.hidden)!r}, '/workspace/escape', {'/proc/self/root' + str(self.hidden)!r}):
        try:
            Path(name).read_bytes()
        except OSError:
            pass
        else:
            raise AssertionError('outside read was allowed: ' + name)
    try:
        Path({str(Path(self.outside.name) / 'outside-write.txt')!r}).write_text('bad')
    except OSError:
        pass
    else:
        raise AssertionError('outside write was allowed')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(.3)
        try:
            connection.connect(('127.0.0.1', {port}))
        except OSError:
            pass
        else:
            raise AssertionError('host listener was reachable')
    try:
        Path('phase.txt').write_text('owned supplemental effect')
    except OSError:
        assert not writable, 'supplemental workspace must stay writable'
    else:
        assert writable, 'hidden acceptance workspace must be read-only'
'''
        state = self.state(source, supplemental="from module import probe\nprobe(True)\n",
                           acceptance="from module import probe\nprobe(False)\n")
        result = await self.score(state)
        self.assertEqual(result.value, 1, result.explanation)
        self.assertFalse((Path(self.outside.name) / "outside-write.txt").exists())
        self.assertEqual((self.root / "phase.txt").read_text(), "owned supplemental effect")
        self.assertEqual((await skills.workspace_policy()(state, None)).value, 0)
        receipt = state.store.get("runner_acceptance")
        self.assertEqual(receipt["workspace_sha256"], receipt["final_workspace_sha256"])

    async def test_readonly_acceptance_cannot_rewrite_its_candidate(self):
        state = self.state(acceptance="from pathlib import Path\nPath('module.py').write_text('VALUE = 4')\n")
        result = await self.score(state)
        self.assertEqual(result.value, 0)
        self.assertIn("Read-only file system", result.explanation)
        self.assertEqual((self.root / "module.py").read_text(), "VALUE = 3\n")

    async def test_unsafe_required_artifact_is_rejected_without_host_read(self):
        state = self.state(supplemental="raise AssertionError('must not execute')\n")
        (self.root / "module.py").unlink()
        (self.root / "module.py").symlink_to(self.hidden)
        result = await self.score(state)
        self.assertEqual(result.value, 0)
        self.assertIn("paths missing", result.explanation)
        self.assertIsNone(state.store.get("runner_acceptance"))

    async def test_source_drift_during_acceptance_invalidates_receipt(self):
        state = self.state()
        execute = skills._execute_workspace_check

        async def drift(root, command, *, read_only):
            result = await execute(root, command, read_only=read_only)
            if read_only:
                (root / "module.py").write_text("VALUE = 4\n")
            return result

        with patch.object(skills, "_execute_workspace_check", drift):
            result = await self.score(state)
        self.assertEqual(result.value, 0)
        self.assertIn("changed during acceptance", result.explanation)
        receipt = state.store.get("runner_acceptance")
        self.assertNotEqual(receipt["workspace_sha256"], receipt["final_workspace_sha256"])
        self.assertNotEqual(receipt["exit_code"], 0)

    async def test_cancellation_ends_owned_checker_descendants(self):
        script = ("import subprocess,time\n"
                  "subprocess.Popen(['python','-c',\"import time,pathlib; time.sleep(.5); pathlib.Path('late.txt').write_text('bad')\"])\n"
                  "print('ready',flush=True)\ntime.sleep(20)\n")
        command = skills.contained_workspace_command(self.root, ["python", "-c", script], read_only=False)
        task = asyncio.create_task(self.environment.exec(command, timeout=30, timeout_retry=False))
        await asyncio.sleep(.15)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(.65)
        self.assertFalse((self.root / "late.txt").exists())

    async def test_timeout_ends_owned_checker_descendants(self):
        script = ("import subprocess,time\n"
                  "subprocess.Popen(['python','-c',\"import time,pathlib; time.sleep(1.5); pathlib.Path('late.txt').write_text('bad')\"])\n"
                  "time.sleep(20)\n")
        command = skills.contained_workspace_command(self.root, ["python", "-c", script], read_only=False)
        with self.assertRaises(TimeoutError):
            await self.environment.exec(command, timeout=1, timeout_retry=False)
        await asyncio.sleep(.7)
        self.assertFalse((self.root / "late.txt").exists())

    def test_bounded_reader_rejects_leaf_parent_hardlink_and_truncation(self):
        (self.root / "escape").symlink_to(self.hidden)
        (self.root / "parent").symlink_to(Path(self.outside.name), target_is_directory=True)
        os.link(self.hidden, self.root / "hardlink")
        (self.root / "large.txt").write_text("too long")
        for name in ("escape", "parent/owned-marker.txt", "hardlink", "../owned-marker.txt", "large.txt"):
            with self.subTest(name=name):
                text, error = read_workspace_file(self.root, name, max_bytes=3)
                self.assertIsNone(text)
                self.assertTrue(error)
        (self.root / "regular.txt").write_text("yes")
        self.assertEqual(read_workspace_file(self.root, "regular.txt", max_bytes=3), ("yes", None))


if __name__ == "__main__":
    unittest.main()
