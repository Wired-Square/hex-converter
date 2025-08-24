from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .logic import (
    MAX_BYTES,
    bytes_to_ascii,
    int_range_for,
    parse_hex_bytes,
    parse_int_maybe,
)


class ConverterApp:
    """Tkinter GUI wrapper around the pure logic functions."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Hex Bytes ⇆ Integer/Text Converter")
        root.minsize(720, 480)

        main = ttk.Frame(root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        for c in range(3):
            main.columnconfigure(c, weight=1 if c == 1 else 0)

        # shared endianness
        self.endian_var = tk.StringVar(value="little")
        ttk.Label(main, text="Endianness (applies to both):").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        endian_frame = ttk.Frame(main)
        endian_frame.grid(row=0, column=1, sticky="w", pady=(0, 8))
        ttk.Radiobutton(
            endian_frame,
            text="Little endian",
            variable=self.endian_var,
            value="little",
            command=self._update_all,
        ).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            endian_frame,
            text="Big endian",
            variable=self.endian_var,
            value="big",
            command=self._update_all,
        ).pack(side="left")
        ttk.Label(main, text="Tip: Ctrl/Cmd + L toggles").grid(
            row=0, column=2, sticky="e"
        )

        # Section A: Hex -> Integer/Text
        ttk.Label(main, text="Hex bytes (≤8):").grid(
            row=2, column=0, sticky="w", padx=(0, 8)
        )
        self.hex_input_var = tk.StringVar()
        hex_input = ttk.Entry(main, textvariable=self.hex_input_var)
        hex_input.grid(row=2, column=1, sticky="ew")
        hex_input.insert(0, "E8 08 B0 04 00 00 2C 01")
        ttk.Button(main, text="Clear", command=self.on_clear_hex).grid(
            row=2, column=2, sticky="w"
        )

        self.hex_status_var = tk.StringVar()
        self.hex_error_var = tk.StringVar()
        ttk.Label(main, textvariable=self.hex_status_var, foreground="#006400").grid(
            row=3, column=1, sticky="w"
        )
        ttk.Label(main, textvariable=self.hex_error_var, foreground="#8B0000").grid(
            row=4, column=1, sticky="w"
        )

        row = 5

        def add_row(label_text: str, var: tk.StringVar, r: int) -> int:
            ttk.Label(main, text=label_text).grid(
                row=r, column=0, sticky="w", padx=(0, 8), pady=2
            )
            entry = ttk.Entry(main, textvariable=var)
            entry.grid(row=r, column=1, sticky="ew", pady=2)
            ttk.Button(main, text="Copy", width=6, command=lambda v=var: self.copy(v)).grid(
                row=r, column=2, padx=(8, 0)
            )
            return r + 1

        self.hex_as_entered_var = tk.StringVar()
        self.hex_effective_view_var = tk.StringVar()
        self.unsigned_var = tk.StringVar()
        self.signed_var = tk.StringVar()
        self.bin_from_hex_var = tk.StringVar()
        self.ascii_from_hex_var = tk.StringVar()

        row = add_row("Bytes (as entered):", self.hex_as_entered_var, row)
        row = add_row(
            "Bytes (MSB→LSB for selected endianness):",
            self.hex_effective_view_var,
            row,
        )
        row = add_row("Unsigned decimal:", self.unsigned_var, row)
        row = add_row("Signed decimal:", self.signed_var, row)
        row = add_row("Binary (8b groups):", self.bin_from_hex_var, row)
        row = add_row("Text (ASCII, '.' for non-printables):", self.ascii_from_hex_var, row)

        ttk.Separator(main, orient="horizontal").grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(10, 8)
        )
        row += 1

        # Section B: Integer -> Hex bytes
        ttk.Label(main, text="Number (dec or 0x…):").grid(
            row=row, column=0, sticky="w", padx=(0, 8)
        )
        self.int_input_var = tk.StringVar()
        int_input = ttk.Entry(main, textvariable=self.int_input_var)
        int_input.grid(row=row, column=1, sticky="ew")
        ttk.Button(main, text="Clear", command=self.on_clear_int).grid(
            row=row, column=2, sticky="w"
        )
        row += 1

        ctrl_frame = ttk.Frame(main)
        ctrl_frame.grid(row=row, column=1, sticky="w", pady=(2, 8))
        ttk.Label(main, text="Width (bytes):").grid(
            row=row, column=0, sticky="w", padx=(0, 8)
        )
        self.width_var = tk.IntVar(value=4)
        spin = ttk.Spinbox(
            ctrl_frame, from_=1, to=MAX_BYTES, textvariable=self.width_var, width=5
        )
        spin.pack(side="left", padx=(0, 10))

        self.signed_chk_var = tk.IntVar(value=0)
        ttk.Checkbutton(
            ctrl_frame,
            text="Signed (allow negatives)",
            variable=self.signed_chk_var,
            command=self.update_from_int,
        ).pack(side="left")
        row += 1

        self.int_error_var = tk.StringVar()
        ttk.Label(main, textvariable=self.int_error_var, foreground="#8B0000").grid(
            row=row, column=1, sticky="w"
        )
        row += 1

        self.int_bytes_hex_var = tk.StringVar()
        self.int_bytes_bin_var = tk.StringVar()
        self.int_bytes_ascii_var = tk.StringVar()
        self.int_hex_scalar_var = tk.StringVar()

        row = add_row("Bytes (per selected endianness):", self.int_bytes_hex_var, row)
        row = add_row("Binary (8b groups):", self.int_bytes_bin_var, row)
        row = add_row("Text (ASCII, '.' for non-printables):", self.int_bytes_ascii_var, row)
        row = add_row("Scalar hex (no width):", self.int_hex_scalar_var, row)

        # Live updates
        self.hex_input_var.trace_add("write", self.update_from_hex)
        self.int_input_var.trace_add("write", self.update_from_int)
        self.width_var.trace_add("write", self.update_from_int)

        # Keyboard: Ctrl/Cmd+L to toggle endianness
        root.bind("<Command-l>", self.toggle_endian)
        root.bind("<Control-l>", self.toggle_endian)

        # Initial compute and focus
        self.update_from_hex()
        self.update_from_int()
        hex_input.focus()

    # callbacks
    def copy(self, var: tk.StringVar) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(var.get())
        self.root.update()

    def on_clear_hex(self) -> None:
        self.hex_input_var.set("")
        self.hex_error_var.set("")
        self.update_from_hex()

    def on_clear_int(self) -> None:
        self.int_input_var.set("")
        self.int_error_var.set("")
        self.update_from_int()

    def toggle_endian(self, _event=None) -> None:
        self.endian_var.set("big" if self.endian_var.get() == "little" else "little")
        self._update_all()

    def _update_all(self) -> None:
        self.update_from_hex()
        self.update_from_int()

    def update_from_hex(self, *_args) -> None:
        text = self.hex_input_var.get()
        endian = self.endian_var.get()
        try:
            data = parse_hex_bytes(text)
            self.hex_status_var.set(f"{len(data)} byte(s) parsed")

            hex_entered = " ".join(f"{x:02X}" for x in data)
            hex_effective = (
                " ".join(f"{x:02X}" for x in data[::-1])
                if endian == "little"
                else hex_entered
            )

            self.hex_as_entered_var.set(hex_entered)
            self.hex_effective_view_var.set(hex_effective)

            if not data:
                self.unsigned_var.set("0")
                self.signed_var.set("0")
                self.bin_from_hex_var.set("")
                self.ascii_from_hex_var.set("")
                self.hex_error_var.set("")
                return

            unsigned = int.from_bytes(data, byteorder=endian, signed=False)
            signed = int.from_bytes(data, byteorder=endian, signed=True)
            binary = " ".join(f"{x:08b}" for x in data)

            self.unsigned_var.set(str(unsigned))
            self.signed_var.set(str(signed))
            self.bin_from_hex_var.set(binary)
            self.ascii_from_hex_var.set(bytes_to_ascii(data))
            self.hex_error_var.set("")
        except Exception as exc:
            self.unsigned_var.set("")
            self.signed_var.set("")
            self.bin_from_hex_var.set("")
            self.ascii_from_hex_var.set("")
            self.hex_as_entered_var.set("")
            self.hex_effective_view_var.set("")
            self.hex_status_var.set("")
            self.hex_error_var.set(str(exc))

    def update_from_int(self, *_args) -> None:
        try:
            val = parse_int_maybe(self.int_input_var.get())
            width = int(self.width_var.get())
            width = min(max(1, width), MAX_BYTES)
            signed = bool(self.signed_chk_var.get())
            endian = self.endian_var.get()

            lo, hi = int_range_for(width, signed)
            if not (lo <= val <= hi):
                self.int_error_var.set(
                    f"Out of range for {width}-byte {'signed' if signed else 'unsigned'} ({lo}..{hi})."
                )
                self._clear_int_outputs()
                return

            data = val.to_bytes(width, byteorder=endian, signed=signed)
            self.int_bytes_hex_var.set(" ".join(f"{x:02X}" for x in data))
            self.int_bytes_bin_var.set(" ".join(f"{x:08b}" for x in data))
            self.int_bytes_ascii_var.set(bytes_to_ascii(data))
            if val < 0:
                scalp = int.from_bytes(data, byteorder="big", signed=False)
                self.int_hex_scalar_var.set(f"0x{scalp:X} (two's complement, {width}B)")
            else:
                self.int_hex_scalar_var.set(hex(val))
            self.int_error_var.set("")
        except Exception as exc:
            self.int_error_var.set(str(exc))
            self._clear_int_outputs()

    def _clear_int_outputs(self) -> None:
        self.int_bytes_hex_var.set("")
        self.int_bytes_bin_var.set("")
        self.int_bytes_ascii_var.set("")
        self.int_hex_scalar_var.set("")


def run() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


def main() -> None:
    run()
