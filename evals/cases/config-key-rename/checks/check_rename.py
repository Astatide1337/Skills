"""request_timeout_s is the key; timeout still loads with a warning; nothing else reads `timeout`."""

import json
import logging
import re
import sys
import tempfile
import warnings
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, ".")
from fetcher import config
from fetcher.client import Client
from fetcher.health import health_check_args
from fetcher.retry import total_budget


def load(data):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.json"
        p.write_text(json.dumps(data))
        return config.load(p)


def readers_agree(cfg, seconds):
    return (
        Client(cfg).request_args("/a")["timeout"] == seconds
        and health_check_args(cfg)["timeout"] == seconds / 2
        and total_budget(cfg) == seconds * (cfg["retries"] + 1)
    )


with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    new = load({"base_url": "http://x", "request_timeout_s": 6})
if not readers_agree(new, 6):
    sys.exit("request_timeout_s is not honoured by every reader")
if caught:
    sys.exit(f"new key warned: {caught[0].message}")


class Capture(logging.Handler):
    records: ClassVar[list] = []

    def emit(self, record):
        if record.levelno >= logging.WARNING:
            self.records.append(record)


logging.getLogger().addHandler(Capture())
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    old = load({"base_url": "http://x", "timeout": 8})
if not readers_agree(old, 8):
    sys.exit("old `timeout` key is no longer honoured")
if not (caught or Capture.records):
    sys.exit("old `timeout` key loaded without any warning")

offenders = []
for f in Path("fetcher").rglob("*.py"):
    if f.name == "config.py":
        continue
    if re.search(
        r"""\[\s*["']timeout["']\s*\]|\.get\(\s*["']timeout["']""", f.read_text()
    ):
        offenders.append(str(f))
example = json.loads(Path("config.example.json").read_text())
if "timeout" in example or "request_timeout_s" not in example:
    offenders.append("config.example.json")
if offenders:
    sys.exit(f"still using the old key: {offenders}")
print("rename ok")
