import os
from datetime import datetime, timezone
from pathlib import Path

from starlette.responses import JSONResponse, PlainTextResponse

from skills_gateway.config import GatewayConfig, VERSION, validate_config
from skills_gateway.skills import get_skills_catalog, validate_skills
from skills_gateway.metrics import metrics


BUILD_COMMIT = os.getenv("SKG_BUILD_COMMIT", "unknown")
BUILD_TIME = os.getenv("SKG_BUILD_TIME", "unknown")


def register_routes(mcp, cfg: GatewayConfig):
    base_url = (cfg.auth.public_base_url or "https://skills.astatide.com").rstrip("/")
    mcp_path = cfg.service.mcp_path

    @mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
    async def oauth_authorization_server_metadata(request):
        return JSONResponse({
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "registration_endpoint": f"{base_url}/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
            "code_challenge_methods_supported": ["S256"],
        }, headers={"Cache-Control": "public, max-age=3600"})

    @mcp.custom_route("/.well-known/oauth-protected-resource/mcp", methods=["GET"])
    async def oauth_protected_resource_metadata(request):
        return JSONResponse({
            "resource": f"{base_url}{mcp_path}",
            "authorization_servers": [base_url],
            "scopes_supported": ["mcp"],
            "bearer_methods_supported": ["header"],
        }, headers={"Cache-Control": "public, max-age=3600"})

    @mcp.custom_route("/health", methods=["GET"])
    async def health(request):
        return JSONResponse({
            "status": "alive",
            "service": "skills-gateway",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @mcp.custom_route("/ready", methods=["GET"])
    async def ready(request):
        checks = {}
        skills_path = Path(cfg.skills.dir).expanduser()
        all_ok = True

        if skills_path.exists() and os.access(skills_path, os.R_OK):
            checks["skills_dir"] = "ok"
        else:
            checks["skills_dir"] = f"failed: {cfg.skills.dir} not accessible"
            all_ok = False

        try:
            catalog = get_skills_catalog(skills_path)
            checks["skills_scan"] = "ok"
        except Exception as e:
            checks["skills_scan"] = f"failed: {e}"
            all_ok = False

        config_errors = validate_config(cfg)
        if config_errors:
            checks["auth_config"] = f"failed: {config_errors[0]}"
            all_ok = False
        else:
            checks["auth_config"] = "ok"

        status_code = 200 if all_ok else 503
        body = {
            "status": "ready" if all_ok else "not_ready",
            "service": "skills-gateway",
            "checks": checks,
            "auth_mode": cfg.auth.mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(body, status_code=status_code)

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request):
        return JSONResponse({
            "service": "skills-gateway",
            "version": VERSION,
            "commit": BUILD_COMMIT,
            "build_time": BUILD_TIME,
        })

    @mcp.custom_route("/inventory", methods=["GET"])
    async def inventory(request):
        skills_path = Path(cfg.skills.dir).expanduser()
        catalog = get_skills_catalog(skills_path)
        result = validate_skills(skills_path)
        resources_count = 0
        if skills_path.exists():
            for _ in skills_path.rglob("*"):
                resources_count += 1
        return JSONResponse({
            "service": "skills-gateway",
            "type": "skills",
            "skills_count": len(catalog),
            "skills_invalid_count": len(result["errors"]),
            "skills_warnings_count": len(result["warnings"]),
            "resources_count": resources_count,
            "tools": ["skills_list", "skills_search", "skills_inspect", "skill_read"],
            "profiles": list(cfg.profiles.keys()),
            "active_profile": cfg.active_profile,
            "auth_mode": cfg.auth.mode,
            "catalogs": list(cfg.catalogs.keys()),
            "active_catalog": cfg.active_catalog,
        })

    @mcp.custom_route("/metrics", methods=["GET"])
    async def metrics_endpoint(request):
        if not cfg.observability.metrics_enabled:
            return PlainTextResponse("# metrics disabled\n", status_code=404)

        skills_path = Path(cfg.skills.dir).expanduser()
        catalog = get_skills_catalog(skills_path)
        result = validate_skills(skills_path)

        metrics.set_gauge("skills_gateway_up", 1)
        metrics.set_gauge("skills_gateway_ready", 1)
        metrics.set_gauge("skills_total", len(catalog))
        metrics.set_gauge("skills_invalid_total", len(result["errors"]))

        return PlainTextResponse(metrics.expose(), media_type="text/plain; version=0.0.4")

    @mcp.custom_route("/docs", methods=["GET"])
    async def docs_index(request):
        return JSONResponse({
            "service": "skills-gateway",
            "docs": {
                "config": "/docs/config",
                "profiles": "/docs/profiles",
                "catalogs": "/docs/catalogs",
                "auth": "/docs/auth",
                "health": "/health",
                "ready": "/ready",
                "version": "/version",
                "inventory": "/inventory",
                "metrics": "/metrics",
            },
        })

    @mcp.custom_route("/docs/config", methods=["GET"])
    async def docs_config(request):
        return JSONResponse({
            "service": "skills-gateway",
            "config": {
                "service": {"host": cfg.service.host, "port": cfg.service.port, "mcp_path": cfg.service.mcp_path},
                "auth": {"mode": cfg.auth.mode, "internal_bypass": cfg.auth.internal_bypass},
                "skills": {"dir": cfg.skills.dir},
                "observability": {"log_level": cfg.observability.log_level, "log_format": cfg.observability.log_format, "metrics_enabled": cfg.observability.metrics_enabled},
                "environment": cfg.environment,
            },
        })

    @mcp.custom_route("/docs/profiles", methods=["GET"])
    async def docs_profiles(request):
        profiles_data = {name: {"skills": pdef.skills} for name, pdef in cfg.profiles.items()}
        return JSONResponse({
            "service": "skills-gateway",
            "profiles": profiles_data,
            "active_profile": cfg.active_profile,
        })

    @mcp.custom_route("/docs/catalogs", methods=["GET"])
    async def docs_catalogs(request):
        catalogs_data = {name: {"type": cdef.type, "path": cdef.path} for name, cdef in cfg.catalogs.items()}
        return JSONResponse({
            "service": "skills-gateway",
            "catalogs": catalogs_data,
            "active_catalog": cfg.active_catalog,
        })

    @mcp.custom_route("/docs/auth", methods=["GET"])
    async def docs_auth(request):
        return JSONResponse({
            "service": "skills-gateway",
            "auth": {
                "mode": cfg.auth.mode,
                "internal_bypass": cfg.auth.internal_bypass,
                "public_base_url": cfg.auth.public_base_url,
            },
        })
