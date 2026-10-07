"""Calculator logic. Pure functions, so the tests need no server."""

OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
}


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


OPERATIONS["divide"] = divide


def calculate(a, op, b):
    """Apply operation `op` to a and b. Raises ValueError on a bad op or b == 0."""
    if op not in OPERATIONS:
        raise ValueError(f"Unknown operation '{op}'. Use one of: {', '.join(OPERATIONS)}")
    return OPERATIONS[op](a, b)
