"""Hex Converter package.

Re-exports the core logic for convenient imports in tests or other code.
"""
from .logic import (
    MAX_BYTES,
    PRINTABLE_MIN,
    PRINTABLE_MAX,
    parse_hex_bytes,
    ascii_runs,
    bytes_to_ascii_runs,
    int_range_for,
    parse_int_maybe,
    group_bytes_to_ints,
    group_bytes_into_hex,
    group_bytes_into_hex_custom,
    group_bytes_by_sizes,
)

__all__ = [
    "MAX_BYTES",
    "PRINTABLE_MIN",
    "PRINTABLE_MAX",
    "parse_hex_bytes",
    "ascii_runs",
    "bytes_to_ascii_runs",
    "int_range_for",
    "parse_int_maybe",
    "group_bytes_to_ints",
    "group_bytes_into_hex",
    "group_bytes_into_hex_custom",
    "group_bytes_by_sizes",
]
