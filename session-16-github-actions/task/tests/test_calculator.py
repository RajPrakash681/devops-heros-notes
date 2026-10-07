import pytest

from app.calculator import calculate, divide


@pytest.mark.parametrize(
    "a, op, b, expected",
    [(10, "add", 5, 15), (10, "subtract", 5, 5), (10, "multiply", 5, 50), (10, "divide", 4, 2.5)],
)
def test_operations(a, op, b, expected):
    assert calculate(a, op, b) == expected


def test_divide_by_zero():
    with pytest.raises(ValueError, match="divide by zero"):
        divide(10, 0)


def test_unknown_operation():
    with pytest.raises(ValueError, match="Unknown operation"):
        calculate(1, "power", 2)
