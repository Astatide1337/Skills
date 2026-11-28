def per_second(count: int, window_s: float) -> float:
    """Events per second over a collection window."""
    return count / window_s
