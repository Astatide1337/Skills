"""resolve_many must use one query; the dashboard must use one query for many codes."""

import sys

sys.path.insert(0, ".")
from shortlinks import resolver
from shortlinks.dashboard import render
from shortlinks.db import Database

db = Database()
codes = [f"c{i}" for i in range(50)]
for code in codes[:40]:
    db.add(code, f"https://{code}.example")
if not hasattr(resolver, "resolve_many"):
    sys.exit("resolve_many missing")
before = db.queries
result = resolver.resolve_many(db, codes)
if db.queries - before != 1:
    sys.exit(f"resolve_many made {db.queries - before} queries")
lookup = result if isinstance(result, dict) else dict(zip(codes, result))
if lookup.get("c3") != "https://c3.example" or lookup.get("c45") is not None:
    sys.exit("resolve_many returned wrong targets")
db.add("c3", "https://edited.example")
before = db.queries
page = render(db, codes)
if db.queries - before != 1:
    sys.exit(f"dashboard made {db.queries - before} queries for {len(codes)} codes")
if "c3 -> https://edited.example" not in page:
    sys.exit("dashboard served a stale target after an edit")
print("batch ok")
