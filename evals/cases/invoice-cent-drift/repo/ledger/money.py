def fmt(amount: float) -> str:
    """Format an amount for printing on an invoice."""
    return f"{round(amount, 2):.2f}"
