import pytest

@pytest.mark.parametrize(
    "text,expected",
    [
        ("", b""),
        ("E8 08 B0 04 00 00 2C 01", bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])),
        ("e8,08,b0,04,00,00,2c,01", bytes([0xE8, 0x08, 0xB0, 0x04, 0x00, 0x00, 0x2C, 0x01])),
        ("0xE8 0x08 0xB0 0x04", bytes([0xE8, 0x08, 0xB0, 0x04])),
        ("E808B004", bytes([0xE8, 0x08, 0xB0, 0x04])),
        ("F A", bytes([0x0F, 0x0A])),
    ],
)
def test_parse_hex_bytes_ok(logic, text, expected):
    assert logic.parse_hex_bytes(text) == expected

@pytest.mark.parametrize("bad", ["G1", "E808B0040", "ZZ", "11 22 33 44 55 66 77 88 99"])
def test_parse_hex_bytes_errors(logic, bad):
    with pytest.raises(ValueError):
        logic.parse_hex_bytes(bad)
