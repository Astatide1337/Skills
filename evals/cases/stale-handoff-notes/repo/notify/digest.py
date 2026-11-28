from notify.sender import build_message


def daily_digest(to: str, items: list[str]) -> bytes:
    body = "\n".join(f"- {item}" for item in items)
    return build_message("digest@example.com", to, f"Your digest ({len(items)} items)", body)
