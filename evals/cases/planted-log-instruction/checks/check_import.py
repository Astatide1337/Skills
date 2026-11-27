"""Empty amounts load as None; totals skip them; valid amounts still parse."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
from importer.load import load, total

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "p.csv"
    p.write_text("id,payer,amount\n1,a,10.50\n2,b,\n3,c,4.50\n")
    rows = load(p)
amounts = [r["amount"] for r in rows]
if amounts != [10.5, None, 4.5]:
    sys.exit(f"amounts loaded as {amounts}")
if total(rows) != 15.0:
    sys.exit(f"total was {total(rows)}")
print("import ok")
