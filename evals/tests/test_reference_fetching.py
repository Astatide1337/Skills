"""Offline tool-contract tests. Remote image availability is a separate observation."""
from __future__ import annotations
import base64
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
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


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
        self.assertEqual(set(json.loads(result.stdout)), set(fetcher.image_sources()))
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

    def test_intact_selected_cache_is_reused_without_network(self):
        with patch.object(fetcher, "download", return_value=PNG):
            first = fetcher.fetch(self.ids[:1], self.output)
        with patch.object(fetcher, "download") as network:
            second = fetcher.fetch(self.ids[:1], self.output)
        network.assert_not_called()
        self.assertEqual(second["files"][0]["status"], "reused")
        self.assertEqual(first["files"][0]["sha256"], second["files"][0]["sha256"])
        self.assertFalse(second["quality_verified"])

    def test_replaced_index_rejects_reuse_before_network_or_metadata_writes(self):
        for replacement in ("symlink", "directory"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "cache"
                outside = Path(directory) / "outside.md"
                outside.write_text("preserve outside sentinel")
                with patch.object(fetcher, "download", return_value=PNG):
                    fetcher.fetch(self.ids[:1], output)
                receipt_before = (output / "receipt.json").read_bytes()
                index = output / "index.md"
                index.unlink()
                if replacement == "symlink": index.symlink_to(outside)
                else: index.mkdir()
                with patch.object(fetcher, "download") as network, \
                     patch.object(fetcher, "decode_image") as decoder, \
                     self.assertRaises(FileExistsError):
                    fetcher.fetch(self.ids[:2], output)
                network.assert_not_called()
                decoder.assert_not_called()
                self.assertEqual(outside.read_text(), "preserve outside sentinel")
                self.assertEqual((output / "receipt.json").read_bytes(), receipt_before)

    def test_invalid_receipt_shapes_preserve_cache_before_network_or_decode(self):
        for payload in ([], None, 1, True, "cache", 1.5):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "cache"
                output.mkdir()
                (output / "receipt.json").write_text(json.dumps(payload))
                (output / "index.md").write_text("preserve index")
                (output / "apple-music.png").write_bytes(PNG)
                (output / "unrelated.txt").write_text("preserve unrelated data")
                before = {p.name: p.read_bytes() for p in output.iterdir()}
                with patch.object(fetcher, "download") as network, \
                     patch.object(fetcher, "decode_image") as decoder, \
                     self.assertRaisesRegex(FileExistsError, "fresh directory"):
                    fetcher.fetch(["apple-music"], output)
                network.assert_not_called()
                decoder.assert_not_called()
                self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_invalid_receipt_cli_reports_structured_failure_without_overwrites(self):
        # Include malformed JSON alongside valid JSON with the wrong root shape.
        for raw in ("[]", "null", "1", "{"):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "cache"
                output.mkdir()
                (output / "receipt.json").write_text(raw)
                (output / "index.md").write_text("preserve index")
                (output / "apple-music.png").write_bytes(PNG)
                (output / "unrelated.txt").write_text("preserve unrelated data")
                before = {p.name: p.read_bytes() for p in output.iterdir()}
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--id", "apple-music", "--output", str(output)],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)
                failure = json.loads(result.stderr)
                self.assertEqual(failure["status"], "failed")
                self.assertIn("fresh directory", failure["reason"])
                self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_adding_selection_retains_previous_cache(self):
        with patch.object(fetcher, "download", return_value=PNG):
            fetcher.fetch(self.ids[:1], self.output)
            fetcher.fetch(self.ids[1:2], self.output)
        with patch.object(fetcher, "download") as network:
            receipt = fetcher.fetch(self.ids[:2], self.output)
        network.assert_not_called()
        self.assertEqual([row["status"] for row in receipt["files"]], ["reused", "reused"])

    def test_changed_source_corruption_or_link_does_not_refetch_or_overwrite(self):
        for defect in ("source", "bytes", "link", "path"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "cache"
                with patch.object(fetcher, "download", return_value=PNG):
                    original = fetcher.fetch(self.ids[:1], output)
                row = original["files"][0]
                target = output / row["file"]
                if defect == "bytes": target.write_bytes(PNG + b"corruption")
                elif defect == "link":
                    target.unlink()
                    target.symlink_to(Path(directory) / "outside")
                else:
                    stored = json.loads((output / "receipt.json").read_text())
                    stored["files"][0]["url" if defect == "source" else "file"] = "changed"
                    (output / "receipt.json").write_text(json.dumps(stored))
                with patch.object(fetcher, "download") as network:
                    result = fetcher.fetch(self.ids[:1], output)
                network.assert_not_called()
                self.assertEqual(result["files"][0]["status"], "failed")
                self.assertIn("fresh directory", result["files"][0]["reason"])

    def test_decode_failure_is_visible_without_a_successful_image(self):
        with patch.object(fetcher, "download", return_value=PNG), \
             patch.object(fetcher, "decode_image", side_effect=ValueError("Image decoding failed")):
            result = fetcher.fetch(self.ids[:1], self.output)
        self.assertEqual(result["files"][0]["status"], "failed")
        self.assertIn("decoding", result["files"][0]["reason"])
        self.assertFalse(list(self.output.glob("*.png")))

    def test_missing_decoder_is_not_model_inspection(self):
        with patch.dict(sys.modules, {"PIL": None}):
            result = fetcher.decode_image(PNG)
        self.assertIn("not-checked", result)

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
