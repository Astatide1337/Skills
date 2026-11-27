"""No in-process cache may remain in the package."""

import re
import sys
from pathlib import Path

hits = [
    str(p)
    for p in Path("shortlinks").rglob("*.py")
    if re.search(
        r"lru_cache|functools\.cache\b|@cache\b|OrderedDict|_cache\b|cache_clear|maxsize",
        p.read_text(),
    )
]
if hits:
    sys.exit(f"cache code remains in {hits}")
print("no cache")
