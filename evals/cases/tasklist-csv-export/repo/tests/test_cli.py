import os
import subprocess
import sys
import tempfile
import unittest


def run(*args, env):
    return subprocess.run([sys.executable, "-m", "tasklist", *args], capture_output=True, text=True, env=env)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "TASKLIST_FILE": os.path.join(self.dir.name, "tasks.json")}

    def tearDown(self):
        self.dir.cleanup()

    def test_add_list_done(self):
        run("add", "Buy", "milk", env=self.env)
        run("done", "1", env=self.env)
        self.assertIn("[x] 1. Buy milk", run("list", env=self.env).stdout)


if __name__ == "__main__":
    unittest.main()
