import pytest

def _chunks_after_group_then_endian(data: bytes, sizes: list[int], endian: str) -> list[bytes]:
    chunks: list[bytes] = []
    i = 0
    for sz in sizes:
        if sz <= 0:
            continue
        if i >= len(data):
            break
        chunks.append(data[i:i+sz])
        i += sz
    if i < len(data):
        chunks.append(data[i:])
    if endian == "little":
        chunks = [bytes(reversed(ch)) for ch in chunks]
    return chunks

def test_group_bytes_into_hex_custom_big_endian_basic(logic):
    data = bytes([0x01, 0x01, 0x45, 0x4D, 0x30, 0x33, 0x32, 0x44])
    sizes = [1, 1, 6]
    got = logic.group_bytes_into_hex_custom(data, sizes, endian="big")
    assert got == ["01", "01", "45 4D 30 33 32 44"]

def test_group_bytes_into_hex_custom_little_endian_basic(logic):
    data = bytes([0x01, 0x01, 0x45, 0x4D, 0x30, 0x33, 0x32, 0x44])
    sizes = [1, 1, 6]
    got = logic.group_bytes_into_hex_custom(data, sizes, endian="little")
    assert got == ["01", "01", "44 32 33 30 4D 45"]

def test_group_bytes_into_hex_custom_with_leftover(logic):
    data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    sizes = [2]
    got_big = logic.group_bytes_into_hex_custom(data, sizes, endian="big")
    got_lil = logic.group_bytes_into_hex_custom(data, sizes, endian="little")
    assert got_big == ["AA BB", "CC DD EE"]
    assert got_lil == ["BB AA", "EE DD CC"]

@pytest.mark.parametrize(
    "data,sizes,endian,expect_unsigned,expect_signed",
    [
        (
            bytes([0x01, 0x01, 0x45, 0x4D, 0x30, 0x33, 0x32, 0x44]),
            [1, 1, 6],
            "big",
            [1, 1, int("454D30333244", 16)],
            [1, 1, int("454D30333244", 16)],
        ),
        (
            bytes([0x01, 0x01, 0x45, 0x4D, 0x30, 0x33, 0x32, 0x44]),
            [1, 1, 6],
            "little",
            [1, 1, int("443233304D45", 16)],
            [1, 1, int("443233304D45", 16)],
        ),
        (
            bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]),
            [4, 2],
            "big",
            [0xAABBCCDD, 0xEEFF],
            [0xAABBCCDD - (1 << 32), -4353],
        ),
        (
            bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]),
            [4, 2],
            "little",
            [0xDDCCBBAA, 0xFFEE],
            [0xDDCCBBAA - (1 << 32), -18],
        ),
    ],
)
def test_custom_group_decimals_match_endian_chunks(logic, data, sizes, endian, expect_unsigned, expect_signed):
    chunks = _chunks_after_group_then_endian(data, sizes, endian)
    u = [int.from_bytes(ch, byteorder="big", signed=False) for ch in chunks]
    s = [int.from_bytes(ch, byteorder="big", signed=True) for ch in chunks]
    assert u == expect_unsigned
    assert s == expect_signed
