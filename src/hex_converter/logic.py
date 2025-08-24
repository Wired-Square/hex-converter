from __future__ import annotations

import re
from typing import Iterable, Tuple

MAX_BYTES = 8
PRINTABLE_MIN = 32
PRINTABLE_MAX = 126


def parse_hex_bytes(text: str) -> bytes:
    """Parse a string of hex into up to ``MAX_BYTES`` bytes.

    Accepts:
      - "E8 08 B0 04 00 00 2C 01" (spaces)
      - "e8,08,b0,04,00,00,2c,01" (commas)
      - "0xE8 0x08 0xB0 0x04 ..." (0x prefixes)
      - "E808B00400002C01" (continuous)
      - Single nibbles allowed when separated ("F" → "0F")
    """
    s = text.strip()
    if not s:
        return b""

    s = s.replace(",", " ")
    s = re.sub(r"0x", "", s, flags=re.IGNORECASE)
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)

    if " " in s:
        tokens = s.split(" ")
    else:
        if len(s) % 2 != 0:
            raise ValueError(
                "Continuous hex string must have an even number of characters."
            )
        tokens = [s[i : i + 2] for i in range(0, len(s), 2)]

    out: list[int] = []
    for tok in tokens:
        if not tok:
            continue
        if len(tok) == 1:
            tok = "0" + tok
        if not re.fullmatch(r"[0-9A-Fa-f]{2}", tok):
            raise ValueError(f"Invalid hex byte: {tok}")
        out.append(int(tok, 16))

    if len(out) > MAX_BYTES:
        raise ValueError(f"More than {MAX_BYTES} bytes provided.")

    return bytes(out)


def bytes_to_ascii(data: Iterable[int]) -> str:
    """Return ASCII text for bytes; replace non-printables with '.'."""
    return "".join(
        chr(x) if PRINTABLE_MIN <= x <= PRINTABLE_MAX else "." for x in data
    )


def int_range_for(width: int, signed: bool) -> Tuple[int, int]:
    """Return inclusive (lo, hi) range for a given byte width and signedness."""
    if width < 1 or width > MAX_BYTES:
        raise ValueError(f"width must be 1..{MAX_BYTES}")
    if signed:
        lo = -(1 << (8 * width - 1))
        hi = (1 << (8 * width - 1)) - 1
    else:
        lo = 0
        hi = (1 << (8 * width)) - 1
    return lo, hi


def parse_int_maybe(text: str) -> int:
    """Parse an integer accepting 0x/0b/0o prefixes or decimal."""
    s = text.strip().replace("_", "")
    if not s:
        raise ValueError("Enter a number (e.g., 1234 or 0x4D2).")
    return int(s, 0)
