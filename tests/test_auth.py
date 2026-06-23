import pytest
from skills_gateway.config import GatewayConfig, ServiceConfig, AuthConfig, SkillsConfig, validate_config


class TestAuthModes:
    def test_dev_none_mode_valid(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert errors == []

    def test_cloudflare_access_missing_team_domain(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", cloudflare_team_domain=None),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert any("cloudflare_team_domain" in e for e in errors)

    def test_cloudflare_access_missing_aud(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", cloudflare_team_domain="test.example.com", cloudflare_aud=None),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert any("cloudflare_aud" in e for e in errors)

    def test_cloudflare_access_valid(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", cloudflare_team_domain="test.example.com", cloudflare_aud="test-aud", public_base_url="https://example.com"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert errors == []

    def test_internal_only_mode_valid(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="internal-only", cloudflare_team_domain="test.example.com", cloudflare_aud="test-aud", public_base_url="https://example.com"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert errors == []

    def test_invalid_auth_mode(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="invalid-mode"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        errors = validate_config(cfg)
        assert any("not valid" in e for e in errors)

    def test_internal_bypass_flag(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="cloudflare-access", internal_bypass=True, cloudflare_team_domain="test.example.com", cloudflare_aud="test-aud", public_base_url="https://example.com"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        assert cfg.auth.internal_bypass is True

    def test_auth_mode_visible_in_inventory(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        from skills_gateway.server import create_app
        mcp = create_app(cfg)
        app = mcp.http_app(transport="streamable-http")
        from starlette.testclient import TestClient
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/inventory")
        assert resp.json()["auth_mode"] == "dev-none"

    def test_auth_mode_visible_in_ready(self, tmp_path):
        cfg = GatewayConfig(
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        from skills_gateway.server import create_app
        mcp = create_app(cfg)
        app = mcp.http_app(transport="streamable-http")
        from starlette.testclient import TestClient
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/ready")
        assert resp.json()["auth_mode"] == "dev-none"
