def health_check_args(config: dict) -> dict:
    # Health checks should fail fast: half the normal request timeout.
    return {"url": config["base_url"] + "/health", "timeout": config["timeout"] / 2}
