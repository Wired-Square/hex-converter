"""Hex Converter package.

Re-exports the core logic for convenient imports in tests or other code.
"""
from .logic import (
    MAX_BYTES,
    PRINTABLE_MIN,
    PRINTABLE_MAX,
    parse_hex_bytes,
    bytes_to_ascii,
    int_range_for,
    parse_int_maybe,
)

__all__ = [
    "MAX_BYTES",
    "PRINTABLE_MIN",
    "PRINTABLE_MAX",
    "parse_hex_bytes",
    "bytes_to_ascii",
    "int_range_for",
    "parse_int_maybe",
]
