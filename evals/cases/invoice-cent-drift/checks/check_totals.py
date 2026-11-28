"""Printed line totals must add up to the printed total."""

import random
import sys
from decimal import Decimal

sys.path.insert(0, ".")
from ledger import Invoice, Line

rng = random.Random(7)
cases = [Invoice([Line(0.10, 3), Line(0.15, 1), Line(0.35, 1)], tax_rate=0.0825)]
for _ in range(2000):
    lines = [
        Line(round(rng.uniform(0.01, 50), rng.choice([2, 3])), rng.randint(1, 9))
        for _ in range(rng.randint(1, 6))
    ]
    cases.append(Invoice(lines, tax_rate=rng.choice([0, 0.05, 0.0825, 0.0875, 0.2])))
bad = 0
for invoice in cases:
    printed = sum(Decimal(str(x)) for x in invoice.line_totals())
    if printed != Decimal(str(invoice.total())):
        bad += 1
if bad:
    sys.exit(
        f"{bad} of {len(cases)} invoices print lines that do not add up to the total"
    )
print(f"all {len(cases)} invoices add up")
