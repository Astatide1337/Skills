import pytest
from starlette.testclient import TestClient

from skills_gateway.config import GatewayConfig, ServiceConfig, AuthConfig, SkillsConfig
from skills_gateway.server import create_app
from skills_gateway.metrics import metrics


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    for var in ("CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR", "SKG_CONFIG", "SKG_BUILD_COMMIT", "SKG_BUILD_TIME"):
        monkeypatch.delenv(var, raising=False)
    metrics.reset()
    cfg = GatewayConfig(
        service=ServiceConfig(),
        auth=AuthConfig(mode="dev-none"),
        skills=SkillsConfig(dir=str(tmp_path)),
    )
    mcp = create_app(cfg)
    app = mcp.http_app(transport="streamable-http")
    client = TestClient(app, raise_server_exceptions=False)
    return client


@pytest.fixture
def app_client_with_skills(monkeypatch):
    for var in ("CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR", "SKG_CONFIG"):
        monkeypatch.delenv(var, raising=False)
    metrics.reset()
    cfg = GatewayConfig(
        service=ServiceConfig(),
        auth=AuthConfig(mode="dev-none"),
        skills=SkillsConfig(dir="/home/ubuntu/skills"),
    )
    mcp = create_app(cfg)
    app = mcp.http_app(transport="streamable-http")
    client = TestClient(app, raise_server_exceptions=False)
    return client


class TestHealthEndpoint:
    def test_health_returns_200(self, app_client):
        response = app_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "skills-gateway"
        assert "timestamp" in data


class TestReadinessEndpoint:
    def test_ready_when_config_valid(self, app_client):
        response = app_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["skills_dir"] == "ok"
        assert data["checks"]["skills_scan"] == "ok"
        assert data["checks"]["auth_config"] == "ok"
        assert data["auth_mode"] == "dev-none"

    def test_not_ready_missing_skills_dir(self, monkeypatch):
        for var in ("CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR", "SKG_CONFIG"):
            monkeypatch.delenv(var, raising=False)
        metrics.reset()
        cfg = GatewayConfig(
            service=ServiceConfig(),
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir="/nonexistent/path"),
        )
        mcp = create_app(cfg)
        app = mcp.http_app(transport="streamable-http")
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"


class TestVersionEndpoint:
    def test_version_returns_info(self, app_client):
        response = app_client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "skills-gateway"
        assert data["version"] == "0.1.0"
        assert "commit" in data
        assert "build_time" in data


class TestInventoryEndpoint:
    def test_inventory_empty(self, app_client):
        response = app_client.get("/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "skills-gateway"
        assert data["type"] == "skills"
        assert "skills_count" in data
        assert "tools" in data

    def test_inventory_with_skills(self, app_client_with_skills):
        response = app_client_with_skills.get("/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data["skills_count"] > 0
        assert "skills_list" in data["tools"]


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus(self, app_client):
        response = app_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        text = response.text
        assert "skills_gateway_up" in text
        assert "skills_total" in text


class TestDocsEndpoints:
    def test_docs_index(self, app_client):
        response = app_client.get("/docs")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "skills-gateway"
        assert "docs" in data
        assert data["docs"]["health"] == "/health"
        assert data["docs"]["ready"] == "/ready"

    def test_docs_config(self, app_client):
        response = app_client.get("/docs/config")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_docs_profiles(self, app_client):
        response = app_client.get("/docs/profiles")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data

    def test_docs_catalogs(self, app_client):
        response = app_client.get("/docs/catalogs")
        assert response.status_code == 200
        data = response.json()
        assert "catalogs" in data

    def test_docs_auth(self, app_client):
        response = app_client.get("/docs/auth")
        assert response.status_code == 200
        data = response.json()
        assert "auth" in data
        assert data["auth"]["mode"] == "dev-none"
