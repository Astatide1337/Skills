from dataclasses import dataclass, field

from ledger.money import fmt


@dataclass
class Line:
    price: float
    qty: int


@dataclass
class Invoice:
    lines: list[Line] = field(default_factory=list)
    tax_rate: float = 0.0

    def line_totals(self) -> list[str]:
        """Printed per-line amounts, tax included."""
        return [fmt(line.price * line.qty * (1 + self.tax_rate)) for line in self.lines]

    def total(self) -> str:
        """Printed invoice total, tax included."""
        return fmt(sum(line.price * line.qty for line in self.lines) * (1 + self.tax_rate))
