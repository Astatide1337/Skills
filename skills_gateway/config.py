from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.1.0"
DEFAULT_CONFIG_FILENAME = "skills-gateway.yaml"


@dataclass
class ServiceConfig:
    host: str = "0.0.0.0"
    port: int = 8091
    mcp_path: str = "/mcp"


@dataclass
class AuthConfig:
    mode: str = "cloudflare-access"
    cloudflare_team_domain: Optional[str] = None
    cloudflare_aud: Optional[str] = None
    public_base_url: Optional[str] = None
    internal_bypass: bool = False


@dataclass
class SkillsConfig:
    dir: str = os.path.expanduser("~/skills")


@dataclass
class ObservabilityConfig:
    log_level: str = "INFO"
    log_format: str = "json"
    metrics_enabled: bool = True


@dataclass
class ProfileDef:
    skills: list[str] = field(default_factory=list)


@dataclass
class CatalogDef:
    type: str = "local"
    path: str = ""


@dataclass
class GatewayConfig:
    service: ServiceConfig = field(default_factory=ServiceConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    profiles: dict[str, ProfileDef] = field(default_factory=dict)
    active_profile: Optional[str] = None
    catalogs: dict[str, CatalogDef] = field(default_factory=dict)
    active_catalog: Optional[str] = None
    environment: str = "production"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    config_path: Optional[str] = None,
    cli_overrides: Optional[dict] = None,
) -> GatewayConfig:
    if config_path is None:
        config_path = os.getenv("SKG_CONFIG", DEFAULT_CONFIG_FILENAME)

    yaml_data = _load_yaml(Path(config_path))

    auth_section = yaml_data.get("auth", {})
    auth_mode = (
        (cli_overrides or {}).get("auth_mode")
        or os.getenv("AUTH_MODE")
        or auth_section.get("mode")
        or "cloudflare-access"
    )

    public_base_url = (
        (cli_overrides or {}).get("public_base_url")
        or os.getenv("PUBLIC_BASE_URL")
        or auth_section.get("public_base_url")
        or "https://skills.astatide.com"
    )

    cf_team = (
        os.getenv("CLOUDFLARE_TEAM_DOMAIN")
        or auth_section.get("cloudflare_team_domain")
    )

    cf_aud = (
        os.getenv("CLOUDFLARE_AUD")
        or auth_section.get("cloudflare_aud")
    )

    internal_bypass = (
        auth_section.get("internal_bypass", False)
        if auth_mode in ("cloudflare-access", "internal-only")
        else False
    )
    if os.getenv("INTERNAL_BYPASS", "").lower() in ("true", "1", "yes"):
        internal_bypass = True

    service_section = yaml_data.get("service", {})
    host = (
        (cli_overrides or {}).get("host")
        or os.getenv("HOST")
        or service_section.get("host")
        or "0.0.0.0"
    )
    port = int(
        (cli_overrides or {}).get("port")
        or os.getenv("PORT")
        or service_section.get("port")
        or 8091
    )
    mcp_path = (
        (cli_overrides or {}).get("mcp_path")
        or os.getenv("MCP_PATH")
        or service_section.get("mcp_path")
        or "/mcp"
    )

    skills_section = yaml_data.get("skills", {})
    skills_dir = (
        (cli_overrides or {}).get("skills_dir")
        or os.getenv("SKILLS_DIR")
        or skills_section.get("dir")
        or os.path.expanduser("~/skills")
    )

    obs_section = yaml_data.get("observability", {})
    log_level = (
        os.getenv("LOG_LEVEL")
        or obs_section.get("log_level")
        or "INFO"
    )
    log_format = (
        os.getenv("LOG_FORMAT")
        or obs_section.get("log_format")
        or "json"
    )
    metrics_enabled = (
        os.getenv("METRICS_ENABLED", "").lower() in ("true", "1", "yes")
        if os.getenv("METRICS_ENABLED", "")
        else obs_section.get("metrics_enabled", True)
    )

    profiles_raw = yaml_data.get("profiles", {})
    profiles = {}
    for name, pdef in profiles_raw.items():
        if isinstance(pdef, dict) and "skills" in pdef:
            profiles[name] = ProfileDef(skills=list(pdef["skills"]))

    active_profile = (
        (cli_overrides or {}).get("profile")
        or os.getenv("SKG_PROFILE")
        or yaml_data.get("active_profile")
        or None
    )

    catalogs_raw = yaml_data.get("catalogs", {})
    catalogs = {}
    for name, cdef in catalogs_raw.items():
        if isinstance(cdef, dict):
            catalogs[name] = CatalogDef(
                type=cdef.get("type", "local"),
                path=cdef.get("path", ""),
            )

    active_catalog = (
        (cli_overrides or {}).get("catalog")
        or os.getenv("SKG_CATALOG")
        or yaml_data.get("active_catalog")
        or None
    )

    environment = (
        os.getenv("SKG_ENVIRONMENT")
        or "production"
    )

    return GatewayConfig(
        service=ServiceConfig(host=host, port=port, mcp_path=mcp_path),
        auth=AuthConfig(
            mode=auth_mode,
            cloudflare_team_domain=cf_team,
            cloudflare_aud=cf_aud,
            public_base_url=public_base_url,
            internal_bypass=internal_bypass,
        ),
        skills=SkillsConfig(dir=skills_dir),
        observability=ObservabilityConfig(
            log_level=log_level,
            log_format=log_format,
            metrics_enabled=metrics_enabled,
        ),
        profiles=profiles,
        active_profile=active_profile,
        catalogs=catalogs,
        active_catalog=active_catalog,
        environment=environment,
    )


def validate_config(cfg: GatewayConfig) -> list[str]:
    errors = []
    if cfg.auth.mode == "cloudflare-access":
        if not cfg.auth.cloudflare_team_domain:
            errors.append("auth.cloudflare_team_domain is required for cloudflare-access mode")
        if not cfg.auth.cloudflare_aud:
            errors.append("auth.cloudflare_aud is required for cloudflare-access mode")
        if not cfg.auth.public_base_url:
            errors.append("auth.public_base_url is required for cloudflare-access mode")
    if cfg.auth.mode not in ("cloudflare-access", "dev-none", "internal-only"):
        errors.append(f"auth.mode '{cfg.auth.mode}' is not valid (must be cloudflare-access, dev-none, or internal-only)")
    if cfg.service.port < 1 or cfg.service.port > 65535:
        errors.append(f"service.port {cfg.service.port} is out of range")
    if not Path(cfg.skills.dir).expanduser().exists():
        errors.append(f"skills.dir '{cfg.skills.dir}' does not exist")
    if cfg.active_profile and cfg.active_profile not in cfg.profiles:
        errors.append(f"active_profile '{cfg.active_profile}' not defined in profiles")
    if cfg.active_catalog and cfg.active_catalog not in cfg.catalogs:
        errors.append(f"active_catalog '{cfg.active_catalog}' not defined in catalogs")
    for catalog_name, catalog_def in cfg.catalogs.items():
        if catalog_def.type != "local":
            errors.append(f"catalog '{catalog_name}' has unsupported type '{catalog_def.type}'")
        elif catalog_def.path and not Path(catalog_def.path).expanduser().exists():
            errors.append(f"catalog '{catalog_name}' path '{catalog_def.path}' does not exist")
    return errors


_config: Optional[GatewayConfig] = None


def get_config(**kwargs) -> GatewayConfig:
    global _config
    if _config is None:
        _config = load_config(**kwargs)
    return _config


def set_config(cfg: GatewayConfig) -> None:
    global _config
    _config = cfg
