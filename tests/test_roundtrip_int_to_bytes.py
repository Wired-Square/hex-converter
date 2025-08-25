import pytest

@pytest.mark.parametrize("endian", ["little", "big"])
@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("value", [0, 1, 255, 256, 65535, 2**31 - 1])
def test_roundtrip_int_to_bytes(logic, endian, signed, width, value):
    lo, hi = logic.int_range_for(width, signed)
    if not (lo <= value <= hi):
        pytest.skip("value out of range for this config")

    data = value.to_bytes(width, byteorder=endian, signed=signed)
    back_unsigned = int.from_bytes(data, byteorder=endian, signed=False)
    back_signed = int.from_bytes(data, byteorder=endian, signed=True)
    assert value in {back_unsigned, back_signed}
