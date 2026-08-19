from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_list_matches_skill_directories(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.splitlines(),
            sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()),
        )

    def test_install_all_copies_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as target:
            subprocess.run(
                [str(ROOT / "install.sh"), "--all", "--target", target],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = sorted(path.name for path in Path(target).iterdir())
            expected = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
            self.assertEqual(installed, expected)
            for name in expected:
                self.assertTrue((Path(target) / name / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
