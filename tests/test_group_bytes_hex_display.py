def test_group_bytes_into_hex_empty(logic):
    assert logic.group_bytes_into_hex(b"", 2, "big") == []
    assert logic.group_bytes_into_hex(b"", 4, "little") == []

def test_group_bytes_into_hex_invalid_group_sizes_return_empty(logic):
    data = bytes([0x01, 0x02, 0x03, 0x04])
    for bad in (0, 3, 9, -1, 16):
        assert logic.group_bytes_into_hex(data, bad, "big") == []
        assert logic.group_bytes_into_hex(data, bad, "little") == []

def test_group_bytes_into_hex_1B_endian_noop(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04])
    expect = ["E8", "08", "B0", "04"]
    assert logic.group_bytes_into_hex(data, 1, "big") == expect
    assert logic.group_bytes_into_hex(data, 1, "little") == expect

def test_group_bytes_into_hex_2B_big_and_little(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    assert logic.group_bytes_into_hex(data, 2, "big") == ["E8 08", "B0 04", "00 00", "2C 01"]
    assert logic.group_bytes_into_hex(data, 2, "little") == ["08 E8", "04 B0", "00 00", "01 2C"]

def test_group_bytes_into_hex_4B_big_and_little(logic):
    data = bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])
    assert logic.group_bytes_into_hex(data, 4, "big") == ["E8 08 B0 04", "00 00 2C 01"]
    assert logic.group_bytes_into_hex(data, 4, "little") == ["04 B0 08 E8", "01 2C 00 00"]

def test_group_bytes_into_hex_len_not_multiple_of_group(logic):
    data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF])
    assert logic.group_bytes_into_hex(data, 4, "big") == ["AA BB CC DD", "EE FF"]
    assert logic.group_bytes_into_hex(data, 4, "little") == ["DD CC BB AA", "FF EE"]
