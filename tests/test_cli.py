import pytest
from typer.testing import CliRunner

from skills_gateway.cli import app


runner = CliRunner()

CF_ENV_VARS = ("CLOUDFLARE_TEAM_DOMAIN", "CLOUDFLARE_AUD", "AUTH_MODE", "SKILLS_DIR", "SKG_CONFIG")


class TestVersionCommand:
    def test_version_output(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestValidateCommand:
    def test_validate_dev_none(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["validate", "--config", "/dev/null", "--auth-mode", "dev-none", "--skills-dir", "/tmp"])
        assert result.exit_code == 0
        assert "OK" in result.stdout

    def test_validate_missing_cf_creds(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["validate", "--config", "/dev/null", "--auth-mode", "cloudflare-access", "--skills-dir", "/tmp"])
        assert result.exit_code == 2


class TestListCommand:
    def test_list_with_skills(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["list", "--config", "/dev/null", "--auth-mode", "dev-none", "--skills-dir", "/home/ubuntu/skills"])
        assert result.exit_code == 0
        assert "react-best-practices" in result.stdout or "distributed-tracing" in result.stdout

    def test_list_empty_dir(self, tmp_path, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["list", "--config", "/dev/null", "--auth-mode", "dev-none", "--skills-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No skills found" in result.stdout


class TestInspectCommand:
    def test_inspect_existing_skill(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["inspect", "react-best-practices", "--config", "/dev/null", "--skills-dir", "/home/ubuntu/skills"])
        assert result.exit_code == 0
        assert "vercel-react-best-practices" in result.stdout

    def test_inspect_nonexistent_skill(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["inspect", "nonexistent-skill", "--config", "/dev/null", "--skills-dir", "/tmp"])
        assert result.exit_code == 1


class TestDoctorCommand:
    def test_doctor_dev_none(self, monkeypatch):
        for var in CF_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        result = runner.invoke(app, ["doctor", "--config", "/dev/null", "--auth-mode", "dev-none", "--skills-dir", "/tmp"])
        assert "config: ok" in result.stdout
