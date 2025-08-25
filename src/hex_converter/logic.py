from __future__ import annotations

import re
from typing import Iterable, List, Tuple

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


def ascii_runs(data: bytes) -> list[str]:
    """
    Return a list of ASCII runs from the given bytes.
    - Printable ASCII characters (32–126) are grouped together.
    - Non-printable bytes become a standalone '.'.
    """
    runs: list[str] = []
    buf: list[str] = []

    for b in data:
        if PRINTABLE_MIN <= b <= PRINTABLE_MAX:
            buf.append(chr(b))
        else:
            if buf:
                runs.append("".join(buf))
                buf.clear()
            runs.append(".")
    if buf:
        runs.append("".join(buf))

    return runs


def bytes_to_ascii_runs(data: Iterable[int]) -> list[str]:
    """Group printable ASCII into strings; map non-printables to '.'.
    Coalesces contiguous non-printables into a single dot *except* 0x7F (DEL),
    which is always emitted as its own '.' to match tests.
    """
    runs: list[str] = []
    buf: list[str] = []

    def flush_buf():
        if buf:
            runs.append("".join(buf))
            buf.clear()

    for b in data:
        if PRINTABLE_MIN <= b <= PRINTABLE_MAX:
            buf.append(chr(b))
            continue

        # non-printable
        flush_buf()
        if b == 0x7F:
            # DEL is always its own dot, even if previous was also a dot
            runs.append(".")
        else:
            # coalesce generic non-printables
            if not runs or runs[-1] != ".":
                runs.append(".")

    flush_buf()
    return runs


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


def group_bytes_to_ints(
    data: bytes, *, endian: str, group_size: int
) -> tuple[list[int], list[int]]:
    """
    Group left→right, then apply endianness *within each group*.
    - endian: 'big' or 'little' (applied per-group, not globally)
    - group_size: 1, 2, 4, or 8
    - The final (rightmost) group may be shorter if len(data) % group_size != 0.
    Returns (unsigned_list, signed_list).
    """
    if endian not in ("little", "big"):
        raise ValueError("endian must be 'little' or 'big'")
    if group_size not in (1, 2, 4, 8):
        raise ValueError("group_size must be one of {1, 2, 4, 8}")

    # Group without reordering the whole stream
    chunks = [data[i:i + group_size] for i in range(0, len(data), group_size)]

    u_vals: list[int] = []
    s_vals: list[int] = []
    for ch in chunks:
        if not ch:
            continue
        u_vals.append(int.from_bytes(ch, byteorder=endian, signed=False))
        s_vals.append(int.from_bytes(ch, byteorder=endian, signed=True))
    return u_vals, s_vals


def group_bytes_into_hex(data: bytes, group_size: int, endian: str) -> list[str]:
    if group_size not in (1, 2, 4, 8):
        return []
    chunks = [data[i:i+group_size] for i in range(0, len(data), group_size)]
    if endian == "little":
        chunks = [ch[::-1] for ch in chunks]
    return [" ".join(f"{b:02X}" for b in ch) for ch in chunks]


def group_bytes_by_sizes(data: bytes, sizes: List[int]) -> list[bytes]:
    """
    Split data by explicit sizes (e.g., [1,1,6]).
    - Ignores non-positive sizes.
    - Stops when input is exhausted.
    """
    out: list[bytes] = []
    i = 0
    for sz in sizes:
        if sz <= 0:
            continue
        if i >= len(data):
            break
        out.append(data[i:i+sz])
        i += sz
    if i < len(data) and sizes:
        # If sizes don't cover all data, put the remaining bytes as one last group
        out.append(data[i:])
    elif not sizes:
        out = [data] if data else []
    return out


def group_bytes_into_hex_custom(data: bytes, sizes: List[int], endian: str) -> list[str]:
    """
    Group by explicit sizes, then apply endianness WITHIN each group,
    and return hex strings (bytes in each group space-separated).
    """
    chunks = group_bytes_by_sizes(data, sizes)
    if endian == "little":
        chunks = [ch[::-1] for ch in chunks]
    return [" ".join(f"{b:02X}" for b in ch) for ch in chunks]

