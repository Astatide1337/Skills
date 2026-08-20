from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "skills" / "html-artifacts" / "scripts" / "check_artifact.py"
SPEC = importlib.util.spec_from_file_location("check_artifact", CHECKER)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HtmlArtifactCheckerTests(unittest.TestCase):
    def write(self, source: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory)
        path = directory / "artifact.html"
        path.write_text(source, encoding="utf-8")
        return path

    def test_accepts_minimal_offline_document(self) -> None:
        path = self.write(
            "<!doctype html><html lang='en'><head><title>Report</title>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "</head><body><main><h1>Report</h1></main></body></html>"
        )
        self.assertEqual(MODULE.check(path), [])

    def test_rejects_remote_runtime_asset_and_heading_jump(self) -> None:
        path = self.write(
            "<!doctype html><html lang='en'><head><title>Report</title>"
            "<meta name='viewport' content='width=device-width'>"
            "<script src='https://example.com/app.js'></script></head>"
            "<body><main><h1>Report</h1><h3>Details</h3></main></body></html>"
        )
        errors = MODULE.check(path)
        self.assertTrue(any("remote runtime assets" in error for error in errors))
        self.assertTrue(any("heading level jumps" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
