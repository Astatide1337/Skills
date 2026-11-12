"""Offline acceptance checks: python -m unittest discover -s ... -p test_nim_models.py."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location("nim_models", Path(__file__).resolve().parents[2] / "skills/follow-instructions/scripts/nim-models.py")
nim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nim)


def payload(*rows):
    return {"object": "list", "data": [{"id": mid, "object": "model", **extra} for mid, extra in rows]}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        runtime = patch.object(nim, "runtime_models", return_value=set())
        runtime.start()
        self.addCleanup(runtime.stop)
        self.config = {"provider": {"nvidia": {"npm": "@ai-sdk/openai-compatible", "options": {
            "baseURL": nim.BASE}, "models": {"retired": {"name": "old"}}}, "other": {"options": {"keep": True}}},
            "model": "other/default", "small_model": "nvidia/retired",
            "permission": {"shell": "ask"}, "plugins": ["keep"],
            "agent": {"critic": {"model": "nvidia/retired", "prompt": "keep", "permission": {"edit": "deny"}},
                      "builder": {"model": "other/default"}}}
        self.rows = nim.inventory(payload(("owner/chat", {}), ("owner/embedding", {})))

    def test_malformed_empty_partial_duplicate_deprecated(self):
        for data in (None, {}, {"object": "list", "data": []}, payload(("bad\nID", {})),
                     payload(("same", {}), ("same", {})),
                     payload(("old", {"deprecated": True})),
                     payload(("old", {"status": "retired"})),
                     payload(("bad", {"deprecated": "false"})),
                     {**payload(("ok", {})), "has_more": True}):
            with self.subTest(data=data), self.assertRaises(nim.DiscoveryError):
                nim.inventory(data)

    def test_metadata_does_not_enable_nonchat_or_claim_tools(self):
        new, _ = nim.sync(self.config, self.rows)
        for model in new["providers"]["nvidia"]["models"].values():
            self.assertTrue(model["disabled"])
            self.assertFalse(model["capabilities"]["tools"])
        self.assertEqual(new["small_model"], "nvidia/retired")

    def test_stale_runtime_catalog_cannot_resurrect_models(self):
        new, _ = nim.sync(self.config, self.rows, runtime_ids={"builtin/retired"})
        models = new["providers"]["nvidia"]["models"]
        self.assertTrue(models["builtin/retired"]["disabled"])
        self.assertTrue(models["retired"]["disabled"])
        self.assertEqual(nim.sync(new, self.rows)[0], new)

    def test_preservation_idempotence_and_explicit_clear(self):
        before = copy.deepcopy(self.config)
        new, removed = nim.sync(self.config, self.rows, clear=True)
        self.assertEqual(self.config, before)
        self.assertEqual(removed, ["small_model", "agent.critic.model"])
        self.assertEqual(new["permission"], before["permission"])
        self.assertEqual(new["provider"]["other"], before["provider"]["other"])
        self.assertEqual(new["agent"]["critic"], {"prompt": "keep", "permission": {"edit": "deny"}})
        self.assertEqual(new["model"], before["model"])
        self.assertEqual(nim.sync(new, self.rows, clear=True), (new, []))

    def test_probe_success_enables_only_explicit_candidate(self):
        response = {"choices": [{"message": {"tool_calls": [{"type": "function", "function": {
            "name": "ping", "arguments": '{"value":"ok"}'}}]}}]}
        def fetch(path, key, body):
            self.assertEqual(path, "/chat/completions")
            self.assertEqual(body["max_tokens"], 64)
            self.assertEqual(body["model"], "owner/chat")
            return response
        nim.probe("owner/chat", "fake-offline-key", fetch)
        new, _ = nim.sync(self.config, self.rows, ["owner/chat"])
        self.assertFalse(new["providers"]["nvidia"]["models"]["owner/chat"]["disabled"])
        self.assertTrue(new["providers"]["nvidia"]["models"]["owner/embedding"]["disabled"])
        self.assertEqual(nim.sync(new, self.rows)[0], new)

    def test_invalid_probe_not_tool_proof(self):
        for result in ({}, {"choices": []}, {"choices": [{"message": {"content": "ok"}}]}):
            with self.assertRaises(nim.DiscoveryError):
                nim.probe("owner/chat", "fake", lambda *a: result)

    def test_transport_sanitizes_errors_and_refuses_redirects(self):
        for code in (401, 403, 429, 503):
            with patch("urllib.request.OpenerDirector.open", side_effect=urllib.error.HTTPError(
                    nim.BASE, code, "secret-like server error", {}, None)):
                with self.assertRaisesRegex(nim.DiscoveryError, f"^HTTP {code}$"):
                    nim.request("/models")
        with self.assertRaises(nim.DiscoveryError):
            nim.NoRedirect().redirect_request(None, None, None, None, None, None)

    def test_atomic_backup_rollback_mode_and_races(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"opencode.json"
            original = json.dumps(self.config).encode()
            path.write_bytes(original)
            path.chmod(0o640)
            updated = json.dumps(nim.sync(self.config, self.rows)[0]).encode()
            backup = Path(nim.apply(path, original, updated))
            self.assertEqual(backup.read_bytes(), original)
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            nim.apply(path, updated, backup.read_bytes())
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(nim.DiscoveryError):
                nim.apply(path, b"stale", updated)
            with patch.object(nim.os, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    nim.apply(path, original, updated)
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(list(Path(folder).glob(".nim-*")))

    def test_cli_errors_preserve_last_good_and_default_is_dry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"config.json"
            original = json.dumps(self.config).encode()
            path.write_bytes(original)
            for result in (nim.DiscoveryError("HTTP 503"), {}, {"object": "list", "data": []},
                           ValueError("malformed JSON"), nim.DiscoveryError("network failure")):
                with patch("sys.argv", ["nim-models", "--config", str(path), "--apply"]), \
                     patch.object(nim, "request", side_effect=result if isinstance(result, Exception) else None,
                                  return_value=result), patch("builtins.print"):
                    self.assertEqual(nim.main(), 1)
                self.assertEqual(path.read_bytes(), original)
            with patch("sys.argv", ["nim-models", "--config", str(path)]), \
                 patch.object(nim, "request", return_value=payload(("owner/chat", {}))), patch("builtins.print"):
                self.assertEqual(nim.main(), 0)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)


    def run_cli(self, path, *args):
        with patch("sys.argv", ["nim-models", "--config", str(path), *args]), patch("builtins.print") as output:
            code = nim.main()
        return code, json.loads(output.call_args.args[0])

    def test_requested_probe_failure_is_nonzero_and_byte_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"config.json"
            original = json.dumps(self.config).encode()
            path.write_bytes(original)
            with patch.object(nim, "request", return_value=payload(("owner/chat", {}))), patch.object(
                    nim, "runtime_probe", side_effect=nim.DiscoveryError("OpenCode ProviderRequestError HTTP 403")):
                code, report = self.run_cli(path, "--probe", "owner/chat", "--apply")
            self.assertEqual(code, 1)
            self.assertFalse(report["applied"])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_config_precedence_and_jsonc_refusal(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(nim.os.environ, {
                "HOME": folder+"/home", "OPENCODE_CONFIG_DIR": folder+"/custom",
                "XDG_CONFIG_HOME": folder+"/xdg"}, clear=True):
            custom = Path(folder)/"custom"
            custom.mkdir()
            self.assertEqual(nim.config_path(), custom/"opencode.json")
            (custom/"opencode.jsonc").write_text("// comment")
            with self.assertRaisesRegex(nim.DiscoveryError, "JSONC"):
                nim.config_path()
            explicit = Path(folder)/"explicit.json"
            self.assertEqual(nim.config_path(explicit), explicit)
            with self.assertRaises(nim.DiscoveryError):
                nim.config_path(custom/"opencode.jsonc")
            del nim.os.environ["OPENCODE_CONFIG_DIR"]
            self.assertEqual(nim.config_path(), Path(folder)/"xdg/opencode/opencode.json")
            del nim.os.environ["XDG_CONFIG_HOME"]
            home_config = Path(folder)/"home/.config/opencode"
            self.assertEqual(nim.config_path(), home_config/"opencode.json")
            home_config.mkdir(parents=True)
            (home_config/"opencode.jsonc").write_text("// comment")
            with self.assertRaisesRegex(nim.DiscoveryError, "JSONC"):
                nim.config_path()

    def test_restore_recovers_corrupt_target_without_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            path, backup = Path(folder)/"config.json", Path(folder)/"backup.json"
            path.write_bytes(b"{broken")
            restored = json.dumps(self.config).encode()
            backup.write_bytes(restored)
            with patch.object(nim, "request") as fetch:
                code, report = self.run_cli(path, "--restore", str(backup), "--apply")
            fetch.assert_not_called()
            self.assertEqual(code, 0)
            self.assertEqual(path.read_bytes(), restored)
            self.assertEqual(Path(report["backup"]).read_bytes(), b"{broken")
            self.assertEqual(stat.S_IMODE(Path(report["backup"]).stat().st_mode), 0o600)

    def test_legacy_metadata_translation_and_tombstone_preservation(self):
        entry = {"id": "api-id", "name": "Custom", "tool_call": True,
                 "modalities": {"input": ["text", "image"], "output": ["text"]},
                 "cost": {"input": 1, "output": 2, "cache_read": 0.1},
                 "limit": {"context": 1000, "output": 100}, "options": {"temperature": 0.2}}
        self.config["provider"]["nvidia"]["models"] = {"owner/chat": entry, "retired": entry}
        new, _ = nim.sync(self.config, self.rows)
        models = new["providers"]["nvidia"]["models"]
        for mid in ("owner/chat", "retired"):
            self.assertEqual(models[mid]["name"], "Custom")
            self.assertEqual(models[mid]["modelID"], "api-id")
            self.assertEqual(models[mid]["cost"]["cache"]["read"], 0.1)
            self.assertEqual(models[mid]["limit"], entry["limit"])
            self.assertEqual(models[mid]["settings"], entry["options"])
            self.assertEqual(models[mid]["capabilities"]["input"], ["text", "image"])
        self.assertFalse(models["retired"]["capabilities"]["tools"])
        self.assertEqual(nim.sync(new, self.rows)[0], new)

    def test_malformed_provider_and_model_maps_are_clean_errors(self):
        for native in (False, True):
            for key in ("options", "settings"):
                for value in (None, 42, [], "bad"):
                    config = nim.sync(self.config, self.rows)[0] if native else copy.deepcopy(self.config)
                    config["providers" if native else "provider"]["nvidia"][key] = value
                    with self.subTest(native=native, key=key, value=value), self.assertRaises(nim.DiscoveryError):
                        nim.sync(config, self.rows)
        for key in ("options", "settings", "capabilities"):
            config = nim.sync(self.config, self.rows)[0]
            config["providers"]["nvidia"]["models"]["retired"][key] = None
            with self.assertRaises(nim.DiscoveryError):
                nim.sync(config, self.rows)

    def test_unresolved_reports_all_override_forms_and_disabled_models(self):
        self.config["model"] = {"providerID": "nvidia", "model": "missing"}
        self.config["agents"] = {"review": {"model": "nvidia/owner/chat#fast"},
                                 "other": {"model": "other/model"}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"config.json"
            path.write_text(json.dumps(self.config))
            with patch.object(nim, "request", return_value=payload(("owner/chat", {}))):
                code, report = self.run_cli(path)
            self.assertEqual(code, 0)
            self.assertEqual(report["unresolved_overrides"],
                             ["model", "small_model", "agent.critic.model", "agents.review.model"])
            self.assertEqual(report["removed_overrides"], [])
            with patch.object(nim, "request", return_value=payload(("owner/chat", {}))):
                code, report = self.run_cli(path, "--clear-unavailable-overrides")
            self.assertEqual(code, 0)
            self.assertEqual(report["unresolved_overrides"], ["agents.review.model"])
            self.assertEqual(report["removed_overrides"], ["model", "small_model", "agent.critic.model"])


    def test_runtime_uses_supported_api_and_private_overlay(self):
        with patch.dict(nim.os.environ, {}, clear=True), patch.object(nim.subprocess, "run") as run:
            run.return_value.stdout = '{"data":{"text":"OK"}}'
            run.return_value.returncode = 0
            nim.runtime_probe("owner/chat", Path("config.json"))
            args, kwargs = run.call_args
            self.assertIn("/api/experimental/generate/text", args[0])
            overlay = json.loads(kwargs["env"]["OPENCODE_CONFIG_CONTENT"])
            model = overlay["providers"]["nvidia"]["models"]["owner/chat"]
            self.assertEqual(model["body"]["max_tokens"], 64)
            self.assertFalse(model["disabled"])
            self.assertNotIn("OPENCODE_CONFIG_CONTENT", nim.os.environ)
            for text in ('{"_tag":"ProviderRequestError","statusCode":403,"message":"fake-secret"}',
                         '[]', '{"data":{}}'):
                run.return_value.stdout = text
                with self.assertRaises(nim.DiscoveryError) as error:
                    nim.runtime_probe("owner/chat", Path("config.json"))
                self.assertNotIn("fake-secret", str(error.exception))

    def test_runtime_success_enables_text_without_claiming_tool_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"config.json"
            path.write_text(json.dumps(self.config))
            with patch.object(nim, "request", return_value=payload(("owner/chat", {}))), patch.object(nim, "runtime_probe"):
                code, report = self.run_cli(path, "--probe", "owner/chat", "--apply")
            self.assertEqual(code, 0)
            self.assertEqual(report["verified"], [])
            self.assertEqual(report["callable_verified"], ["owner/chat"])
            model = json.loads(path.read_bytes())["providers"]["nvidia"]["models"]["owner/chat"]
            self.assertFalse(model["disabled"])
            self.assertFalse(model["capabilities"]["tools"])

    def test_explicit_environment_tool_probe_and_missing_secret(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(nim.os.environ, {}, clear=True):
            path = Path(folder)/"config.json"
            original = json.dumps(self.config).encode()
            path.write_bytes(original)
            with patch.object(nim, "request", return_value=payload(("owner/chat", {}))), patch.object(nim, "probe") as tool:
                code, report = self.run_cli(path, "--probe", "owner/chat", "--key-env", "NIM_TEST_KEY", "--apply")
                self.assertEqual(code, 1)
                self.assertEqual(path.read_bytes(), original)
                tool.assert_not_called()
                nim.os.environ["NIM_TEST_KEY"] = "fake-offline-only"
                with patch.object(nim, "runtime_probe") as runtime:
                    code, report = self.run_cli(path, "--probe", "owner/chat", "--key-env", "NIM_TEST_KEY", "--apply")
                runtime.assert_not_called()
                tool.assert_called_once_with("owner/chat", "fake-offline-only")
                self.assertEqual(code, 0)
                self.assertEqual(report["verified"], ["owner/chat"])
                self.assertNotIn("fake-offline-only", json.dumps(report))

    def test_invalid_restore_preserves_corrupt_target(self):
        with tempfile.TemporaryDirectory() as folder:
            path, backup = Path(folder)/"config.json", Path(folder)/"backup.json"
            for data in (b"[]", b"{broken"):
                path.write_bytes(b"corrupt target")
                backup.write_bytes(data)
                code, _ = self.run_cli(path, "--restore", str(backup), "--apply")
                self.assertEqual(code, 1)
                self.assertEqual(path.read_bytes(), b"corrupt target")
                self.assertFalse(list(Path(folder).glob("*.nim-backup-*")))


if __name__ == "__main__":
    unittest.main()


class ConfigurationSelectionTests(unittest.TestCase):
    def test_explicit_then_environment_config(self):
        with patch.dict(nim.os.environ, {"OPENCODE_CONFIG": "/tmp/selected.json",
                                        "OPENCODE_CONFIG_DIR": "/tmp/other"}, clear=True):
            self.assertEqual(nim.config_path(), Path("/tmp/selected.json"))
            self.assertEqual(nim.config_path(Path("/tmp/explicit.json")),
                             Path("/tmp/explicit.json"))

    def test_catalog_uses_standalone_selected_config(self):
        with patch.object(nim.subprocess, "run") as run:
            run.return_value.stdout = "nvidia/owner/chat\nother/model\n"
            self.assertEqual(nim.runtime_models(Path("/tmp/selected.json")), {"owner/chat"})
            args, kwargs = run.call_args
            self.assertEqual(args[0], ["opencode", "models", "--standalone"])
            self.assertEqual(kwargs["env"]["OPENCODE_CONFIG"], "/tmp/selected.json")
