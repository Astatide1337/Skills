"""Offline tool-contract tests. Remote image availability is a separate observation."""
from __future__ import annotations
import hashlib
from http.client import IncompleteRead
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/web-interface/scripts/fetch_references.py"
SPEC = importlib.util.spec_from_file_location("fetch_references", SCRIPT)
assert SPEC and SPEC.loader
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)
PNG = b"\x89PNG\r\n\x1a\nfixture"


class ReferenceFetchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "references"
        self.ids = list(fetcher.image_sources())

    def test_list_uses_attributed_definitions_without_network(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--list"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)), 5)
        self.assertFalse(self.output.exists())

    def test_unknown_duplicate_and_empty_selection_do_not_create_output(self):
        for selection in ([], ["unknown"], [self.ids[0], self.ids[0]]):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                fetcher.fetch(selection, self.output)
        self.assertFalse(self.output.exists())

    def test_fetch_preserves_provenance_and_never_asserts_quality(self):
        with patch.object(fetcher, "download", return_value=PNG) as network:
            receipt = fetcher.fetch(self.ids[:2], self.output)
        self.assertEqual(network.call_count, 2)
        self.assertFalse(receipt["quality_verified"])
        for row in receipt["files"]:
            self.assertEqual(row["status"], "fetched")
            self.assertEqual(row["sha256"], hashlib.sha256(PNG).hexdigest())
            self.assertEqual((self.output / row["file"]).read_bytes(), PNG)
        self.assertEqual(json.loads((self.output / "receipt.json").read_text()), receipt)
        self.assertTrue((self.output / "index.md").is_file())

    def test_partial_failure_is_recorded_and_other_selected_sources_continue(self):
        with patch.object(fetcher, "download", side_effect=[OSError("network unavailable"), PNG]):
            receipt = fetcher.fetch(self.ids[:2], self.output)
        self.assertEqual([row["status"] for row in receipt["files"]], ["failed", "fetched"])
        self.assertIn("network unavailable", receipt["files"][0]["reason"])

    def test_interruption_keeps_remaining_sources_not_run(self):
        with patch.object(fetcher, "download", side_effect=KeyboardInterrupt):
            receipt = fetcher.fetch(self.ids[:2], self.output)
        self.assertEqual([row["status"] for row in receipt["files"]], ["interrupted", "not-run"])
        self.assertTrue((self.output / "receipt.json").is_file())

    def test_existing_directory_file_or_link_is_not_overwritten(self):
        for kind in ("directory", "file", "link"):
            destination = self.root / kind
            if kind == "directory": destination.mkdir()
            elif kind == "file": destination.write_text("preserve")
            else: destination.symlink_to(self.root / "absent")
            with self.subTest(kind=kind), self.assertRaises(FileExistsError):
                fetcher.fetch(self.ids[:1], destination)
        self.assertEqual((self.root / "file").read_text(), "preserve")
        self.assertFalse((self.root / "absent").exists())

    def test_source_definitions_reject_duplicate_and_unreviewed_origins(self):
        document = self.root / "references.md"
        for content in ("[image-a]: https://example.invalid/a.png\n",
                        "[image-a]: https://www.apple.com/a.png\n" * 2,
                        "[image-a]: https://user:pass@www.apple.com/a.png\n"):
            document.write_text(content)
            with patch.object(fetcher, "REFERENCE", document), self.assertRaises(ValueError):
                fetcher.image_sources()

    def test_request_contract_rejects_html_oversize_and_bad_http_status(self):
        url = fetcher.image_sources()[self.ids[0]]
        for status, data in ((200, b"<html>error</html>"),
                             (200, PNG + b"x" * 32), (403, PNG)):
            response = MagicMock()
            response.__enter__.return_value = response
            response.status = status
            response.read.return_value = data
            opener = MagicMock()
            opener.open.return_value = response
            with patch.object(fetcher, "build_opener", return_value=opener), \
                 patch.object(fetcher, "MAX_BYTES", len(PNG) + 1), self.assertRaises(ValueError):
                fetcher.download(url)

    def test_redirect_is_not_silently_followed(self):
        self.assertIsNone(fetcher.NoRedirect().redirect_request(
            None, None, 302, "moved", {}, "https://example.invalid/image.png"))

    def test_truncated_http_response_is_a_recorded_failure(self):
        with patch.object(fetcher, "download", side_effect=IncompleteRead(b"partial")):
            receipt = fetcher.fetch(self.ids[:1], self.output)
        self.assertEqual(receipt["files"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
