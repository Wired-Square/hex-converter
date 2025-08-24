from __future__ import annotations

import importlib
import pytest

logic = importlib.import_module("hex_converter.logic")


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
def test_parse_hex_bytes_ok(text, expected):
    assert logic.parse_hex_bytes(text) == expected


@pytest.mark.parametrize("bad", ["G1", "E808B0040", "ZZ", "11 22 33 44 55 66 77 88 99"])
def test_parse_hex_bytes_errors(bad):
    with pytest.raises(ValueError):
        logic.parse_hex_bytes(bad)


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
def test_int_range_for(width, signed, expect_lo, expect_hi):
    lo, hi = logic.int_range_for(width, signed)
    assert (lo, hi) == (expect_lo, expect_hi)


@pytest.mark.parametrize("width", [0, 9])
def test_int_range_for_bad_width(width):
    with pytest.raises(ValueError):
        logic.int_range_for(width, signed=False)


@pytest.mark.parametrize(
    "text,expected",
    [("1234", 1234), ("0x4D2", 1234), ("0b1010", 10), ("0o17", 15), ("1_000", 1000)],
)
def test_parse_int_maybe(text, expected):
    assert logic.parse_int_maybe(text) == expected


@pytest.mark.parametrize("bad", ["", " ", "abc"])
def test_parse_int_maybe_errors(bad):
    with pytest.raises(ValueError):
        logic.parse_int_maybe(bad)


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"ABC", "ABC"),
        (bytes([0x41, 0x00, 0x7F, 0x80, 0x20]), "A... "),
    ],
)
def test_bytes_to_ascii(data, expected):
    assert logic.bytes_to_ascii(data) == expected


def test_bytes_to_ascii_boundaries():
    assert logic.bytes_to_ascii(b"\x20") == " "
    assert logic.bytes_to_ascii(b"\x7F") == "."


@pytest.mark.parametrize("endian", ["little", "big"])
@pytest.mark.parametrize("signed", [False, True])
@pytest.mark.parametrize("width", [1, 2, 4, 8])
@pytest.mark.parametrize("value", [0, 1, 255, 256, 65535, 2**31 - 1])
def test_roundtrip_int_to_bytes(endian, signed, width, value):
    lo, hi = logic.int_range_for(width, signed)
    if not (lo <= value <= hi):
        pytest.skip("value out of range for this config")

    data = value.to_bytes(width, byteorder=endian, signed=signed)
    back_unsigned = int.from_bytes(data, byteorder=endian, signed=False)
    back_signed = int.from_bytes(data, byteorder=endian, signed=True)

    assert value in {back_unsigned, back_signed}
