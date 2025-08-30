# hex_converter/__init__.py

from importlib.metadata import version, PackageNotFoundError

"""Hex Converter package.

Re-exports the core logic for convenient imports in tests or other code.
"""
from .__about__ import (
    __version__,
    APP_NAME,
    APP_TITLE,
    BUNDLE_ID,
    AUTHOR,
    COPYRIGHT,
    COPYRIGHT_YEAR,
    HOMEPAGE,
)

from .logic import (
    MAX_BYTES,
    PRINTABLE_MIN,
    PRINTABLE_MAX,
    bytes_to_ascii_runs,
    bytes_to_int,
    bytes_to_ones_complement,
    bytes_to_sign_magnitude,
    parse_hex_bytes,
    parse_groups_pattern,
    parse_int_maybe,
    int_range_for,
    int_to_bytes,
    group_bytes_by_sizes,
    group_bytes_into_hex,
    group_bytes_into_hex_custom,
    group_bytes_to_ints,
    int_to_ones_complement,
    int_to_sign_magnitude,
)

__all__ = [
    # Metadata
    "__version__", "APP_NAME", "APP_TITLE", "BUNDLE_ID",
    "AUTHOR", "COPYRIGHT", "COPYRIGHT_YEAR", "HOMEPAGE",
    # Logic
    "MAX_BYTES", "PRINTABLE_MIN", "PRINTABLE_MAX",
    "bytes_to_ascii_runs", "bytes_to_int",
    "bytes_to_ones_complement", "bytes_to_sign_magnitude",
    "parse_hex_bytes", "parse_groups_pattern", "parse_int_maybe",
    "int_range_for", "int_to_bytes",
    "group_bytes_by_sizes", "group_bytes_into_hex", "group_bytes_into_hex_custom",
    "group_bytes_to_ints", "int_to_ones_complement", "int_to_sign_magnitude",
]
