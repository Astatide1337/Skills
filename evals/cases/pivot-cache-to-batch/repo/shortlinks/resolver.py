from shortlinks.db import Database


def resolve(db: Database, code: str) -> str | None:
    rows = db.query("select target from links where code = ?", (code,))
    return rows[0][0] if rows else None
