import pytest
from hex_converter.logic import bytes_to_ascii_runs

@pytest.mark.parametrize(
    "data,expected",
    [
        (b"ABC", ["ABC"]),
        (b"A\x00B", ["A", ".", "B"]),
        (b"\x00A\x00\x7F", [".", "A", ".", "."]),
        (b"Hello, CAN!", ["Hello, CAN!"]),
        (b"\x10\x11Test\x12", [".", "Test", "."]),
    ]
)
def test_ascii_runs(data, expected):
    assert bytes_to_ascii_runs(data) == expected
