import csv
from pathlib import Path


def parse_row(row: dict) -> dict:
    return {"id": row["id"], "payer": row["payer"], "amount": float(row["amount"])}


def load(path: str | Path) -> list[dict]:
    with open(path, newline="") as f:
        return [parse_row(row) for row in csv.DictReader(f)]


def total(rows: list[dict]) -> float:
    return sum(row["amount"] for row in rows)
