from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from skills_gateway.config import (
    GatewayConfig,
    load_config,
    set_config,
    validate_config,
)
from skills_gateway.auth import CloudflareAccessOAuthProvider, apply_auth_patches
from skills_gateway.logging import setup_logging, log_event
from skills_gateway.resources import register_resources
from skills_gateway.tools import register_tools
from skills_gateway.routes import register_routes


def create_app(cfg: GatewayConfig) -> FastMCP:
    auth = None
    if cfg.auth.mode == "cloudflare-access":
        from skills_gateway.auth import CloudflareAccessOAuthProvider
        auth = CloudflareAccessOAuthProvider(cfg)
    elif cfg.auth.mode == "dev-none":
        auth = None
    elif cfg.auth.mode == "internal-only":
        from skills_gateway.auth import CloudflareAccessOAuthProvider
        auth = CloudflareAccessOAuthProvider(cfg)

    if auth is not None:
        apply_auth_patches()

    mcp = FastMCP("Skills Gateway", auth=auth)

    skills_path = Path(cfg.skills.dir).expanduser()

    log_event("skill_scan_started", f"Scanning skills directory: {skills_path}")
    register_resources(mcp, skills_path)
    register_tools(mcp, skills_path, cfg)
    from skills_gateway.skills import get_skills_catalog, validate_skills
    catalog = get_skills_catalog(skills_path)
    skill_errors = validate_skills(skills_path)
    log_event("skill_scan_completed", f"Found {len(catalog)} skills, {len(skill_errors)} invalid", skills_count=len(catalog), skills_invalid_count=len(skill_errors))
    for err in skill_errors:
        log_event("skill_invalid", err, level="WARNING")

    log_event("auth_mode_set", f"Auth mode: {cfg.auth.mode}", auth_mode=cfg.auth.mode)
    if cfg.active_profile:
        log_event("profile_set", f"Active profile: {cfg.active_profile}", profile=cfg.active_profile)
    if cfg.active_catalog:
        log_event("catalog_set", f"Active catalog: {cfg.active_catalog}", catalog=cfg.active_catalog)

    if cfg.observability.metrics_enabled:
        from starlette.middleware import Middleware
        from skills_gateway.metrics import MetricsMiddleware
        mcp.add_middleware(Middleware(MetricsMiddleware))

    register_routes(mcp, cfg)

    from skills_gateway.metrics import metrics
    metrics.set_gauge("skills_gateway_up", 1)

    return mcp


def run_with_config(cfg: GatewayConfig):
    setup_logging(
        log_level=cfg.observability.log_level,
        log_format=cfg.observability.log_format,
        environment=cfg.environment,
    )

    log_event("service_start", "Skills Gateway starting", host=cfg.service.host, port=cfg.service.port, auth_mode=cfg.auth.mode)

    errors = validate_config(cfg)
    if cfg.auth.mode != "dev-none" and errors:
        for e in errors:
            log_event("config_error", e, level="ERROR")
        raise SystemExit(2)

    if cfg.auth.mode == "dev-none":
        log_event("auth_warning", "auth.mode=dev-none — no authentication. NOT for production use!", level="WARNING")

    mcp = create_app(cfg)

    log_event("service_ready", "Skills Gateway ready to serve requests")

    mcp.run(
        transport="streamable-http",
        host=cfg.service.host,
        port=cfg.service.port,
        path=cfg.service.mcp_path,
    )


def main():
    cfg = load_config()
    set_config(cfg)
    run_with_config(cfg)


if __name__ == "__main__":
    main()
