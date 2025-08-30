# hex_converter/cli.py
from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Sequence

try:
    # Prefer package's own version constant if you export it in __init__.py
    from . import __version__  # type: ignore[attr-defined]
except Exception:
    # Fallback to installed distribution metadata
    try:
        from importlib.metadata import version as _dist_version, PackageNotFoundError
        try:
            __version__ = _dist_version("hex-converter")
        except PackageNotFoundError:
            __version__ = "0.0.0+dev"
    except Exception:  # very old Python
        __version__ = "0.0.0+dev"

from .logic import (
    MAX_BYTES,
    parse_hex_bytes,
    parse_int_maybe,
    parse_groups_pattern,
    group_bytes_by_sizes,
    group_bytes_into_hex,
    group_bytes_into_hex_custom,
    bytes_to_ascii_runs,
    int_to_bytes,
    bytes_to_int,
    bytes_to_ones_complement,
    bytes_to_sign_magnitude,
)


# ---------- helpers ----------
def _print_kv(key: str, value: str | Iterable[str]) -> None:
    if isinstance(value, (list, tuple)):
        print(f"{key}: {' '.join(str(v) for v in value)}")
    else:
        print(f"{key}: {value}")

def _as_bin_per_byte(data: bytes) -> list[str]:
    return [f"{b:08b}" for b in data]

def _apply_grouping_hex(data: bytes, group: str, groups_pattern: str, endian: str) -> list[str]:
    if group == "custom":
        sizes = parse_groups_pattern(groups_pattern)
        return group_bytes_into_hex_custom(data, sizes, endian)
    else:
        g = int(group)
        return group_bytes_into_hex(data, g, endian)

def _chunks_for_grouping(data: bytes, group: str, groups_pattern: str, endian: str) -> list[bytes]:
    if group == "custom":
        sizes = parse_groups_pattern(groups_pattern)
        chunks = group_bytes_by_sizes(data, sizes)
    else:
        g = int(group)
        chunks = [data[i:i+g] for i in range(0, len(data), g)]
    if endian == "little":
        chunks = [ch[::-1] for ch in chunks]
    return chunks


# ---------- subcommands ----------
def cmd_hex(args: argparse.Namespace) -> int:
    # Input
    src = args.hex if args.hex is not None else sys.stdin.read()
    data = parse_hex_bytes(src)

    # Bytes (raw)
    _print_kv("Bytes", " ".join(f"{b:02X}" for b in data))
    _print_kv("Binary", _as_bin_per_byte(data))

    # Grouped hex (endianness applied within each group like the GUI)
    groups_hex = _apply_grouping_hex(data, args.group, args.groups, args.endian)
    if groups_hex:
        _print_kv("Hex groups", groups_hex)

    # Integers per group (if groups exist)
    chunks = _chunks_for_grouping(data, args.group, args.groups, args.endian)
    if chunks:
        unsigned = [int.from_bytes(ch, byteorder="big", signed=False) for ch in chunks]
        twos    = [int.from_bytes(ch, byteorder="big", signed=True)  for ch in chunks]
        _print_kv("Unsigned", [str(u) for u in unsigned])
        _print_kv("Signed 2's", [str(s) for s in twos])

    # Whole-buffer “other signed” interpretations (match GUI)
    _print_kv("Signed 1's (whole)", str(bytes_to_ones_complement(data)))
    _print_kv("Sign-magnitude (whole)", str(bytes_to_sign_magnitude(data)))

    # ASCII runs
    runs = bytes_to_ascii_runs(data)
    if runs:
        _print_kv("ASCII", "".join(runs))

    _print_kv("Length", str(len(data)))
    return 0


def cmd_number(args: argparse.Namespace) -> int:
    val = parse_int_maybe(args.value)
    width = max(1, min(args.width, MAX_BYTES))

    # Convert number → bytes (according to representation + endianness)
    mode = {
        "unsigned": "Unsigned",
        "twos": "Signed (2's complement)",
        "ones": "Signed (1's complement)",
        "signmag": "Signed (Sign-magnitude)",
    }[args.repr]

    data = int_to_bytes(val, width, mode, args.endian)

    # Bytes view
    _print_kv("Bytes", " ".join(f"{b:02X}" for b in data))
    _print_kv("Binary", _as_bin_per_byte(data))

    # ASCII runs
    runs = bytes_to_ascii_runs(data)
    if runs:
        _print_kv("ASCII", "".join(runs))

    # Scalars
    masked = val & ((1 << (width * 8)) - 1)
    _print_kv("Scalar hex", hex(masked))
    _print_kv("Scalar dec", str(val))
    return 0


def cmd_string(args: argparse.Namespace) -> int:
    # Encode as latin-1 (matches GUI behavior)
    raw = args.text.encode("latin-1", errors="replace")

    # Per-byte views
    _print_kv("Bytes", " ".join(f"{b:02X}" for b in raw))
    _print_kv("Binary", _as_bin_per_byte(raw))
    _print_kv("ASCII", args.text)  # original text

    # Grouped views (endianness applied inside each group)
    chunks = _chunks_for_grouping(raw, args.group, args.groups, args.endian)
    if chunks:
        hex_groups = [" ".join(f"{b:02X}" for b in ch) for ch in chunks]
        bin_groups = [" ".join(f"{b:08b}" for b in ch) for ch in chunks]
        text_groups = ["".join(bytes_to_ascii_runs(ch)) for ch in chunks]
        _print_kv("Hex groups", hex_groups)
        _print_kv("Bin groups", bin_groups)
        _print_kv("Text groups", text_groups)
    return 0


# ---------- parser ----------
def _add_grouping_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--endian", choices=("little", "big"), default="little",
        help="apply endianness within each group (default: little)"
    )
    p.add_argument(
        "--group", choices=("1", "2", "4", "8", "custom"), default="1",
        help="group size for group displays (default: 1)"
    )
    p.add_argument(
        "--groups", default="",
        help='custom pattern for --group=custom, e.g. "1,1,6"'
    )

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hex-converter",
        description="Hex Bytes ⇆ Integer/Text Converter (CLI)"
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sp = p.add_subparsers(dest="cmd")

    # hex
    ph = sp.add_parser("hex", help="inspect a sequence of hex bytes")
    ph.add_argument("hex", nargs="?", help="hex like 'E8 08 B0 04' or 'E808B004'")
    _add_grouping_args(ph)
    ph.set_defaults(func=cmd_hex)

    # number
    pn = sp.add_parser("number", help="convert number → bytes and views")
    pn.add_argument("value", help="number (dec or 0x… / 0b… / 0o…)")
    pn.add_argument("--width", type=int, default=4, help=f"bytes width (1..{MAX_BYTES}, default: 4)")
    pn.add_argument(
        "--repr",
        choices=("unsigned", "twos", "ones", "signmag"),
        default="unsigned",
        help="numeric representation (default: unsigned)",
    )
    pn.add_argument("--endian", choices=("little", "big"), default="little")
    pn.set_defaults(func=cmd_number)

    # string
    ps = sp.add_parser("string", help="inspect a text string as bytes")
    ps.add_argument("text", help="text to inspect (latin-1)")
    _add_grouping_args(ps)
    ps.set_defaults(func=cmd_string)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "cmd", None):
        # Back-compat convenience: if user just passes bytes after the program
        #   hex-converter "E8 08 B0 04"
        # treat it as `hex` subcommand.
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            # Re-parse as hex
            return main(["hex"] + sys.argv[1:])
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
