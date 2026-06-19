from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from skills_gateway.config import (
    GatewayConfig,
    VERSION,
    load_config,
    validate_config,
    set_config,
)
from skills_gateway.skills import get_skills_catalog, parse_skill_frontmatter, get_skill_file_tree

app = typer.Typer(
    name="skills-gateway",
    help="Skills Gateway MCP Server — agent skills gateway CLI",
    no_args_is_help=True,
)


def _init_config(
    config: str | None = None,
    skills_dir: str | None = None,
    host: str | None = None,
    port: int | None = None,
    profile: str | None = None,
    catalog: str | None = None,
    auth_mode: str | None = None,
    public_base_url: str | None = None,
    mcp_path: str | None = None,
) -> GatewayConfig:
    cli_overrides = {}
    if skills_dir is not None:
        cli_overrides["skills_dir"] = skills_dir
    if host is not None:
        cli_overrides["host"] = host
    if port is not None:
        cli_overrides["port"] = port
    if profile is not None:
        cli_overrides["profile"] = profile
    if catalog is not None:
        cli_overrides["catalog"] = catalog
    if auth_mode is not None:
        cli_overrides["auth_mode"] = auth_mode
    if public_base_url is not None:
        cli_overrides["public_base_url"] = public_base_url
    if mcp_path is not None:
        cli_overrides["mcp_path"] = mcp_path

    cfg = load_config(config_path=config, cli_overrides=cli_overrides if cli_overrides else None)
    set_config(cfg)
    return cfg


ConfigOption = typer.Option(None, "--config", "-c", help="Config file path")
SkillsDirOption = typer.Option(None, "--skills-dir", help="Skills directory path")
HostOption = typer.Option(None, "--host", help="Bind host")
PortOption = typer.Option(None, "--port", help="Bind port")
ProfileOption = typer.Option(None, "--profile", "-p", help="Active profile name")
CatalogOption = typer.Option(None, "--catalog", help="Active catalog name")
AuthModeOption = typer.Option(None, "--auth-mode", help="Auth mode (cloudflare-access|dev-none|internal-only)")
PublicBaseURLOption = typer.Option(None, "--public-base-url", help="Public base URL for OAuth")
MCPPathOption = typer.Option(None, "--mcp-path", help="MCP endpoint path")


@app.command()
def run(
    config: str | None = ConfigOption,
    skills_dir: str | None = SkillsDirOption,
    host: str | None = HostOption,
    port: int | None = PortOption,
    profile: str | None = ProfileOption,
    catalog: str | None = CatalogOption,
    auth_mode: str | None = AuthModeOption,
    public_base_url: str | None = PublicBaseURLOption,
    mcp_path: str | None = MCPPathOption,
):
    """Start the Skills Gateway MCP server."""
    cfg = _init_config(
        config=config, skills_dir=skills_dir, host=host, port=port,
        profile=profile, catalog=catalog, auth_mode=auth_mode,
        public_base_url=public_base_url, mcp_path=mcp_path,
    )

    errors = validate_config(cfg)
    if cfg.auth.mode != "dev-none" and errors:
        for e in errors:
            typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(code=2)

    if cfg.auth.mode == "dev-none":
        typer.echo("WARNING: auth.mode=dev-none — no authentication enabled. NOT for production use!", err=True)

    from skills_gateway.server import run_with_config
    run_with_config(cfg)


@app.command()
def validate(
    config: str | None = ConfigOption,
    skills_dir: str | None = SkillsDirOption,
    auth_mode: str | None = AuthModeOption,
):
    """Validate configuration and skill manifests."""
    cfg = _init_config(config=config, skills_dir=skills_dir, auth_mode=auth_mode)

    config_errors = validate_config(cfg)
    all_errors = list(config_errors)

    skills_path = Path(cfg.skills.dir).expanduser()
    if skills_path.exists():
        from skills_gateway.skills import validate_skills
        skill_errors = validate_skills(skills_path)
        all_errors.extend(skill_errors)
    else:
        all_errors.append(f"skills.dir '{cfg.skills.dir}' does not exist")

    if all_errors:
        for e in all_errors:
            typer.echo(f"FAIL: {e}", err=True)
        raise typer.Exit(code=2)
    else:
        typer.echo("OK: all checks passed")


@app.command(name="list")
def list_skills(
    config: str | None = ConfigOption,
    skills_dir: str | None = SkillsDirOption,
    profile: str | None = ProfileOption,
    auth_mode: str | None = AuthModeOption,
):
    """List available skills."""
    cfg = _init_config(config=config, skills_dir=skills_dir, profile=profile, auth_mode=auth_mode)
    skills_path = Path(cfg.skills.dir).expanduser()
    catalog = get_skills_catalog(skills_path)

    if cfg.active_profile and cfg.active_profile in cfg.profiles:
        allowed = set(cfg.profiles[cfg.active_profile].skills)
        catalog = [s for s in catalog if s["name"] in allowed]

    if not catalog:
        typer.echo("No skills found")
        return

    for s in catalog:
        version = s.get("version", "?")
        typer.echo(f"  {s['name']}  ({version})  {s.get('description', '')}")


@app.command()
def inspect(
    skill_name: str = typer.Argument(..., help="Skill name to inspect"),
    config: str | None = ConfigOption,
    skills_dir: str | None = SkillsDirOption,
    auth_mode: str | None = AuthModeOption,
):
    """Inspect a single skill's metadata and file tree."""
    cfg = _init_config(config=config, skills_dir=skills_dir, auth_mode=auth_mode)
    skills_path = Path(cfg.skills.dir).expanduser()
    skill_dir = skills_path / skill_name

    if not skill_dir.exists() or not skill_dir.is_dir():
        typer.echo(f"Skill '{skill_name}' not found", err=True)
        raise typer.Exit(code=1)

    frontmatter = parse_skill_frontmatter(skill_dir)
    if not frontmatter:
        typer.echo(f"Skill '{skill_name}' has no valid SKILL.md", err=True)
        raise typer.Exit(code=1)

    tree = get_skill_file_tree(skill_dir)
    result = {"metadata": frontmatter, "file_tree": tree}
    typer.echo(json.dumps(result, indent=2))


@app.command()
def doctor(
    config: str | None = ConfigOption,
    skills_dir: str | None = SkillsDirOption,
    auth_mode: str | None = AuthModeOption,
):
    """Run diagnostic checks (config, auth, skills, readiness)."""
    cfg = _init_config(config=config, skills_dir=skills_dir, auth_mode=auth_mode)

    checks = {}

    config_errors = validate_config(cfg)
    checks["config"] = "ok" if not config_errors else f"failed: {'; '.join(config_errors)}"

    if cfg.auth.mode == "cloudflare-access":
        has_cf = bool(cfg.auth.cloudflare_team_domain and cfg.auth.cloudflare_aud)
        checks["auth_config"] = "ok" if has_cf else "failed: missing CLOUDFLARE_TEAM_DOMAIN or CLOUDFLARE_AUD"
    elif cfg.auth.mode == "dev-none":
        checks["auth_config"] = "ok (dev-none: no auth)"
    elif cfg.auth.mode == "internal-only":
        checks["auth_config"] = "ok (internal-only: Docker-internal bypass)"
    else:
        checks["auth_config"] = f"failed: unknown auth mode '{cfg.auth.mode}'"

    skills_path = Path(cfg.skills.dir).expanduser()
    checks["skills_dir"] = "ok" if skills_path.exists() else f"failed: {cfg.skills.dir} does not exist"

    if skills_path.exists():
        from skills_gateway.skills import validate_skills
        skill_errors = validate_skills(skills_path)
        checks["skills_scan"] = "ok" if not skill_errors else f"failed: {len(skill_errors)} invalid skill(s)"
    else:
        checks["skills_scan"] = "skipped (skills_dir missing)"

    all_ok = all(v == "ok" or v.startswith("ok ") for v in checks.values())
    status = "ready" if all_ok else "not_ready"

    typer.echo(f"Status: {status}")
    for name, result in checks.items():
        icon = "✓" if result == "ok" or result.startswith("ok ") else "✗"
        typer.echo(f"  {icon} {name}: {result}")

    if not all_ok:
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show version information."""
    typer.echo(f"skills-gateway {VERSION}")


def cli_main():
    app()


if __name__ == "__main__":
    cli_main()
