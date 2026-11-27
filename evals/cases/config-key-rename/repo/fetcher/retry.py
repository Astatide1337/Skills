def total_budget(config: dict) -> float:
    """Worst-case seconds spent on one fetch including retries."""
    return config["timeout"] * (config["retries"] + 1)
