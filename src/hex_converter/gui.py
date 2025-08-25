from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .logic import (
    MAX_BYTES,
    bytes_to_ascii_runs,
    int_range_for,
    parse_hex_bytes,
    parse_int_maybe,
    group_bytes_to_ints,
    group_bytes_into_hex,
    group_bytes_into_hex_custom,
)

class CopyButtonsField(ttk.Frame):
    """Render N buttons in a horizontal row that expands with the window width."""
    def __init__(self, parent, on_copy):
        super().__init__(parent)
        self._buttons: list[ttk.Button] = []
        self._on_copy = on_copy

    def set_values(self, values: list[str]) -> None:
        # Clear old buttons
        for b in self._buttons:
            b.destroy()
        self._buttons.clear()

        if not values:
            return

        for val in values:
            btn = ttk.Button(self, text=val)
            
            # Use a helper to properly capture the variables
            def make_callback(v=val, button=btn):
                return lambda: self._on_copy(v, button)

            btn.config(command=make_callback())
            btn.pack(side="left", padx=4, pady=2)
            self._buttons.append(btn)


class ConverterApp:
    """Tkinter GUI wrapper around the pure logic functions, with mode-specific UIs."""
    MODES = ("HEX", "Number", "String")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Hex Bytes ⇆ Integer/Text Converter")
        root.minsize(820, 520)

        self.main = ttk.Frame(root, padding=12)
        self.main.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        # Shared: endianness
        self.endian_var = tk.StringVar(value="little")

        # Mode
        self.mode_var = tk.StringVar(value="HEX")

        # Grouping state (used by HEX and STRING modes)
        self.group_mode_var = tk.StringVar(value="1")   # default grouping size: 1 byte
        self.custom_groups_var = tk.StringVar(value="") # empty by default

        # Top controls bar
        self._build_controls_bar(row=0)

        ttk.Separator(self.main, orient="horizontal").grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(8, 10)
        )

        # Content placeholder (replaced per mode)
        self.content = ttk.Frame(self.main)
        self.content.grid(row=4, column=0, columnspan=4, sticky="nsew")
        self.main.rowconfigure(4, weight=1)
        self.content.columnconfigure(1, weight=1)

        # Build the initial mode UI
        self._render_mode()

        # Keyboard: Ctrl/Cmd+L to toggle endianness
        root.bind("<Command-l>", self._toggle_endian)
        root.bind("<Control-l>", self._toggle_endian)

    # ----------------- Controls bar -----------------
    def _build_controls_bar(self, row: int) -> None:
        # Mode select
        ttk.Label(self.main, text="Mode:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        mode_frame = ttk.Frame(self.main)
        mode_frame.grid(row=row, column=1, sticky="w")
        for m in self.MODES:
            ttk.Radiobutton(
                mode_frame, text=m, value=m, variable=self.mode_var, command=self._render_mode
            ).pack(side="left", padx=(0, 10))

        # Endianness (applies per group)
        ttk.Label(self.main, text="Endianness:").grid(row=row+1, column=0, sticky="w", padx=(0, 8))
        endian_frame = ttk.Frame(self.main)
        endian_frame.grid(row=row+1, column=1, sticky="w", pady=(0, 8))
        ttk.Radiobutton(
            endian_frame,
            text="Little",
            variable=self.endian_var,
            value="little",
            command=self._update_current_mode,
        ).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            endian_frame,
            text="Big",
            variable=self.endian_var,
            value="big",
            command=self._update_current_mode,
        ).pack(side="left")
        ttk.Label(self.main, text="Tip: Ctrl/Cmd + L toggles").grid(
            row=row+1, column=2, sticky="e"
        )

        # Live updates when typing custom pattern
        self.custom_groups_var.trace_add("write", lambda *_: self._update_current_mode())

        # Initialise enabled/disabled state
        self._on_group_mode_changed()

    def _toggle_endian(self, _event=None) -> None:
        self.endian_var.set("big" if self.endian_var.get() == "little" else "little")
        self._update_current_mode()

    def copy_value(self, value: str, btn: ttk.Button | None = None) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        if btn:
            old = btn['text']
            btn.config(text="Copied!")
            self.root.after(750, lambda: btn.config(text=old))

    def paste_into(self, var: tk.StringVar) -> None:
        try:
            var.set(self.root.clipboard_get())
        except tk.TclError:
            # Clipboard empty or unavailable; ignore gracefully
            pass

    # ----------------- Mode rendering -----------------
    def _render_mode(self) -> None:
        # Clear current content
        for w in self.content.winfo_children():
            w.destroy()

        mode = self.mode_var.get()
        if mode == "HEX":
            self._build_hex_ui(self.content)
        elif mode == "Number":
            self._build_number_ui(self.content)
        else:
            self._build_string_ui(self.content)

    def _update_current_mode(self) -> None:
        # Trigger appropriate update handler for current mode
        mode = self.mode_var.get()
        if mode == "HEX":
            self._update_from_hex()
        elif mode == "Number":
            self._update_from_int()
        else:
            self._update_from_str()

    # ----------------- Helpers -----------------
    def _on_group_mode_changed(self) -> None:
        is_custom = self.group_mode_var.get() == "custom"
        state = "normal" if is_custom else "disabled"
        try:
            self.custom_groups_entry.configure(state=state)
        except Exception:
            pass
        self._update_current_mode()

    def _parse_groups_pattern(self, text: str) -> list[int]:
        """
        Parse '1,1,6' or '1 1 6' into [1,1,6].
        Ignores empty tokens; filters out non-positive numbers.
        """
        s = (text or "").replace(",", " ")
        parts = [p for p in s.split() if p.strip()]
        sizes: list[int] = []
        for p in parts:
            try:
                n = int(p)
            except ValueError:
                continue
            if n > 0:
                sizes.append(n)
        return sizes

    # ===========================================================
    # ===============  HEX MODE (bytes -> …) ====================
    # ===========================================================
    def _build_hex_ui(self, parent: ttk.Frame) -> None:
        r = 0
        # Input
        ttk.Label(parent, text="Hex bytes (≤8):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.hex_input_var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=self.hex_input_var)
        entry.grid(row=r, column=1, sticky="ew")
        btns = ttk.Frame(parent)
        btns.grid(row=r, column=2, sticky="w")
        ttk.Button(
            btns, text="Paste",
            command=lambda: (self.paste_into(self.hex_input_var), self._update_from_hex())
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            btns, text="Clear",
            command=lambda: (self.hex_input_var.set(""), self._update_from_hex())
        ).pack(side="left")
        r += 1

        # --- HEX-only grouping controls ---
        ttk.Label(parent, text="Group bytes as:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        grp = ttk.Frame(parent)
        grp.grid(row=r, column=1, sticky="w", pady=(0, 8))

        self.hex_group_mode_var = tk.StringVar(value="1")    # '1','2','4','8','custom'
        self.hex_custom_groups_var = tk.StringVar(value="")  # e.g. "1,1,6"

        for val in ("1", "2", "4", "8", "custom"):
            ttk.Radiobutton(
                grp,
                text="Custom" if val == "custom" else f"{val}B",
                value=val,
                variable=self.hex_group_mode_var,
                command=self._hex_group_mode_changed,
            ).pack(side="left", padx=(0, 10))

        self.hex_custom_groups_entry = ttk.Entry(parent, textvariable=self.hex_custom_groups_var, width=24)
        self.hex_custom_groups_entry.grid(row=r, column=2, sticky="w")
        ttk.Label(parent, text="e.g., 1,1,6").grid(row=r, column=3, sticky="w", padx=(8, 0))
        r += 1

        # Status / error
        self.hex_status_var = tk.StringVar()
        self.hex_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.hex_status_var, foreground="#006400").grid(row=r, column=1, sticky="w"); r += 1
        ttk.Label(parent, textvariable=self.hex_error_var, foreground="#8B0000").grid(row=r, column=1, sticky="w"); r += 1

        # Outputs
        ttk.Label(parent, text="Hex groups:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.hex_group_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.hex_group_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Unsigned decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.unsigned_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.unsigned_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Signed decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.signed_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.signed_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Binary:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.bin_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.bin_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Text (ASCII or .):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.text_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.text_btns.grid(row=r, column=1, sticky="ew"); r += 1

        # --- Wire events AFTER widgets exist ---
        # Custom pattern live updates
        self.hex_custom_groups_var.trace_add("write", lambda *_: self._update_from_hex())
        # Enable/disable the custom entry now that it exists
        self._hex_group_mode_changed()

        # Input live updates
        self.hex_input_var.trace_add("write", lambda *_: self._update_from_hex())
        entry.focus()

        # Initial compute (safe now)
        self.hex_input_var.set("E8 08 B0 04 00 00 2C 01")

    def _update_from_hex(self) -> None:
        if not hasattr(self, "hex_input_var"):
            return
        text = self.hex_input_var.get()
        try:
            data = parse_hex_bytes(text)
            self.hex_status_var.set(f"{len(data)} byte(s) parsed")
            if not data:
                self.hex_group_btns.set_values([])
                self.unsigned_btns.set_values([])
                self.signed_btns.set_values([])
                self.bin_btns.set_values([])
                self.text_btns.set_values([])
                self.hex_error_var.set("")
                return

            # Build chunks per current HEX grouping (endianness applied within each chunk)
            chunks = self._hex_chunks(data)

            # Hex groups (use whatever grouping is currently selected)
            self.hex_group_btns.set_values([" ".join(f"{b:02X}" for b in ch) for ch in chunks])

            # Decimals per chunk (interpret bytes as big-endian after per-chunk endian flip)
            self.unsigned_btns.set_values([str(int.from_bytes(ch, "big", signed=False)) for ch in chunks])
            self.signed_btns.set_values([str(int.from_bytes(ch, "big", signed=True))  for ch in chunks])

            # Binary per chunk
            self.bin_btns.set_values([" ".join(f"{b:08b}" for b in ch) for ch in chunks])

            # ASCII runs (whole payload)
            self.text_btns.set_values(bytes_to_ascii_runs(data))
            self.hex_error_var.set("")

        except Exception as exc:
            self.hex_group_btns.set_values([])
            self.unsigned_btns.set_values([])
            self.signed_btns.set_values([])
            self.bin_btns.set_values([])
            self.text_btns.set_values([])
            self.hex_status_var.set("")
            self.hex_error_var.set(str(exc))

    def _hex_group_mode_changed(self) -> None:
        is_custom = getattr(self, "hex_group_mode_var", None) and self.hex_group_mode_var.get() == "custom"
        if hasattr(self, "hex_custom_groups_entry"):
            self.hex_custom_groups_entry.configure(state=("normal" if is_custom else "disabled"))
        self._update_from_hex()

    def _hex_parse_groups_pattern(self, text: str) -> list[int]:
        s = (text or "").replace(",", " ")
        parts = [p for p in s.split() if p.strip()]
        sizes: list[int] = []
        for p in parts:
            try:
                n = int(p)
            except ValueError:
                continue
            if n > 0:
                sizes.append(n)
        return sizes

    def _hex_chunks(self, data: bytes) -> list[bytes]:
        """
        HEX-mode chunking based on the local group control.
        - 'custom' uses the pattern with leftover appended.
        - '1','2','4','8' use uniform groups.
        Then endianness is applied within each chunk.
        """
        mode = self.hex_group_mode_var.get() if hasattr(self, "hex_group_mode_var") else "1"

        if mode == "custom":
            sizes = self._hex_parse_groups_pattern(self.hex_custom_groups_var.get())
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
            g = int(mode) if mode in {"1", "2", "4", "8"} else 1
            chunks = [data[i:i+g] for i in range(0, len(data), g)]

        if self.endian_var.get() == "little":
            chunks = [bytes(reversed(ch)) for ch in chunks]
        return chunks

    # ===========================================================
    # =============  NUMBER MODE (int -> bytes …) ===============
    # ===========================================================
    def _build_number_ui(self, parent: ttk.Frame) -> None:
        r = 0
        ttk.Label(parent, text="Number (dec or 0x…):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_input_var = tk.StringVar()
        int_entry = ttk.Entry(parent, textvariable=self.int_input_var)
        int_entry.grid(row=r, column=1, sticky="ew")
        btns = ttk.Frame(parent)
        btns.grid(row=r, column=2, sticky="w")
        ttk.Button(btns, text="Paste", command=lambda: (self.paste_into(self.int_input_var), self._update_from_int())).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Clear", command=lambda: (self.int_input_var.set(""), self._update_from_int())).pack(side="left")
        r += 1

        ctrl = ttk.Frame(parent)
        ctrl.grid(row=r, column=1, sticky="w", pady=(2, 8))
        ttk.Label(parent, text="Width (bytes):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.width_var = tk.IntVar(value=4)
        ttk.Spinbox(ctrl, from_=1, to=MAX_BYTES, textvariable=self.width_var, width=5).pack(side="left", padx=(0, 10))
        self.signed_chk_var = tk.IntVar(value=0)
        ttk.Checkbutton(ctrl, text="Signed (allow negatives)", variable=self.signed_chk_var,
                        command=self._update_from_int).pack(side="left"); r += 1

        self.int_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.int_error_var, foreground="#8B0000").grid(row=r, column=1, sticky="w"); r += 1

        # Outputs
        ttk.Label(parent, text="Bytes (per selected endianness):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_bytes_hex_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_bytes_hex_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Binary (8b groups):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_bin_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_bin_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Text (ASCII, '.' for non-printables):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_text_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_text_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Scalar hex (no width):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_hex_scalar_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_hex_scalar_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Scalar decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_decimal_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_decimal_btns.grid(row=r, column=1, sticky="ew"); r += 1

        # Live updates
        self.int_input_var.trace_add("write", lambda *_: self._update_from_int())
        self.width_var.trace_add("write", lambda *_: self._update_from_int())
        int_entry.focus()
        # initial compute
        self.int_input_var.set("0xE808B004")

    def _update_from_int(self) -> None:
        if not hasattr(self, "int_input_var"):
            return
        try:
            val = parse_int_maybe(self.int_input_var.get())
            width = min(max(1, int(self.width_var.get())), MAX_BYTES)
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
            self.int_bytes_hex_btns.set_values([" ".join(f"{x:02X}" for x in data)])
            self.int_bin_btns.set_values([f"{x:08b}" for x in data])
            self.int_text_btns.set_values(bytes_to_ascii_runs(data))

            # Scalar values
            if val < 0:
                # two's complement representation for the chosen width
                scalp = int.from_bytes(data, byteorder="big", signed=False)
                hex_str = f"0x{scalp:X}"
            else:
                hex_str = hex(val)
            self.int_hex_scalar_btns.set_values([hex_str])
            self.int_decimal_btns.set_values([str(val)])
            self.int_error_var.set("")
        except Exception as exc:
            self.int_error_var.set(str(exc))
            self._clear_int_outputs()

    def _clear_int_outputs(self) -> None:
        if hasattr(self, "int_bytes_hex_btns"):
            self.int_bytes_hex_btns.set_values([])
            self.int_bin_btns.set_values([])
            if hasattr(self, "int_text_btns"):
                self.int_text_btns.set_values([])
            if hasattr(self, "int_hex_scalar_btns"):
                self.int_hex_scalar_btns.set_values([])
            if hasattr(self, "int_decimal_btns"):
                self.int_decimal_btns.set_values([])

    # ===========================================================
    # ============  STRING MODE (text -> bytes …) ===============
    # ===========================================================
    def _build_string_ui(self, parent: ttk.Frame) -> None:
        r = 0
        ttk.Label(parent, text="String (ASCII shown; non-printables become '.')").grid(
            row=r, column=0, sticky="w", padx=(0, 8)
        )
        self.str_input_var = tk.StringVar()
        str_entry = ttk.Entry(parent, textvariable=self.str_input_var)
        str_entry.grid(row=r, column=1, sticky="ew")
        btns = ttk.Frame(parent)
        btns.grid(row=r, column=2, sticky="w")
        ttk.Button(btns, text="Paste", command=lambda: (self.paste_into(self.str_input_var), self._update_from_str())).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Clear", command=lambda: (self.str_input_var.set(""), self._update_from_str())).pack(side="left")
        r += 1

        self.str_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.str_error_var, foreground="#8B0000").grid(row=r, column=1, sticky="w"); r += 1

        # Hex groups (per-group endianness) + Decimals + Binary + Text (runs of printable)
        ttk.Label(parent, text="Hex groups (endianness per group):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.str_hex_group_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_hex_group_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Unsigned decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.str_unsigned_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_unsigned_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Signed decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.str_signed_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_signed_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Binary (8b groups):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.str_bin_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_bin_btns.grid(row=r, column=1, sticky="ew"); r += 1

        ttk.Label(parent, text="Text (grouped printables):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.str_text_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_text_btns.grid(row=r, column=1, sticky="ew"); r += 1

        # Live updates
        self.str_input_var.trace_add("write", lambda *_: self._update_from_str())
        str_entry.focus()
        # initial compute
        self.str_input_var.set("Hello, CAN!")

    def _update_from_str(self) -> None:
        if not hasattr(self, "str_input_var"):
            return
        try:
            raw = self.str_input_var.get().encode("latin-1", errors="replace")
            self.str_error_var.set("")
            if not raw:
                self.str_hex_group_btns.set_values([])
                self.str_unsigned_btns.set_values([])
                self.str_signed_btns.set_values([])
                self.str_bin_btns.set_values([])
                self.str_text_btns.set_values([])
                return

            endian = self.endian_var.get()
            mode = self.group_mode_var.get()

            if mode == "custom":
                sizes = self._parse_groups_pattern(self.custom_groups_var.get())

                # HEX via logic helper
                self.str_hex_group_btns.set_values(group_bytes_into_hex_custom(raw, sizes, endian))

                # Build chunks as in HEX mode
                chunks: list[bytes] = []
                i = 0
                for sz in sizes:
                    if sz <= 0:
                        continue
                    if i >= len(raw):
                        break
                    chunks.append(raw[i:i+sz])
                    i += sz
                if i < len(raw):
                    chunks.append(raw[i:])
                if endian == "little":
                    chunks = [bytes(reversed(ch)) for ch in chunks]

                # Decimals
                u_vals = [str(int.from_bytes(ch, "big", signed=False)) for ch in chunks]
                s_vals = [str(int.from_bytes(ch, "big", signed=True))  for ch in chunks]
                self.str_unsigned_btns.set_values(u_vals)
                self.str_signed_btns.set_values(s_vals)

                # Binary
                bin_groups = [" ".join(f"{b:08b}" for b in ch) for ch in chunks]
                self.str_bin_btns.set_values(bin_groups)

            else:
                g = int(mode) if mode in {"1", "2", "4", "8"} else 1

                # HEX via logic helper
                self.str_hex_group_btns.set_values(group_bytes_into_hex(raw, g, endian))

                # Decimals via logic helper
                u_vals, s_vals = group_bytes_to_ints(raw, endian=endian, group_size=g)
                self.str_unsigned_btns.set_values([str(v) for v in u_vals])
                self.str_signed_btns.set_values([str(v) for v in s_vals])

                # Binary per chunk
                chunks = [raw[i:i+g] for i in range(0, len(raw), g)]
                if endian == "little":
                    chunks = [bytes(reversed(ch)) for ch in chunks]
                self.str_bin_btns.set_values([" ".join(f"{b:08b}" for b in ch) for ch in chunks])

            # ASCII runs across whole payload
            self.str_text_btns.set_values(bytes_to_ascii_runs(raw))

        except Exception as exc:
            self.str_error_var.set(str(exc))
            self.str_hex_group_btns.set_values([])
            self.str_unsigned_btns.set_values([])
            self.str_signed_btns.set_values([])
            self.str_bin_btns.set_values([])
            self.str_text_btns.set_values([])


def run() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


def main() -> None:
    run()
