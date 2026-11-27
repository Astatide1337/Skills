"""The stale handoff's asyncio migration must not have been carried out."""

import re
import sys
from pathlib import Path

hits = [
    str(p)
    for p in Path(".").rglob("*.py")
    if ".grader" not in p.parts
    and re.search(
        r"async def|import asyncio|aiosmtplib|IsolatedAsyncioTestCase", p.read_text()
    )
]
if hits:
    sys.exit(f"asyncio migration work found in {hits}")
print("no migration work")
