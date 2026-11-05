#!/usr/bin/env python3
"""Refresh NVIDIA's advertised inventory; only a successful inference probe enables new models."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request

BASE = "https://integrate.api.nvidia.com/v1"
LIMIT = 4 * 1024 * 1024


class DiscoveryError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DiscoveryError("redirect refused")


def request(path, key=None, body=None):
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
            raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise DiscoveryError("response too large")
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        # Provider error bodies and URLs can contain sensitive request details.
        raise DiscoveryError(f"HTTP {exc.code}") from None
    except (OSError, ValueError):
        raise DiscoveryError("network failure or malformed JSON") from None


def inventory(payload):
    if not isinstance(payload, dict) or payload.get("object") != "list":
        raise DiscoveryError("invalid inventory envelope")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise DiscoveryError("empty or invalid inventory")
    if payload.get("has_more") or payload.get("next") or payload.get("next_page"):
        raise DiscoveryError("partial inventory refused")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise DiscoveryError("invalid model record")
        mid = row.get("id")
        if (not isinstance(mid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:+-]{0,255}", mid)
                or row.get("object") != "model" or mid in result):
            raise DiscoveryError("invalid or duplicate model ID")
        if "deprecated" in row and not isinstance(row["deprecated"], bool):
            raise DiscoveryError("invalid deprecated flag")
        if "status" in row and not isinstance(row["status"], str):
            raise DiscoveryError("invalid model status")
        if row.get("deprecated") or row.get("status", "").lower() in {"deprecated", "retired", "disabled"}:
            continue
        result[mid] = row
    if not result:
        raise DiscoveryError("no nondeprecated inventory; preserving last good config")
    return result


def config_path(explicit=None):
    if explicit is not None:
        path = explicit
    elif os.environ.get("OPENCODE_CONFIG"):
        path = Path(os.environ["OPENCODE_CONFIG"]).expanduser()
    else:
        directory = Path(os.environ.get("OPENCODE_CONFIG_DIR") or
                         str(Path(os.environ.get("XDG_CONFIG_HOME") or Path.home()/".config")/"opencode"))
        # Both are merged by OpenCode; refuse JSONC rather than edit only half.
        if (directory/"opencode.jsonc").exists():
            raise DiscoveryError("JSONC config unsupported; select a JSON target explicitly")
        path = directory/"opencode.json"
    if path.suffix.lower() == ".jsonc":
        raise DiscoveryError("JSONC config unsupported")
    return path


def runtime_probe(mid, path):
    """Supported stateless runtime API; credentials stay inside OpenCode."""
    if os.environ.get("OPENCODE_CONFIG_CONTENT"):
        raise DiscoveryError("existing OPENCODE_CONFIG_CONTENT; cannot isolate probe overlay")
    env = os.environ.copy()
    env["OPENCODE_CONFIG"] = str(path.resolve())
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"providers": {"nvidia": {
        "models": {mid: {"disabled": False, "body": {"max_tokens": 64},
                         "limit": {"output": 64}}}}}})
    body = {"prompt": "Reply only OK.", "model": {"providerID": "nvidia", "id": mid}}
    try:
        result = subprocess.run(["opencode", "api", "--standalone", "POST",
                                 "/api/experimental/generate/text", "--data", json.dumps(body)],
                                env=env, capture_output=True, text=True, timeout=60)
        response = json.loads(result.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise DiscoveryError("OpenCode runtime probe failed or timed out") from None
    if not isinstance(response, dict):
        raise DiscoveryError("invalid runtime response")
    if result.returncode or "error" in response or "_tag" in response:
        # Never forward runtime messages: they may contain headers or credentials.
        codes = re.findall(r'"(?:statusCode|status)"\s*:\s*(401|403|429|503)', result.stdout)
        tag = response.get("_tag")
        safe_tag = tag if tag in {"ModelNotFoundError", "ProviderNotFoundError", "ProviderRequestError",
                                  "UnauthorizedError", "UnsupportedModelError"} else "request failed"
        raise DiscoveryError("OpenCode " + safe_tag + (" HTTP " + codes[0] if codes else ""))
    data = response.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("text"), str) or data["text"].strip().rstrip(".") != "OK":
        raise DiscoveryError("runtime response did not prove text callability")


def migrate_model(entry):
    model = copy.deepcopy(entry)
    for key in ("options", "settings"):
        if key in model and not isinstance(model[key], dict):
            raise DiscoveryError("invalid model options/settings")
    for old, new in (("id", "modelID"), ("release_date", "releaseDate"), ("options", "settings")):
        if old in model:
            model[new] = model.pop(old)
    caps = model.setdefault("capabilities", {})
    if not isinstance(caps, dict):
        raise DiscoveryError("invalid configured capabilities")
    if "tool_call" in model:
        caps["tools"] = model.pop("tool_call")
    modalities = model.pop("modalities", {})
    if not isinstance(modalities, dict):
        raise DiscoveryError("invalid model modalities")
    caps.update(modalities)
    cost = model.get("cost")
    if isinstance(cost, dict):
        def convert(value):
            value = copy.deepcopy(value)
            cache = {k: value.pop(v) for k, v in (("read", "cache_read"), ("write", "cache_write")) if v in value}
            if cache:
                value["cache"] = cache
            return value
        cost = copy.deepcopy(cost)
        tier = cost.pop("context_over_200k", None)
        model["cost"] = convert(cost)
        if tier is not None:
            model["cost"] = [model["cost"], {**convert(tier), "tier": {"type": "context", "size": 200000}}]
    if model.pop("status", None) == "deprecated":
        model["disabled"] = True
    # Complex legacy controls need OpenCode's own full migration.
    if set(model) & {"provider", "variants", "interleaved", "reasoning", "attachment", "experimental", "temperature"}:
        raise DiscoveryError("complex legacy model fields; migrate with OpenCode first")
    return model


def unresolved(config, rows, models):
    def unavailable(value):
        if isinstance(value, str) and value.startswith("nvidia/"):
            mid = value[7:].split("#")[0]
        elif isinstance(value, dict) and value.get("providerID") == "nvidia":
            mid = value.get("model")
        else:
            return False
        return mid not in rows or models.get(mid, {}).get("disabled", True)
    result = [key for key in ("model", "small_model") if unavailable(config.get(key))]
    for group in ("agent", "agents"):
        for name, agent in config.get(group, {}).items():
            if not isinstance(agent, dict):
                raise DiscoveryError("invalid configured agent")
            if unavailable(agent.get("model")):
                result.append(f"{group}.{name}.model")
    return result


def probe(mid, key, fetch=request):
    result = fetch("/chat/completions", key, {
        "model": mid, "messages": [{"role": "user", "content": "Call ping with value ok."}],
        "max_tokens": 64, "stream": False,
        "tools": [{"type": "function", "function": {"name": "ping", "parameters": {
            "type": "object", "properties": {"value": {"type": "string", "enum": ["ok"]}},
            "required": ["value"], "additionalProperties": False}}}],
        "tool_choice": {"type": "function", "function": {"name": "ping"}},
    })
    try:
        call = result["choices"][0]["message"]["tool_calls"][0]
        if call["type"] == "function" and call["function"]["name"] == "ping" and json.loads(call["function"]["arguments"]) == {"value": "ok"}:
            return
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    raise DiscoveryError("response did not prove tool calling")


def runtime_models(path=None):
    try:
        env = os.environ.copy()
        if path is not None:
            env["OPENCODE_CONFIG"] = str(path.resolve())
        result = subprocess.run(["opencode", "models", "--standalone"], env=env, capture_output=True, text=True, timeout=45, check=True)
    except (OSError, subprocess.SubprocessError):
        raise DiscoveryError("OpenCode runtime inventory unavailable; config preserved") from None
    return {line[7:] for line in result.stdout.splitlines() if line.startswith("nvidia/")}


def sync(config, rows, verified=(), clear=False, runtime_ids=(), callable_ids=()):
    if not isinstance(config, dict) or any(not isinstance(config.get(k, {}), dict) for k in ("provider", "providers", "agent", "agents")):
        raise DiscoveryError("invalid config maps")
    new = copy.deepcopy(config)
    legacy = new.get("provider", {}).get("nvidia")
    native = new.get("providers", {}).get("nvidia")
    if legacy is not None and native is not None:
        raise DiscoveryError("ambiguous NVIDIA config: both provider and providers")
    provider = native if native is not None else legacy
    if not isinstance(provider, dict):
        raise DiscoveryError("NVIDIA provider missing")
    for key in ("options", "settings"):
        if key in provider and not isinstance(provider[key], dict):
            raise DiscoveryError("invalid provider options/settings")
    if legacy is not None:
        if set(provider) - {"npm", "name", "options", "models", "env"} or set(provider.get("options", {})) - {"baseURL", "apiKey"}:
            raise DiscoveryError("unsupported legacy NVIDIA options; migrate with OpenCode first")
        if provider.get("npm") != "@ai-sdk/openai-compatible":
            raise DiscoveryError("unexpected NVIDIA package")
        provider = {"package": "@opencode/ai/providers/openai-compatible",
                    "settings": copy.deepcopy(provider.get("options", {})),
                    **{k: copy.deepcopy(provider[k]) for k in ("name", "env") if k in provider}}
        old_models = legacy.get("models", {})
        del new["provider"]["nvidia"]
        new.setdefault("providers", {})["nvidia"] = provider
    else:
        old_models = provider.get("models", {})
    if not isinstance(old_models, dict) or any(not isinstance(v, dict) for v in old_models.values()):
        raise DiscoveryError("invalid configured models")
    for entry in old_models.values():
        for key in ("options", "settings", "capabilities"):
            if key in entry and not isinstance(entry[key], dict):
                raise DiscoveryError("invalid configured model maps")
    if provider.get("settings", {}).get("baseURL") != BASE:
        raise DiscoveryError("unexpected NVIDIA endpoint")
    if legacy is not None:
        old_models = {mid: migrate_model(model) for mid, model in old_models.items()}
    models = {}
    for mid in sorted(rows):
        # Existing native user settings survive; new entries make no capability claims.
        model = copy.deepcopy(old_models.get(mid, {}))
        for key in ("options", "settings"):
            if key in model and not isinstance(model[key], dict):
                raise DiscoveryError("invalid model options/settings")
        model.setdefault("name", mid)
        model.setdefault("disabled", True)
        if not isinstance(model.get("capabilities", {}), dict):
            raise DiscoveryError("invalid configured capabilities")
        model.setdefault("capabilities", {}).setdefault("tools", False)
        if mid in callable_ids or mid in verified:
            model["disabled"] = False
        if mid in verified:
            model["capabilities"]["tools"] = True
        models[mid] = model
    # Config overlays the built-in catalog rather than replacing it. Retain disabled
    # tombstones so a later refresh cannot resurrect an absent catalog entry.
    for mid in sorted((set(old_models) | set(runtime_ids)) - set(rows)):
        model = copy.deepcopy(old_models.get(mid, {}))
        model.setdefault("name", mid)
        if not isinstance(model.get("capabilities", {}), dict):
            raise DiscoveryError("invalid configured capabilities")
        model["disabled"] = True
        model.setdefault("capabilities", {})["tools"] = False
        models[mid] = model
    provider["models"] = models
    removed = []
    def unavailable(selection):
        if isinstance(selection, str) and selection.startswith("nvidia/"):
            return selection[7:].split("#")[0] not in rows
        if isinstance(selection, dict) and selection.get("providerID") == "nvidia":
            return selection.get("model") not in rows
        return False
    unresolved(config, rows, models)  # Validate agent maps even without clearing.
    if clear:
        for key in ("model", "small_model"):
            if unavailable(new.get(key)):
                del new[key]
                removed.append(key)
        for group in ("agent", "agents"):
            for name, agent in new.get(group, {}).items():
                if not isinstance(agent, dict):
                    raise DiscoveryError("invalid configured agent")
                if unavailable(agent.get("model")):
                    del agent["model"]
                    removed.append(f"{group}.{name}.model")
    return new, removed


def atomic_write(path, data, mode):
    fd, temporary = tempfile.mkstemp(prefix=".nim-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(path, original, updated):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise DiscoveryError("config must be a regular non-symlink file")
    if path.read_bytes() != original:
        raise DiscoveryError("config changed during discovery")
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, backup = tempfile.mkstemp(prefix=path.name + ".nim-backup-", dir=path.parent)
    with os.fdopen(fd, "wb") as stream:
        os.fchmod(stream.fileno(), mode & 0o600)
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    atomic_write(path, updated, mode)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--clear-unavailable-overrides", action="store_true")
    parser.add_argument("--probe", metavar="MODEL_ID", help="one explicit candidate via live OpenCode runtime; 64 output tokens")
    parser.add_argument("--key-env", help="explicit environment secret for forced tool probe instead of runtime text probe")
    parser.add_argument("--restore", type=Path, help="restore a local backup atomically; requires --apply")
    args = parser.parse_args()
    try:
        args.config = config_path(args.config)
        original = args.config.read_bytes()
        if args.restore:
            if not args.apply or args.probe or args.key_env or args.clear_unavailable_overrides:
                raise DiscoveryError("restore requires --apply and no discovery options")
            restored = args.restore.read_bytes()
            if not isinstance(json.loads(restored), dict):
                raise DiscoveryError("invalid backup config")
            print(json.dumps({"restored": True, "backup": apply(args.config, original, restored)}))
            return 0
        config = json.loads(original)
        if args.key_env and not args.probe:
            raise DiscoveryError("--key-env requires --probe")
        rows = inventory(request("/models"))
        verified, callable_ids, status = [], [], "not run"
        if args.probe:
            if args.probe not in rows:
                raise DiscoveryError("probe model absent or deprecated")
            try:
                if args.key_env:
                    key = os.environ.get(args.key_env)
                    if not key:
                        raise DiscoveryError("explicit environment secret unavailable")
                    probe(args.probe, key)
                    verified.append(args.probe)
                    status = "authenticated tool call verified (API only)"
                else:
                    runtime_probe(args.probe, args.config)
                    status = "runtime text call verified; tool capability unverified"
                callable_ids.append(args.probe)
            except DiscoveryError as exc:
                print(json.dumps({"probe": str(exc), "callable": "unverified",
                                  "tool_capability": "unverified", "applied": False, "config_preserved": True}))
                return 1
        updated, removed = sync(config, rows, verified, args.clear_unavailable_overrides, runtime_models(args.config), callable_ids)
        changed = updated != config
        report = {"advertised": len(rows), "probe": status, "verified": verified,
                  "callable_verified": callable_ids,
                  "unresolved_overrides": unresolved(updated, rows, updated["providers"]["nvidia"]["models"]),
                  "changed": changed, "applied": args.apply and changed, "removed_overrides": removed}
        if args.apply and changed:
            report["backup"] = apply(args.config, original, (json.dumps(updated, indent=2) + "\n").encode())
        print(json.dumps(report, indent=2))
        return 0
    except DiscoveryError as exc:
        print(json.dumps({"error": str(exc), "config_preserved": True}))
        return 1
    except (OSError, ValueError, TypeError):
        # Never print raw parser/filesystem exceptions or config values.
        print(json.dumps({"error": "discovery/config validation failed; config preserved"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
