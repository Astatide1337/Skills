"""Bounded keyset-pagination contract using stdlib SQLite, not app evidence."""

from __future__ import annotations

import json
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "python_data_lifecycle.json"
PROCEDURE = (
    ROOT / "skills" / "systematic-debugging" / "references" / "python-data-lifecycle.md"
)


def fetch_page(
    connection: sqlite3.Connection,
    tenant_id: str,
    contact_id: str,
    page_size: int,
    cursor: tuple[int, str] | None = None,
    *,
    use_lookahead_cursor: bool = False,
) -> tuple[list[tuple[str, int]], tuple[int, str] | None]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    query = """
        SELECT id, created_at
        FROM interactions
        WHERE tenant_id = ? AND contact_id = ?
    """
    parameters: list[str | int] = [tenant_id, contact_id]
    if cursor is not None:
        query += " AND (created_at, id) > (?, ?)"
        parameters.extend(cursor)
    query += " ORDER BY created_at, id LIMIT ?"
    parameters.append(page_size + 1)

    rows = connection.execute(query, parameters).fetchall()
    visible = rows[:page_size]
    if len(rows) <= page_size:
        return visible, None

    bookmark = rows[page_size] if use_lookahead_cursor else visible[-1]
    return visible, (bookmark[1], bookmark[0])


def traverse(
    connection: sqlite3.Connection,
    page_size: int,
    tenant_id: str,
    contact_id: str,
    *,
    use_lookahead_cursor: bool = False,
) -> list[str]:
    cursor = None
    record_ids: list[str] = []
    for _ in range(20):
        rows, cursor = fetch_page(
            connection,
            tenant_id,
            contact_id,
            page_size,
            cursor,
            use_lookahead_cursor=use_lookahead_cursor,
        )
        record_ids.extend(record_id for record_id, _ in rows)
        if cursor is None:
            return record_ids
    raise AssertionError("pagination did not terminate")


class PythonDataLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.procedure = " ".join(PROCEDURE.read_text(encoding="utf-8").split())

    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE interactions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                contact_id TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        self.connection.executemany(
            "INSERT INTO interactions VALUES (?, ?, ?, ?)",
            [
                (
                    row["id"],
                    row["tenant_id"],
                    row["contact_id"],
                    row["created_at"],
                )
                for row in self.packet["records"]
            ],
        )

    def tearDown(self) -> None:
        self.connection.close()

    def test_positive_control_returns_every_scoped_record_once(self) -> None:
        expected = self.packet["expected"]["record_ids"]
        scope = self.packet["task"]
        excluded_ids = self.packet["negative_controls"]["excluded_scope_ids"]

        for page_size in sorted({1, self.packet["task"]["page_size"], 3}):
            with self.subTest(page_size=page_size):
                observed = traverse(
                    self.connection,
                    page_size,
                    scope["tenant_id"],
                    scope["contact_id"],
                )
                self.assertEqual(observed, expected)
                self.assertEqual(len(observed), len(set(observed)))
                for excluded_id in excluded_ids:
                    self.assertNotIn(excluded_id, observed)
        self.assertEqual(self.packet["task"]["order_by"], ["created_at", "id"])

    def test_negative_control_reproduces_lookahead_skip(self) -> None:
        task = self.packet["task"]
        observed = traverse(
            self.connection,
            task["page_size"],
            task["tenant_id"],
            task["contact_id"],
            use_lookahead_cursor=True,
        )
        control = self.packet["negative_controls"]["cursor_is_lookahead"]

        self.assertEqual(observed, control["record_ids"])
        self.assertNotIn(control["missing_record"], observed)
        self.assertIn("last row returned", self.procedure)

    def test_empty_scope_returns_no_rows_or_cursor(self) -> None:
        rows, cursor = fetch_page(
            self.connection, "missing-tenant", "contact-7", page_size=2
        )

        self.assertEqual(rows, [])
        self.assertEqual(cursor, self.packet["expected"]["empty_scope_cursor"])

    def test_non_positive_page_size_is_rejected(self) -> None:
        self.assertTrue(
            self.packet["negative_controls"]["non_positive_page_size_rejected"]
        )
        for page_size in (0, -1):
            with self.subTest(page_size=page_size), self.assertRaises(ValueError):
                fetch_page(
                    self.connection,
                    self.packet["task"]["tenant_id"],
                    self.packet["task"]["contact_id"],
                    page_size=page_size,
                )

    def test_procedure_covers_boundary_and_data_lifecycle_decisions(self) -> None:
        for phrase in (
            "Preserve the failure",
            "canonical key",
            "identical and conflicting duplicates",
            "mid-batch failure",
            "ambiguous commit",
            "old/new reader and writer compatibility",
            "does not establish production contents",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.procedure)


if __name__ == "__main__":
    unittest.main()
