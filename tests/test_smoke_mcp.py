import json
import pytest
import anyio
from starlette.testclient import TestClient

from skills_gateway.config import GatewayConfig, ServiceConfig, AuthConfig, SkillsConfig
from skills_gateway.server import create_app
from skills_gateway.metrics import metrics

_fastmcp_client_available = False
try:
    from fastmcp.client import Client
    _fastmcp_client_available = True
except ImportError:
    pass


_SKILL_FIXTURES = {
    "echo-tool": """---
name: Echo Tool
description: A simple echo utility skill
metadata:
  version: "1.0.0"
risk_level: low
tags:
  - utility
---
# Echo Tool

Returns whatever you pass in.
""",
    "file-lister": """---
name: File Lister
description: Lists files in a directory
metadata:
  version: "1.1.0"
risk_level: medium
tags:
  - filesystem
  - utility
---
# File Lister

Lists files in the provided path.
""",
    "secret-scanner": """---
name: Secret Scanner
description: Scans for secrets in code
metadata:
  version: "0.5.0"
risk_level: high
tags:
  - security
---
# Secret Scanner

Scans code for hardcoded secrets.
""",
}


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    for var in (
        "CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR",
        "SKG_CONFIG", "SKG_BUILD_COMMIT", "SKG_BUILD_TIME",
    ):
        monkeypatch.delenv(var, raising=False)
    for skill_name, content in _SKILL_FIXTURES.items():
        d = tmp_path / skill_name
        d.mkdir()
        (d / "SKILL.md").write_text(content)
    return tmp_path


@pytest.fixture
def app(skills_dir):
    metrics.reset()
    cfg = GatewayConfig(
        service=ServiceConfig(),
        auth=AuthConfig(mode="dev-none"),
        skills=SkillsConfig(dir=str(skills_dir)),
    )
    mcp = create_app(cfg)
    return mcp


@pytest.fixture
def http_client(app):
    starlette_app = app.http_app(transport="streamable-http")
    return TestClient(starlette_app, raise_server_exceptions=False)


class TestRestSmoke:
    def test_health_endpoint(self, http_client):
        response = http_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "skills-gateway"

    def test_inventory_endpoint(self, http_client):
        response = http_client.get("/inventory")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "skills-gateway"
        assert data["type"] == "skills"
        assert data["skills_count"] == len(_SKILL_FIXTURES)
        expected_tools = {"skills_list", "skills_search", "skills_inspect", "skill_read"}
        assert set(data["tools"]) == expected_tools
        assert data["skills_invalid_count"] == 0

    def test_skills_endpoint(self, http_client):
        response = http_client.get("/skills")
        assert response.status_code == 200
        data = response.json()
        skill_names = {s["name"] for s in data.get("skills", [])}
        assert skill_names == {"Echo Tool", "File Lister", "Secret Scanner"}

    def test_ready_endpoint(self, http_client):
        response = http_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_version_endpoint(self, http_client):
        response = http_client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "skills-gateway"

    def test_metrics_endpoint(self, http_client):
        response = http_client.get("/metrics")
        assert response.status_code == 200
        assert "skills_gateway_up" in response.text


class TestMcpSmoke:
    @pytest.mark.skipif(not _fastmcp_client_available,
                        reason="fastmcp.client.Client unavailable in FastMCP 2.14.7")
    async def _run_client_checks(self, app):
        async with Client(app, auto_initialize=True) as client:
            result = await client.call_tool("skills_list")
            data = json.loads(result.data)
            assert len(data) == len(_SKILL_FIXTURES)
            names = {s["name"] for s in data}
            assert names == {"Echo Tool", "File Lister", "Secret Scanner"}
            for s in data:
                assert "id" in s
                assert "name" in s
                assert "description" in s
                assert "risk_level" in s

            result = await client.call_tool("skills_search", arguments={"query": "file"})
            data = json.loads(result.data)
            assert len(data) >= 1
            assert "File Lister" in {s["name"] for s in data}

            result = await client.call_tool("skills_search", arguments={"query": "secret"})
            data = json.loads(result.data)
            assert len(data) >= 1
            assert "Secret Scanner" in {s["name"] for s in data}

            result = await client.call_tool("skills_search", arguments={"query": "nonexistent"})
            data = json.loads(result.data)
            assert data == []

            result = await client.call_tool("skills_inspect", arguments={"name": "echo-tool"})
            data = json.loads(result.data)
            assert "manifest" in data
            assert data["manifest"]["id"] == "echo-tool"
            assert data["manifest"]["name"] == "Echo Tool"
            assert data["manifest"]["entrypoint"] == "SKILL.md"
            assert "SKILL.md" in data["file_tree"]
            assert data["metadata"]["risk_level"] == "low"

            result = await client.call_tool("skills_inspect", arguments={"name": "secret-scanner"})
            data = json.loads(result.data)
            assert data["manifest"]["name"] == "Secret Scanner"
            assert data["metadata"]["risk_level"] == "high"

            result = await client.call_tool("skills_inspect", arguments={"name": "nonexistent"})
            data = json.loads(result.data)
            assert "error" in data
            assert data["error"]["code"] == "not_found"

            result = await client.call_tool("skill_read", arguments={"path": "echo-tool/SKILL.md"})
            assert isinstance(result.data, str)
            assert "Echo Tool" in result.data

            result = await client.call_tool("skill_read", arguments={"path": "file-lister/SKILL.md"})
            assert "File Lister" in result.data

            result = await client.call_tool("skill_read", arguments={"path": "echo-tool/nonexistent.py"})
            data = json.loads(result.data)
            assert data["error"]["code"] == "not_found"

            result = await client.call_tool("skill_read", arguments={"path": "../etc/passwd"})
            data = json.loads(result.data)
            assert data["error"]["code"] == "invalid_path"

            result = await client.call_tool("skill_read", arguments={"path": "echo-tool/../../secret.txt"})
            data = json.loads(result.data)
            assert data["error"]["code"] == "invalid_path"

    @pytest.mark.skipif(not _fastmcp_client_available,
                        reason="fastmcp.client.Client unavailable in FastMCP 2.14.7")
    def test_all_mcp_tools(self, app):
        anyio.run(self._run_client_checks, app)


class TestMcpInitialization:
    def test_app_creates_without_error(self, skills_dir):
        metrics.reset()
        cfg = GatewayConfig(
            service=ServiceConfig(),
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(skills_dir)),
        )
        mcp = create_app(cfg)
        assert mcp.name == "Skills Gateway"

    def test_app_creates_with_empty_skills_dir(self, tmp_path, monkeypatch):
        for var in (
            "CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR",
            "SKG_CONFIG",
        ):
            monkeypatch.delenv(var, raising=False)
        metrics.reset()
        cfg = GatewayConfig(
            service=ServiceConfig(),
            auth=AuthConfig(mode="dev-none"),
            skills=SkillsConfig(dir=str(tmp_path)),
        )
        mcp = create_app(cfg)
        assert mcp.name == "Skills Gateway"
        starlette_app = mcp.http_app(transport="streamable-http")
        client = TestClient(starlette_app, raise_server_exceptions=False)
        response = client.get("/inventory")
        assert response.status_code == 200
        assert response.json()["skills_count"] == 0
        assert response.json()["skills_invalid_count"] == 0

    @pytest.mark.skipif(not _fastmcp_client_available,
                        reason="fastmcp.client.Client unavailable in FastMCP 2.14.7")
    def test_mcp_initialize_protocol(self, app):
        async def run():
            async with Client(app, auto_initialize=True) as client:
                assert client.is_connected()
                assert client.initialize_result is not None
                tools = await client.list_tools()
                tool_names = {t.name for t in tools}
                expected = {"skills_list", "skills_search", "skills_inspect", "skill_read"}
                assert tool_names == expected

        anyio.run(run)

    @pytest.mark.skipif(not _fastmcp_client_available,
                        reason="fastmcp.client.Client unavailable in FastMCP 2.14.7")
    def test_mcp_list_tools(self, app):
        async def run():
            async with Client(app, auto_initialize=True) as client:
                tools = await client.list_tools()
                tool_map = {t.name: t for t in tools}
                assert tool_map["skills_list"].description == "List all available skills with full metadata."
                schema = tool_map["skills_search"].inputSchema
                assert "query" in schema.get("properties", {})
                schema = tool_map["skills_inspect"].inputSchema
                assert "name" in schema.get("properties", {})
                schema = tool_map["skill_read"].inputSchema
                assert "path" in schema.get("properties", {})

        anyio.run(run)
