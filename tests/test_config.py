import os
import pytest
from pathlib import Path
from unittest.mock import patch

CONFIG_ENV_VARS = (
    "AUTH_MODE",
    "CLOUDFLARE_TEAM_DOMAIN",
    "CLOUDFLARE_AUD",
    "PUBLIC_BASE_URL",
    "INTERNAL_BYPASS",
    "HOST",
    "PORT",
    "MCP_PATH",
    "SKILLS_DIR",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "METRICS_ENABLED",
    "SKG_CONFIG",
    "SKG_ENVIRONMENT",
    "SKG_PROFILE",
    "SKG_CATALOG",
)


@pytest.fixture(autouse=True)
def clean_config_env(monkeypatch):
    for var in CONFIG_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


from skills_gateway.config import (
    load_config,
    validate_config,
    GatewayConfig,
    ServiceConfig,
    AuthConfig,
    SkillsConfig,
    ObservabilityConfig,
    ProfileDef,
    CatalogDef,
    VERSION,
)


class TestConfigDefaults:
    def test_default_auth_mode(self):
        env = dict(os.environ)
        env.pop("AUTH_MODE", None)
        with patch.dict(os.environ, env, clear=True):
            cfg = load_config(config_path="/dev/null")
            assert cfg.auth.mode in ("cloudflare-access", "dev-none")

    def test_default_host_port(self):
        cfg = load_config(config_path="/dev/null")
        assert cfg.service.host == "0.0.0.0"
        assert cfg.service.port == 8091

    def test_default_mcp_path(self):
        cfg = load_config(config_path="/dev/null")
        assert cfg.service.mcp_path == "/mcp"

    def test_default_version(self):
        assert VERSION == "0.1.0"


class TestConfigResolution:
    def test_env_overrides_default(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev-none"}):
            cfg = load_config(config_path="/dev/null")
            assert cfg.auth.mode == "dev-none"

    def test_cli_overrides_env(self):
        with patch.dict(os.environ, {"AUTH_MODE": "internal-only"}):
            cfg = load_config(config_path="/dev/null", cli_overrides={"auth_mode": "dev-none"})
            assert cfg.auth.mode == "dev-none"

    def test_env_host(self):
        with patch.dict(os.environ, {"HOST": "127.0.0.1"}):
            cfg = load_config(config_path="/dev/null")
            assert cfg.service.host == "127.0.0.1"

    def test_env_port(self):
        with patch.dict(os.environ, {"PORT": "9999"}):
            cfg = load_config(config_path="/dev/null")
            assert cfg.service.port == 9999

    def test_cli_skills_dir(self):
        cfg = load_config(config_path="/dev/null", cli_overrides={"skills_dir": "/tmp/test-skills"})
        assert cfg.skills.dir == "/tmp/test-skills"


class TestConfigYaml:
    def test_load_from_yaml(self, tmp_path):
        yaml_file = tmp_path / "skills-gateway.yaml"
        yaml_file.write_text(
            "service:\n"
            "  host: 0.0.0.0\n"
            "  port: 9999\n"
            "auth:\n"
            "  mode: dev-none\n"
        )
        cfg = load_config(config_path=str(yaml_file))
        assert cfg.service.port == 9999
        assert cfg.auth.mode == "dev-none"

    def test_yaml_profiles(self, tmp_path):
        yaml_file = tmp_path / "skills-gateway.yaml"
        yaml_file.write_text(
            "profiles:\n"
            "  test:\n"
            "    skills:\n"
            "      - skill-a\n"
            "      - skill-b\n"
        )
        cfg = load_config(config_path=str(yaml_file))
        assert "test" in cfg.profiles
        assert cfg.profiles["test"].skills == ["skill-a", "skill-b"]

    def test_yaml_catalogs(self, tmp_path):
        yaml_file = tmp_path / "skills-gateway.yaml"
        yaml_file.write_text(
            "catalogs:\n"
            "  local:\n"
            "    type: local\n"
            "    path: /tmp/skills\n"
        )
        cfg = load_config(config_path=str(yaml_file))
        assert "local" in cfg.catalogs
        assert cfg.catalogs["local"].type == "local"
        assert cfg.catalogs["local"].path == "/tmp/skills"

    def test_missing_yaml_uses_defaults(self):
        cfg = load_config(config_path="/nonexistent/path.yaml")
        assert cfg.service.port == 8091


class TestConfigValidation:
    def test_cf_access_missing_team_domain(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", public_base_url="https://example.com")
        )
        errors = validate_config(cfg)
        assert any("cloudflare_team_domain" in e for e in errors)

    def test_cf_access_missing_aud(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", cloudflare_team_domain="team.example.com", public_base_url="https://example.com")
        )
        errors = validate_config(cfg)
        assert any("cloudflare_aud" in e for e in errors)

    def test_dev_none_no_errors(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert not errors

    def test_invalid_auth_mode(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="invalid-mode"),
            skills=SkillsConfig(dir="/tmp"),
        )
        errors = validate_config(cfg)
        assert any("invalid-mode" in e for e in errors)

    def test_missing_skills_dir(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir="/nonexistent/path"),
        )
        errors = validate_config(cfg)
        assert any("does not exist" in e for e in errors)

    def test_invalid_port(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            service=ServiceConfig(port=0),
            skills=SkillsConfig(dir="/tmp"),
        )
        errors = validate_config(cfg)
        assert any("port" in e.lower() for e in errors)

    def test_unknown_active_profile(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir="/tmp"),
            active_profile="nonexistent",
        )
        errors = validate_config(cfg)
        assert any("active_profile" in e for e in errors)

    def test_unknown_active_catalog(self):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir="/tmp"),
            active_catalog="nonexistent",
        )
        errors = validate_config(cfg)
        assert any("active_catalog" in e for e in errors)
