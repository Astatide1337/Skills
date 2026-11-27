import json
from pathlib import Path

DEFAULTS = {"timeout": 10, "retries": 3}


def load(path: str | Path) -> dict:
    """Read a config file and fill in defaults."""
    return {**DEFAULTS, **json.loads(Path(path).read_text())}
