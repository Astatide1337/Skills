def human_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    return f"{n / 1000:.1f} KB"


def percent(ratio: float) -> str:
    return f"{ratio * 100:.1f}%"
