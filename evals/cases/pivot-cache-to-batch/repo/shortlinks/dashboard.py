from shortlinks.db import Database
from shortlinks.resolver import resolve


def render(db: Database, codes: list[str]) -> str:
    return "\n".join(f"{code} -> {resolve(db, code) or '(missing)'}" for code in codes)
