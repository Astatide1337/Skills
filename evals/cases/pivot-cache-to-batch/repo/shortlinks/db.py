import sqlite3


class Database:
    """Thin wrapper that counts queries so callers can see their cost."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("create table links (code text primary key, target text)")
        self.queries = 0

    def add(self, code: str, target: str) -> None:
        self.conn.execute("insert or replace into links values (?, ?)", (code, target))

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        self.queries += 1
        return self.conn.execute(sql, params).fetchall()
