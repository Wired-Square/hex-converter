import pytest

@pytest.mark.parametrize("endian", ["little", "big"])
@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("width", [1, 2, 4, 8])
def test_roundtrip_int_to_bytes(logic, endian, signed, width):
    lo, hi = logic.int_range_for(width, signed)

    # Build a small representative set within the valid range
    candidates = {
        lo,
        lo + 1 if lo < hi else lo,
        -1 if signed and lo < 0 <= hi else None,
        0 if lo <= 0 <= hi else None,
        1 if lo <= 1 <= hi else None,
        hi - 1 if lo < hi else hi,
        hi,
    }
    values = [v for v in candidates if v is not None and lo <= v <= hi]

    for value in values:
        data = value.to_bytes(width, byteorder=endian, signed=signed)
        back_unsigned = int.from_bytes(data, byteorder=endian, signed=False)
        back_signed = int.from_bytes(data, byteorder=endian, signed=True)
        assert value in {back_unsigned, back_signed}
