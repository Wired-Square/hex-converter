import pytest

@pytest.mark.parametrize(
    "width,signed,expect_lo,expect_hi",
    [
        (1, False, 0, 255),
        (1, True, -128, 127),
        (2, False, 0, 65535),
        (2, True, -32768, 32767),
        (4, False, 0, 2**32 - 1),
        (4, True, -(2**31), 2**31 - 1),
        (8, False, 0, 2**64 - 1),
        (8, True, -(2**63), 2**63 - 1),
    ],
)
def test_int_range_for(logic, width, signed, expect_lo, expect_hi):
    lo, hi = logic.int_range_for(width, signed)
    assert (lo, hi) == (expect_lo, expect_hi)

@pytest.mark.parametrize("width", [0, 9])
def test_int_range_for_bad_width(logic, width):
    with pytest.raises(ValueError):
        logic.int_range_for(width, signed=False)

@pytest.mark.parametrize(
    "text,expected",
    [("1234", 1234), ("0x4D2", 1234), ("0b1010", 10), ("0o17", 15), ("1_000", 1000)],
)
def test_parse_int_maybe(logic, text, expected):
    assert logic.parse_int_maybe(text) == expected

@pytest.mark.parametrize("text,expected", [("-42", -42), ("-0x2A", -42), ("-0b101010", -42), ("-0o52", -42)])
def test_parse_int_maybe_negatives(logic, text, expected):
    assert logic.parse_int_maybe(text) == expected

@pytest.mark.parametrize("bad", ["", " ", "abc"])
def test_parse_int_maybe_errors(logic, bad):
    with pytest.raises(ValueError):
        logic.parse_int_maybe(bad)
