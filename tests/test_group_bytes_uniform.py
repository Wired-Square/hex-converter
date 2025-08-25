import pytest

@pytest.mark.parametrize("group_size", [0, 3, 9])
def test_group_bytes_to_ints_bad_group_size(logic, group_size):
    with pytest.raises(ValueError):
        logic.group_bytes_to_ints(b"\x01\x02\x03", endian="big", group_size=group_size)

def test_group_bytes_to_ints_1B_big_endian_identity(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    u, s = logic.group_bytes_to_ints(data, endian="big", group_size=1)
    assert u == [232, 8, 176, 4, 0, 0, 44, 1]
    assert s == [-24, 8, -80, 4, 0, 0, 44, 1]

def test_group_bytes_to_ints_2B_little_endian(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    u, s = logic.group_bytes_to_ints(data, endian="little", group_size=2)
    assert u == [2280, 1200, 0, 300]
    assert s == [2280, 1200, 0, 300]

def test_group_bytes_to_ints_4B_big_endian_signedness(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    u, s = logic.group_bytes_to_ints(data, endian="big", group_size=4)
    assert u == [3892883460, 11265]
    assert s == [-402083836, 11265]

def test_group_bytes_to_ints_4B_little_endian_after_grouping(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    u, s = logic.group_bytes_to_ints(data, endian="little", group_size=4)
    assert u == [0x04B008E8, 0x012C0000]
    assert s == [0x04B008E8, 0x012C0000]

def test_group_bytes_to_ints_len_not_multiple_of_group(logic):
    data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
    u, s = logic.group_bytes_to_ints(data, endian="big", group_size=4)
    assert u == [0xAABBCCDD, 0xEEFF]
    assert s[0] == 0xAABBCCDD - (1 << 32)
    assert s[1] == 0xEEFF - (1 << 16)  # -4353
