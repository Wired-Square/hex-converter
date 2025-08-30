# tests/test_boundaries.py
import pytest

@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("endian", ["little", "big"])
def test_unsigned_boundaries(logic, width, endian):
    lo, hi = logic.int_range_for(width, signed=False)
    for val in [lo, 1, hi]:
        b = logic.int_to_bytes(val, width, "Unsigned", endian)
        assert logic.bytes_to_int(b, "Unsigned", endian) == val
    with pytest.raises(ValueError):
        logic.int_to_bytes(-1, width, "Unsigned", endian)
    with pytest.raises(ValueError):
        logic.int_to_bytes(hi + 1, width, "Unsigned", endian)

@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("endian", ["little", "big"])
def test_twos_complement_boundaries(logic, width, endian):
    lo, hi = logic.int_range_for(width, signed=True)  # exact 2's complement range
    for val in [lo, -1, 0, 1, hi]:
        b = logic.int_to_bytes(val, width, "Signed (2's complement)", endian)
        assert logic.bytes_to_int(b, "Signed (2's complement)", endian) == val

@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("endian", ["little", "big"])
def test_ones_complement_boundaries_and_negzero(logic, width, endian):
    # 1's complement has range −(2^(n−1)−1) .. +(2^(n−1)−1)
    max_mag = (1 << (8*width - 1)) - 1
    lo, hi = -max_mag, max_mag
    for val in [lo, -1, 0, 1, hi]:
        b = logic.int_to_bytes(val, width, "Signed (1's complement)", endian)
        assert logic.bytes_to_int(b, "Signed (1's complement)", endian) == val
    # Out-of-range (too negative)
    with pytest.raises(ValueError):
        logic.int_to_bytes(-(1 << (8*width - 1)), width, "Signed (1's complement)", endian)
    # Decode “negative zero” (all ones) should normalize to 0
    neg_zero = bytes([0xFF]) * width
    assert logic.bytes_to_int(neg_zero, "Signed (1's complement)", endian) == 0

@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("endian", ["little", "big"])
def test_sign_magnitude_boundaries_and_negzero(logic, width, endian):
    # sign-magnitude also: −(2^(n−1)−1) .. +(2^(n−1)−1)
    max_mag = (1 << (8*width - 1)) - 1
    lo, hi = -max_mag, max_mag
    for val in [lo, -1, 0, 1, hi]:
        b = logic.int_to_bytes(val, width, "Signed (Sign-magnitude)", endian)
        assert logic.bytes_to_int(b, "Signed (Sign-magnitude)", endian) == val
    # Out-of-range (magnitude needs more than 7 bits of the top byte)
    with pytest.raises(ValueError):
        logic.int_to_bytes(-(1 << (8*width - 1)), width, "Signed (Sign-magnitude)", endian)
    # Decode “negative zero” form should normalize to 0
    if endian == "big":
        neg_zero = bytes([0x80]) + bytes(width - 1)
    else:
        neg_zero = bytes(width - 1) + bytes([0x80])
    assert logic.bytes_to_int(neg_zero, "Signed (Sign-magnitude)", endian) == 0
