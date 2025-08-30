# hex_converter/logic.py

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

MAX_BYTES = 8
PRINTABLE_MIN = 32
PRINTABLE_MAX = 126


# ---------------- Value logic ----------------
def parse_groups_pattern(text: str) -> list[int]:
    s = (text or "").replace(",", " ")
    parts = [p for p in s.split() if p.strip()]
    return [int(p) for p in parts if int(p) > 0]

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

def parse_int_maybe(text: str) -> int:
    """Parse an integer accepting 0x/0b/0o prefixes or decimal."""
    s = text.strip().replace("_", "")
    if not s:
        raise ValueError("Enter a number (e.g., 1234 or 0x4D2).")
    return int(s, 0)

def int_range_for(width: int, signed: bool) -> Tuple[int, int]:
    """
    Return inclusive (lo, hi) range for a given byte width and signedness.

    Ranges:
    Unsigned:        [0, 2^n - 1]
    2's complement:  [-(2^(n-1)), 2^(n-1) - 1]
    1's complement:  [-(2^(n-1) - 1), 2^(n-1) - 1]
    Sign-magnitude:  [-(2^(n-1) - 1), 2^(n-1) - 1]
    """
    if width < 1 or width > MAX_BYTES:
        raise ValueError(f"width must be 1..{MAX_BYTES}")
    if signed:
        lo = -(1 << (8 * width - 1))
        hi = (1 << (8 * width - 1)) - 1
    else:
        lo = 0
        hi = (1 << (8 * width)) - 1
    return lo, hi


# ---------------- Byte grouping ----------------
def chunk_bytes(data: bytes, group_mode: str, custom_pattern: str, endian: str) -> list[bytes]:
    if group_mode == "custom":
        sizes = parse_groups_pattern(custom_pattern)
        chunks: list[bytes] = []
        i = 0
        for sz in sizes:
            if i >= len(data):
                break
            chunks.append(data[i:i+sz])
            i += sz
        if i < len(data):
            chunks.append(data[i:])
    else:
        g = int(group_mode) if group_mode in {"1","2","4","8"} else 1
        chunks = [data[i:i+g] for i in range(0, len(data), g)]
    if endian == "little":
        chunks = [bytes(reversed(ch)) for ch in chunks]
    return chunks

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

def group_bytes_into_hex(data: bytes, group_size: int, endian: str) -> list[str]:
    if group_size not in (1, 2, 4, 8):
        return []
    chunks = [data[i:i+group_size] for i in range(0, len(data), group_size)]
    if endian == "little":
        chunks = [ch[::-1] for ch in chunks]
    return [" ".join(f"{b:02X}" for b in ch) for ch in chunks]

def group_bytes_into_hex_custom(data: bytes, sizes: List[int], endian: str) -> list[str]:
    """
    Group by explicit sizes, then apply endianness WITHIN each group,
    and return hex strings (bytes in each group space-separated).
    """
    chunks = group_bytes_by_sizes(data, sizes)
    if endian == "little":
        chunks = [ch[::-1] for ch in chunks]
    return [" ".join(f"{b:02X}" for b in ch) for ch in chunks]


# ---------------- Value logic ----------------
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

def int_to_bytes(val: int, width: int, mode: str, endian: str) -> bytes:
    """Convert integer to bytes according to representation."""
    if mode == "Unsigned":
        if val < 0 or val >= 1 << (width * 8):
            raise ValueError(f"Value out of range for {width}-byte unsigned")
        return val.to_bytes(width, byteorder=endian, signed=False)

    elif mode == "Signed (2's complement)":
        min_val, max_val = -(1 << (width*8 - 1)), (1 << (width*8 - 1)) - 1
        if not (min_val <= val <= max_val):
            raise ValueError(f"Value out of range for {width}-byte 2's complement")
        return val.to_bytes(width, byteorder=endian, signed=True)

    elif mode == "Signed (1's complement)":
        # Range: −(2^(n−1)−1) .. +(2^(n−1)−1); no representable −2^(n−1)
        max_mag = (1 << (8*width - 1)) - 1
        if not (-max_mag <= val <= max_mag):
            raise ValueError(f"Value out of range for {width}-byte 1's complement")
        if val >= 0:
            return val.to_bytes(width, byteorder=endian, signed=False)
        # negative: bitwise NOT of the magnitude
        mag = (-val).to_bytes(width, byteorder=endian, signed=False)
        return bytes((~x) & 0xFF for x in mag)

    elif mode == "Signed (Sign-magnitude)":
        # Range: −(2^(n−1)−1) .. +(2^(n−1)−1); the top bit is the sign bit.
        magnitude = abs(val)
        if magnitude >= 1 << (width*8 - 1):
            raise ValueError("Value out of range for sign-magnitude")
        data = magnitude.to_bytes(width, byteorder=endian, signed=False)
        if val < 0:
            if endian == "big":
                data = bytes([data[0] | 0x80]) + data[1:]
            else:
                data = data[:-1] + bytes([data[-1] | 0x80])
        return data

    else:
        raise ValueError(f"Unknown representation mode: {mode}")

def bytes_to_int(b: bytes, mode: str, endian: str) -> int:
    """Convert bytes to integer according to representation."""
    if mode == "Unsigned":
        return int.from_bytes(b, byteorder=endian, signed=False)

    elif mode == "Signed (2's complement)":
        return int.from_bytes(b, byteorder=endian, signed=True)

    elif mode == "Signed (1's complement)":
        # Endian-agnostic: operate on the full-width unsigned int.
        u = int.from_bytes(b, byteorder=endian, signed=False)
        mask = (1 << (8*len(b))) - 1
        sign_bit = 1 << (8*len(b) - 1)
        if u & sign_bit:
            mag = (~u) & mask
            # Normalize negative zero (all ones) to 0
            return 0 if mag == 0 else -mag
        return u

    elif mode == "Signed (Sign-magnitude)":
        if endian == "big":
            sign = b[0] & 0x80
            mag_bytes = bytes([b[0] & 0x7F]) + b[1:]
        else:
            sign = b[-1] & 0x80
            mag_bytes = b[:-1] + bytes([b[-1] & 0x7F])
        magnitude = int.from_bytes(mag_bytes, byteorder=endian, signed=False)
        return -magnitude if sign else magnitude

    else:
        raise ValueError(f"Unknown representation mode: {mode}")

def string_to_bytes_chunks(raw: bytes, group_mode: str, custom_pattern: str, endian: str) -> list[bytes]:
    """Return list of chunks like in HEX mode."""
    return chunk_bytes(raw, group_mode, custom_pattern, endian)

def chunks_to_unsigned_signed(chunks: list[bytes]) -> tuple[list[int], list[int]]:
    u_vals = [int.from_bytes(ch, "big", signed=False) for ch in chunks]
    s_vals = [int.from_bytes(ch, "big", signed=True) for ch in chunks]
    return u_vals, s_vals


# ---------------- Signed representations ----------------
def bytes_to_ones_complement(b: bytes) -> int:
    """Interpret bytes as signed 1's complement integer."""
    first_bit = b[0] & 0x80
    if first_bit:
        inv = bytes(~x & 0xFF for x in b)
        return -int.from_bytes(inv, "big")
    return int.from_bytes(b, "big")

def bytes_to_sign_magnitude(b: bytes) -> int:
    """Interpret bytes as signed sign-magnitude integer."""
    sign = b[0] & 0x80
    mag_bytes = bytes([b[0] & 0x7F]) + b[1:]
    magnitude = int.from_bytes(mag_bytes, "big")
    return -magnitude if sign else magnitude

def int_to_ones_complement(val: int, width: int, endian: str) -> bytes:
    if val < 0:
        data = abs(val).to_bytes(width, byteorder=endian)
        data = bytes(~b & 0xFF for b in data)
    else:
        data = val.to_bytes(width, byteorder=endian)
    return data

def int_to_sign_magnitude(val: int, width: int, endian: str) -> bytes:
    sign = (val < 0)
    mag = abs(val)
    if mag >= 1 << (width*8 - 1):
        raise ValueError("Value out of range for sign-magnitude")
    b = bytearray(mag.to_bytes(width, byteorder=endian))
    if sign:
        if endian == "big":
            b[0] |= 0x80
        else:
            b[-1] |= 0x80
    return bytes(b)
