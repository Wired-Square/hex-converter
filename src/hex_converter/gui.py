# hex_converter/gui.py

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from functools import partial

from .gui_menu import (
    MENU_SPEC,
    _platform_keycfg,
    _resolve_shortcut,
    build_menubar,
    show_about_dialog,
    show_shortcuts_dialog,
)
from .logic import (
    MAX_BYTES,
    bytes_to_ascii_runs,
    bytes_to_int,
    bytes_to_ones_complement,
    bytes_to_sign_magnitude,
    parse_hex_bytes,
    parse_groups_pattern,
    parse_int_maybe,
    int_range_for,
    int_to_bytes,
    group_bytes_into_hex,
    group_bytes_into_hex_custom,
    group_bytes_to_ints,
    int_to_ones_complement,
    int_to_sign_magnitude,
)


class BitToggleField(ttk.Frame):
    """Render checkboxes for each bit of a byte sequence (in given order)."""
    def __init__(self, parent, on_bits_changed):
        super().__init__(parent)
        self._vars: list[tuple[int, int, tk.IntVar]] = []  # (byte_index, bit, var)
        self._on_bits_changed = on_bits_changed

    def set_bits(self, data: bytes) -> None:
        """Rebuild the UI for the given bytes (display order: MSB..LSB)."""
        # Nuke previous
        for w in self.winfo_children():
            w.destroy()
        self._vars.clear()

        if not data:
            return

        # Build one grid row per byte: [Label][b7][b6][b5][b4][b3][b2][b1][b0]
        for byte_index, b in enumerate(data):
            row = ttk.Frame(self)
            row.grid(row=byte_index, column=0, sticky="w", pady=(0, 2))

            # Fixed-width label so bit columns start at the same x for every row
            # width is in characters; adjust to taste if your font is wider/narrower
            ttk.Label(row, text=f"Byte {byte_index:02d}:", width=9)\
                .grid(row=0, column=0, sticky="w", padx=(0, 6))

            row_checks = []
            # MSB..LSB laid out left→right as columns 1..8
            for col, bit in enumerate(range(7, -1, -1), start=1):
                v = tk.IntVar(value=(b >> bit) & 1)
                chk = ttk.Checkbutton(row, variable=v, command=self._make_callback())
                # Kill any internal padding to keep columns tight
                try:
                    chk.configure(padding=0)
                except Exception:
                    pass
                chk.grid(row=0, column=col, sticky="w", padx=(0, 0), pady=0, ipadx=0, ipady=0)
                self._vars.append((byte_index, bit, v))
                row_checks.append(chk)

            # Give each bit-column a consistent pixel width so columns align across rows
            # Measure once from this row's checkbuttons (works cross-platform)
            try:
                self.update_idletasks()
                col_w = max(cb.winfo_reqwidth() for cb in row_checks) if row_checks else 18
            except Exception:
                col_w = 18  # safe fallback

            for col in range(1, 9):
                row.grid_columnconfigure(col, minsize=col_w, weight=0)

            # Keep the label column non-stretchy as well
            row.grid_columnconfigure(0, weight=0)

    def _make_callback(self):
        return lambda: self._on_bits_changed(self.get_bytes())

    def get_bytes(self) -> bytes:
        """Return the current bytes represented by the toggles (display order)."""
        if not self._vars:
            return b""

        grouped: dict[int, list[tuple[int, tk.IntVar]]] = {}
        for byte_index, bit, v in self._vars:
            grouped.setdefault(byte_index, []).append((bit, v))

        out = bytearray()
        for byte_index in sorted(grouped):
            val = 0
            for bit, v in grouped[byte_index]:
                if v.get():
                    val |= (1 << bit)
            out.append(val)

        return bytes(out)


class MultiRowField(ttk.Frame):
    """Render N rows of copyable buttons in aligned columns with wrapping.
    width_strategy: "min" (narrowest) or "max" (widest) per column/view.
    """
    def __init__(
        self,
        parent,
        on_copy,
        wrap: int = 16,
        # "view" = global width, "column" = per-column widths
        compact_by: str = "view",
        # "min" = narrowest fit, "max" = widest fit
        width_strategy: str = "max",
        pad_chars: int = 0
    ):
        """
        MultiRowField constructor.

        Args:
            parent: parent widget
            on_copy: callback function (value, button) -> None
            wrap: number of columns before wrapping
            compact_by: "view" (same width for all) or "column" (width computed per column)
            width_strategy: "min" (narrowest) or "max" (widest)
            pad_chars: characters of extra width padding to avoid clipping
        """
        super().__init__(parent)

        # Core behavior
        self._on_copy = on_copy
        self._wrap = wrap
        self._compact_by = compact_by
        self._width_strategy = width_strategy
        self._pad_chars = pad_chars

        # Track layout widgets
        self._blocks: list[ttk.Frame] = []
        self._buttons: list[ttk.Button] = []

        # Styling
        self._style = ttk.Style(self)
        base = "Toolbutton"
        try:
            # On unsupported themes this raises TclError
            _ = self._style.layout(base)
        except tk.TclError:
            base = "TButton"

        self._cell_style = f"ByteCell.{base}"

        self._style.configure(
            self._cell_style,
            padding=0,
            borderwidth=0,
            relief="flat"
        )

        self._style.map(
            self._cell_style,
            relief=[('pressed', 'sunken'), ('!pressed', 'flat')]
        )

    def clear(self) -> None:
        for f in self._blocks:
            f.destroy()
        self._blocks.clear()
        self._buttons.clear()

    def set_values(
        self,
        rows: list[list[str]] | list[str],
        *,
        pad: tuple[int, int] = (0, 0),        # (padx, pady) for each cell
        anchor: str = "w",                    # left-align long strings
        monospaced: bool = True,              # helps binary readability
    ) -> None:
        """
        Render a matrix of values as buttons. `rows` can be:
        - list[list[str]]  -> multiple rows
        - list[str]        -> treated as a single row

        Uses:
        - self._wrap (columns per block)
        - self._compact_by: "column" or "view"
        - self._width_strategy: "min" or "max"
        - self._pad_chars: extra characters of width padding
        """
        # Normalize input to a 2D list
        if not rows:
            self.clear()
            return
        if rows and all(isinstance(x, str) for x in rows):
            rows = [list(rows)]  # single row

        # Clear previous layout
        self.clear()

        # Basic shape
        max_cols = max((len(r) for r in rows), default=0)
        if max_cols == 0:
            return

        # Compute per-column widths (in "characters")
        lengths_by_col: list[list[int]] = [[] for _ in range(max_cols)]
        for r in rows:
            for c, v in enumerate(r):
                txt = "" if v is None else str(v)
                lengths_by_col[c].append(len(txt))

        def choose_width(nums: list[int]) -> int:
            if not nums:
                return 1
            if getattr(self, "_width_strategy", "min") == "max":
                return max(nums)
            return min(nums)

        if getattr(self, "_compact_by", "view") == "column":
            col_widths = [max(1, choose_width(lens)) for lens in lengths_by_col]
        else:
            # Global width across all cells
            all_lengths = [n for col in lengths_by_col for n in col]
            global_w = max(1, choose_width(all_lengths))
            col_widths = [global_w] * max_cols

        # Apply padding
        pad_chars = int(getattr(self, "_pad_chars", 0) or 0)
        col_widths = [max(1, w + pad_chars) for w in col_widths]

        # Optional monospaced font for better binary readability
        if monospaced:
            try:
                self._style.configure(self._cell_style, font=("TkFixedFont", 11))
            except Exception:
                pass

        padx, pady = pad
        running_idx = 0
        block_idx = 0

        while running_idx < max_cols:
            take = min(self._wrap, max_cols - running_idx)
            block = ttk.Frame(self)
            block.grid(row=block_idx, column=0, sticky="w")
            self._blocks.append(block)

            for r_index, row_vals in enumerate(rows):
                for col_idx in range(take):
                    abs_col = running_idx + col_idx
                    if abs_col < len(row_vals):
                        val = row_vals[abs_col]
                        text = "" if val is None else str(val)
                        btn = ttk.Button(block, text=text, style=self._cell_style)
                        # width & anchor
                        try:
                            btn.config(width=col_widths[abs_col], anchor=anchor, padding=0)
                        except Exception:
                            btn.config(width=col_widths[abs_col], padding=0)
                        if hasattr(self, "_on_copy"):
                            btn.config(command=lambda v=text, b=btn: self._on_copy(v, b))
                        btn.grid(
                            row=r_index,
                            column=col_idx,
                            padx=padx,
                            pady=pady,
                            ipadx=0,
                            ipady=0,
                            sticky="w"
                        )
                        self._buttons.append(btn)
                    else:
                        # keep the grid aligned when this row is shorter
                        ttk.Label(block, text="").grid(row=r_index, column=col_idx, padx=padx, pady=pady, sticky="w")

            # Align columns within this block
            for col_idx in range(take):
                block.grid_columnconfigure(col_idx, weight=0)

            running_idx += take
            block_idx += 1


class CopyButtonsField(ttk.Frame):
    """Render N buttons in a horizontal row that expands with the window width."""
    def __init__(self, parent, on_copy):
        super().__init__(parent)
        self._buttons: list[ttk.Button] = []
        self._on_copy = on_copy

    def clear_buttons(self) -> None:
        """Remove all existing buttons from the field."""
        for btn in self._buttons:
            btn.destroy()
        self._buttons.clear()

    def set_values(self, values: list[str], button_width: int | None = None) -> None:
        """Replace current buttons with a new set of buttons."""
        self.clear_buttons()

        for val in values:
            btn = ttk.Button(self, text=val)

            if button_width is not None:
                btn.config(width=button_width)

            btn.config(command=partial(self._on_copy, val, btn))
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

        # Shared variables
        self.endian_var = tk.StringVar(value="little")
        self.mode_var = tk.StringVar(value="HEX")
        self.group_mode_var = tk.StringVar(value="1")
        self.custom_groups_var = tk.StringVar(value="")
        self._bit_display_chunk_sizes: list[int] = []
        self.str_group_mode_var = tk.StringVar(value="1")
        self.str_custom_groups_var = tk.StringVar(value="")

        # Build shared UI
        build_menubar(self.root, self)
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


    # ----------------- Controls bar -----------------
    def _build_controls_bar(self, row: int) -> None:
        # Mode select
        ttk.Label(self.main, text="Mode:").grid(row=row, column=0, sticky="w", padx=(0, 8))
        mode_frame = ttk.Frame(self.main)
        mode_frame.grid(row=row, column=1, sticky="w")
        for m in self.MODES:
            ttk.Radiobutton(
                mode_frame,
                text=m,
                value=m,
                variable=self.mode_var,
                command=self._render_mode
            ).pack(side="left", padx=(0, 10))

        # Endianness (applies per group)
        ttk.Label(self.main, text="Endianness:").grid(row=row+1, column=0, sticky="w", padx=(0, 8))
        endian_frame = ttk.Frame(self.main)
        endian_frame.grid(row=row+1, column=1, sticky="w", pady=(0, 8))

        for endianness in ("Little","Big"):
            ttk.Radiobutton(
                endian_frame,
                text=endianness,
                variable=self.endian_var,
                value=endianness.lower(),
                command=self._update_current_mode
            ).pack(side="left", padx=(0,10))

        # Live updates when typing custom pattern
        self.custom_groups_var.trace_add("write", lambda *_: self._update_current_mode())

    def _show_about(self):
        show_about_dialog(self, self.root)

    def _show_shortcuts(self):
        show_shortcuts_dialog(self, self.root)

    def _toggle_endian(self, _event=None) -> None:
        self.endian_var.set("big" if self.endian_var.get() == "little" else "little")
        self._update_current_mode()

    def _set_mode(self, mode: str) -> None:
        self.mode_var.set(mode)
        self._render_mode()


    # ----------------- Mode rendering -----------------
    def _on_group_mode_changed(self, scope: str) -> None:
        """
        Enable/disable the custom group entry for the given scope ('HEX' | 'Number' | 'String')
        and trigger that scope's update.
        """
        # Map each scope to (group_mode_var, custom_entry_widget, update_fn)
        mapping = {
            "HEX": (
                getattr(self, "hex_group_mode_var", None),
                getattr(self, "hex_custom_groups_entry", None),
                self._update_from_hex,
            ),
            "Number": (
                getattr(self, "group_mode_var", None),
                getattr(self, "custom_groups_entry", None),
                self._update_from_number,
            ),
            "String": (
                getattr(self, "str_group_mode_var", None),
                getattr(self, "str_custom_groups_entry", None),
                self._update_from_string,
            ),
        }

        group_var, custom_entry, update_fn = mapping.get(scope, (None, None, self._update_current_mode))

        # Safely enable/disable the custom pattern entry
        is_custom = False
        if group_var is not None:
            try:
                is_custom = (group_var.get() == "custom")
            except Exception:
                is_custom = False

        if custom_entry is not None:
            try:
                custom_entry.configure(state="normal" if is_custom else "disabled")
            except Exception:
                pass

        # Refresh just this scope
        update_fn()

    def _render_mode(self) -> None:
        # Clear current content
        for w in self.content.winfo_children():
            w.destroy()

        mode = self.mode_var.get()
        if mode == "HEX":
            self._build_hex_ui(self.content)
            self._on_group_mode_changed("HEX")
        elif mode == "Number":
            self._build_number_ui(self.content)
        else:
            self._build_string_ui(self.content)

    def _set_error_state(self, msg: str) -> None:
        if hasattr(self, "hex_error_var"):
            self.hex_error_var.set(msg)
        else:
            print("Error:", msg)

    def _toggle_compact(self):
        """Toggle compact view mode for byte rows and refresh UI."""
        self.compact_mode = not getattr(self, "compact_mode", False)

        # Update ByteRowsField styling (e.g., reduce padding when compact)
        if hasattr(self, "str_bytes_grid"):
            for btn in self.str_bytes_grid._buttons:
                btn.config(padding=0 if self.compact_mode else 4)

        self._update_current_mode()

    def _update_current_mode(self) -> None:
        # Trigger appropriate update handler for current mode
        mode = self.mode_var.get()
        if mode == "HEX":
            self._update_from_hex()
        elif mode == "Number":
            self._update_from_number()
        else:
            self._update_from_string()


    # ----------------- Clipboard helpers -----------------
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


    # ===========================================================
    # ===============  HEX MODE (bytes -> …) ====================
    # ===========================================================
    def _build_hex_ui(self, parent: ttk.Frame) -> None:
        r = 0

        # Input
        ttk.Label(parent, text="Hex bytes (≤8):").grid(row=r, column=0, sticky="w", padx=(0, 8))

        input_frame = ttk.Frame(parent)
        input_frame.grid(row=r, column=1, sticky="w")

        self.hex_input_var = tk.StringVar()
        entry = ttk.Entry(input_frame, textvariable=self.hex_input_var, width=24)
        entry.grid(row=0, column=0, sticky="w")

        ttk.Button(
            input_frame, text="Paste",
            command=lambda: (self.paste_into(self.hex_input_var), self._update_from_hex())
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Button(
            input_frame, text="Clear",
            command=lambda: (self.hex_input_var.set(""), self._update_from_hex())
        ).grid(row=0, column=2, sticky="w", padx=(6, 0))
        r += 1

        # Error messages
        self.hex_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.hex_error_var, foreground="#8B0000").grid(row=r, column=1, sticky="w")
        r += 1

        # Grouping controls
        ttk.Label(parent, text="Group bytes as:").grid(row=r, column=0, sticky="w", padx=(0, 8))

        hex_group_frame = ttk.Frame(parent)
        hex_group_frame.grid(row=r, column=1, sticky="w", pady=(0, 8))

        self.hex_group_mode_var = tk.StringVar(value="1")    # '1','2','4','8','custom'
        self.hex_custom_groups_var = tk.StringVar(value="")  # e.g. "1,1,6"

        # Radios in one row: 1B, 2B, 4B, 8B, Custom
        for idx, val in enumerate(("1", "2", "4", "8", "custom"), start=1):
            ttk.Radiobutton(
                hex_group_frame,
                text="Custom" if val == "custom" else f"{val}B",
                value=val,
                variable=self.hex_group_mode_var,
                command=lambda: self._on_group_mode_changed("HEX"),
            ).grid(row=0, column=idx, sticky="w", padx=(0, 6))

        # Compact custom pattern entry + hint
        self.hex_custom_groups_entry = ttk.Entry(
            hex_group_frame,
            textvariable=self.hex_custom_groups_var,
            width=10
        )
        self.hex_custom_groups_entry.grid(row=0, column=6, sticky="w", padx=(10, 4))
        ttk.Label(hex_group_frame, text="e.g., 1,1,6").grid(row=0, column=7, sticky="w")

        # Keep it tight — no column stretch
        for i in range(8):
            hex_group_frame.grid_columnconfigure(i, weight=0)

        r += 1

        # Outputs
        ttk.Label(parent, text="Hex groups:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.hex_group_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.hex_group_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Unsigned decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.unsigned_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.unsigned_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Signed 2's complement:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.signed_twos_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.signed_twos_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Signed 1's complement:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.signed_ones_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.signed_ones_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Signed sign-magnitude:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.signed_signmag_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.signed_signmag_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Binary:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.bin_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.bin_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Toggle bits:").grid(row=r, column=0, sticky="nw", padx=(0, 8))
        self.bit_toggles = BitToggleField(parent, on_bits_changed=self._update_from_bits)
        self.bit_toggles.grid(row=r, column=1, sticky="w")
        r += 1

        ttk.Label(parent, text="Text (ASCII or .):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.text_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.text_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        # --- Wire events AFTER widgets exist ---
        # Custom pattern live updates
        self.hex_custom_groups_var.trace_add("write", lambda *_: self._update_from_hex())
        # Enable/disable the custom entry now that it exists
        self._on_group_mode_changed("HEX")

        # Input live updates
        self.hex_input_var.trace_add("write", lambda *_: self._update_from_hex())
        entry.focus()

        # Initial compute (safe now)
        self.hex_input_var.set("E8 08 B0 04 00 00 2C 01")

    def _update_from_hex(self) -> None:
        try:
            data = parse_hex_bytes(self.hex_input_var.get())
            if not data:
                self.hex_group_btns.set_values([])
                self.unsigned_btns.set_values([])
                self.signed_twos_btns.set_values([])
                self.signed_ones_btns.set_values([])
                self.signed_signmag_btns.set_values([])
                self.bin_btns.set_values([])
                self.bit_toggles.set_bits(b"")
                self.text_btns.set_values([])
                self._bit_display_chunk_sizes = []
                if hasattr(self, "hex_error_var"):
                    self.hex_error_var.set("")
                return

            # Grouping
            mode = self.hex_group_mode_var.get()
            if mode == "custom":
                sizes = parse_groups_pattern(self.hex_custom_groups_var.get())
                hex_groups = group_bytes_into_hex_custom(data, sizes, self.endian_var.get())
            else:
                g = int(mode)
                hex_groups = group_bytes_into_hex(data, g, self.endian_var.get())
            self.hex_group_btns.set_values(hex_groups)

            # Update chunk sizes for toggles
            self._bit_display_chunk_sizes = [len(bytes.fromhex(g.replace(" ",""))) for g in hex_groups]

            # Unsigned/Signed conversions
            u_vals, s_vals = group_bytes_to_ints(data, endian=self.endian_var.get(), group_size=1)
            self.unsigned_btns.set_values(u_vals)
            self.signed_twos_btns.set_values(s_vals)
            self.signed_ones_btns.set_values([bytes_to_ones_complement(data)])
            self.signed_signmag_btns.set_values([bytes_to_sign_magnitude(data)])

            # Binary and Bit toggles
            self.bin_btns.set_values([f"{b:08b}" for b in data])
            self.bit_toggles.set_bits(data)

            # ASCII / Text
            self.text_btns.set_values(bytes_to_ascii_runs(data))

            if hasattr(self, "hex_error_var"):
                self.hex_error_var.set("")

        except ValueError as e:
            self._set_error_state(str(e))

    def _update_from_bits(self, new_display_bytes: bytes) -> None:
        """
        Called when the user toggles bits in the display order (i.e., the same
        order shown in the Binary row where per-chunk endianness has been applied).
        Convert back to canonical input order before writing to the hex field.
        """
        sizes = getattr(self, "_bit_display_chunk_sizes", []) or [len(new_display_bytes)]
        endian = self.endian_var.get()

        out = bytearray()
        i = 0
        for sz in sizes:
            seg = new_display_bytes[i:i+sz]
            # Undo per-chunk endianness for canonical input order
            if endian == "little":
                seg = seg[::-1]
            out.extend(seg)
            i += sz

        # Any leftover (unlikely) — treat as one more chunk
        if i < len(new_display_bytes):
            seg = new_display_bytes[i:]
            if endian == "little":
                seg = seg[::-1]
            out.extend(seg)

        # Writing to the input triggers a full recompute
        self.hex_input_var.set(" ".join(f"{b:02X}" for b in out))


    # ===========================================================
    # =============  NUMBER MODE (int -> bytes …) ===============
    # ===========================================================
    def _build_number_ui(self, parent: ttk.Frame) -> None:
        r = 0

        ttk.Label(parent, text="Number (dec or 0x…):").grid(row=r, column=0, sticky="w", padx=(0, 8))

        input_frame = ttk.Frame(parent)
        input_frame.grid(row=r, column=1, sticky="w")

        self.num_input_var = tk.StringVar()
        int_entry = ttk.Entry(input_frame, textvariable=self.num_input_var, width=20)
        int_entry.grid(row=0, column=0, sticky="w")

        ttk.Button(
            input_frame, text="Paste",
            command=lambda: (self.paste_into(self.num_input_var), self._update_from_number())
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Button(
            input_frame, text="Clear",
            command=lambda: (self.num_input_var.set(""), self._update_from_number())
        ).grid(row=0, column=2, sticky="w", padx=(6, 0))
        r += 1

        ctrl = ttk.Frame(parent)
        ctrl.grid(row=r, column=1, sticky="w", pady=(2, 8))
        ttk.Label(parent, text="Width (bytes):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.width_var = tk.IntVar(value=4)
        ttk.Spinbox(ctrl, from_=1, to=MAX_BYTES, textvariable=self.width_var, width=5).pack(side="left", padx=(0, 10))

        # Representation drop-down
        ttk.Label(ctrl, text="Representation:").pack(side="left", padx=(10,2))
        self.repr_var = tk.StringVar(value="Unsigned")
        repr_options = ["Unsigned", "Signed (2's complement)", "Signed (1's complement)", "Signed (Sign-magnitude)"]
        ttk.OptionMenu(ctrl, self.repr_var, self.repr_var.get(), *repr_options, command=lambda _: self._update_from_number()).pack(side="left")
        r += 1

        # Valid range label (updates with width/representation)
        self.int_range_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.int_range_var, foreground="#006400").grid(row=r, column=1, sticky="w")
        r += 1

        # Error label
        self.int_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.int_error_var, foreground="#8B0000").grid(row=r, column=1, sticky="w")
        r += 1

        # Outputs
        ttk.Label(parent, text="Bytes (per selected endianness):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_bytes_hex_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_bytes_hex_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Binary (8b groups):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_bin_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_bin_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Toggle bits:").grid(row=r, column=0, sticky="nw", padx=(0, 8))
        self.num_bit_toggles = BitToggleField(parent, on_bits_changed=self._update_number_from_bits)
        self.num_bit_toggles.grid(row=r, column=1, sticky="w")
        r += 1

        # Additional outputs
        ttk.Label(parent, text="Text (ASCII, '.' for non-printables):").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_text_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_text_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Scalar hex:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_hex_scalar_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_hex_scalar_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        ttk.Label(parent, text="Scalar decimal:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        self.int_decimal_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.int_decimal_btns.grid(row=r, column=1, sticky="ew")
        r += 1

        # Live updates
        self.num_input_var.trace_add("write", lambda *_: self._update_from_number())
        self.width_var.trace_add("write", lambda *_: self._update_from_number())
        int_entry.focus()
        self.num_input_var.set("0xE808B004")

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

    def _update_from_number(self) -> None:
        if not hasattr(self, "num_input_var"):
            return
        try:
            val = parse_int_maybe(self.num_input_var.get())
            width = min(max(1, int(self.width_var.get())), MAX_BYTES)
            endian = self.endian_var.get()
            mode = self.repr_var.get()

            # Keep the range label in sync even when parsing succeeds
            self._update_number_range_label()

            # Convert integer to bytes using centralized logic
            data = int_to_bytes(val, width, mode, endian)

            # Update outputs
            self.int_bytes_hex_btns.set_values([" ".join(f"{b:02X}" for b in data)])
            self.int_bin_btns.set_values([f"{b:08b}" for b in data])
            self.num_bit_toggles.set_bits(data)
            self.int_text_btns.set_values(bytes_to_ascii_runs(data))
            self.int_hex_scalar_btns.set_values([hex(val & ((1 << (width*8))-1))])
            self.int_decimal_btns.set_values([str(val)])
            self.int_error_var.set("")

        except Exception as exc:
            self._update_number_range_label()
            self.int_error_var.set(str(exc))
            self._clear_int_outputs()
            self.num_bit_toggles.set_bits(b"")

    def _update_number_from_bits(self, new_display_bytes: bytes) -> None:
        """
        Called when toggles in Number View change.
        Updates the numeric input according to the current representation and endianness.
        """
        if not hasattr(self, "num_input_var"):
            return

        endian = self.endian_var.get()
        mode = self.repr_var.get()
        width = min(max(1, int(self.width_var.get())), MAX_BYTES)

        # Apply little-endian display reversal if needed
        if endian == "little":
            data = new_display_bytes[::-1]
        else:
            data = new_display_bytes

        try:
            val = bytes_to_int(data, mode, "big")  # bytes_to_int expects logical "big" order
            self.num_input_var.set(str(val))
            self.int_error_var.set("")
        except Exception as exc:
            self.int_error_var.set(str(exc))

    def _update_number_range_label(self) -> None:
        """Compute and display the valid range for current width/representation."""
        if not hasattr(self, "width_var") or not hasattr(self, "repr_var"):
            return
        width = max(1, min(MAX_BYTES, int(self.width_var.get() or 1)))
        mode = self.repr_var.get()

        if mode == "Unsigned":
            lo, hi = int_range_for(width, signed=False)
        elif mode == "Signed (2's complement)":
            lo, hi = int_range_for(width, signed=True)
        else:
            # 1's complement and sign-magnitude share the same numeric bounds:
            # [-(2^(n-1)-1), 2^(n-1)-1]
            nbits = 8 * width
            hi = (1 << (nbits - 1)) - 1
            lo = -hi
        self.int_range_var.set(f"Valid range: {lo:,} to {hi:,}")

    # ===========================================================
    # ============  STRING MODE (text -> bytes …) ===============
    # ===========================================================
    def _build_string_ui(self, parent: ttk.Frame) -> None:
        r = 0

        # Controls: Input row
        input_frame = ttk.Frame(parent)
        input_frame.grid(row=r, column=0, sticky="w")

        # Entry Box
        self.str_input_var = tk.StringVar()
        str_entry = ttk.Entry(input_frame, textvariable=self.str_input_var, width=20)
        str_entry.grid(row=0, column=0, sticky="w")

        # Buttons
        ttk.Button(input_frame, text="Paste",
                command=lambda: (self.paste_into(self.str_input_var), self._update_from_string())
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Button(input_frame, text="Clear",
                command=lambda: (self.str_input_var.set(""), self._update_from_string())
        ).grid(row=0, column=2, sticky="w", padx=(6, 0))
        r += 1

        # Error messages
        self.str_error_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.str_error_var, foreground="#8B0000").grid(row=r, column=0, sticky="w")
        r += 1

        # (BYTES)
        ttk.Label(parent, text="Individual Bytes:").grid(row=r, column=0, sticky="w", padx=(0, 8))
        r += 1

        # Row 1/2 (BYTES): Hex + Binary per byte, aligned & compact
        label_frame = ttk.Frame(parent)
        label_frame.grid(row=r, column=0, sticky="w")

        self.str_bytes_grid = MultiRowField(parent, on_copy=self.copy_value, wrap=16, compact_by="column")
        self.str_bytes_grid.grid(row=r, column=0, sticky="w")
        r += 1

        # Row 3 (BYTES): Text (printable runs)
        self.str_text_byte_btns = CopyButtonsField(parent, on_copy=self.copy_value)
        self.str_text_byte_btns.grid(row=r, column=0, sticky="ew")
        r += 1

        # UI Separator — horizontal line
        ttk.Separator(parent, orient="horizontal").grid(row=r, column=0, columnspan=4, sticky="ew", pady=(6, 10))
        r += 1

        # Controls: String-mode grouping
        str_group_frame = ttk.Frame(parent)
        str_group_frame.grid(row=r, column=0, sticky="w", pady=(0, 8))

        ttk.Label(str_group_frame, text="Group bytes as:").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8)
        )

        # Radio buttons for group size
        for idx, val in enumerate(("1", "2", "4", "8", "custom"), start=1):
            ttk.Radiobutton(
                str_group_frame,
                text="Custom" if val == "custom" else f"{val}B",
                value=val,
                variable=self.str_group_mode_var,
                command=lambda: self._on_group_mode_changed("String"),
            ).grid(row=0, column=idx, sticky="w", padx=(0, 6))

        # Entry box for custom group sizes
        self.str_custom_groups_entry = ttk.Entry(
            str_group_frame,
            textvariable=self.str_custom_groups_var,
            width=10
        )
        self.str_custom_groups_entry.grid(row=0, column=6, sticky="w", padx=(10, 4))

        # Helper label for example
        ttk.Label(str_group_frame, text="e.g., 1,1,6").grid(row=0, column=7, sticky="w")

        # Configure the frame to keep things compact
        for i in range(7):
            str_group_frame.columnconfigure(i, weight=0)

        r += 1

        # Live updates when typing custom pattern
        self.str_custom_groups_var.trace_add("write", lambda *_: self._update_from_string())

        # (GROUPS): Values
        self.str_groups_grid = MultiRowField(parent, on_copy=self.copy_value, wrap=16, compact_by="column")
        self.str_groups_grid.grid(row=r, column=0, sticky="ew")
        r += 1

        # Initialize enable/disable state now that widgets exist
        self._on_group_mode_changed("String")

        # Live updates
        self.str_input_var.trace_add("write", lambda *_: self._update_from_string())
        str_entry.focus()

        # Initial compute
        self.str_input_var.set("Hello, CAN!")

    def _update_from_string(self) -> None:
        if not hasattr(self, "str_input_var"):
            return
        try:
            raw = self.str_input_var.get().encode("latin-1", errors="replace")
            self.str_error_var.set("")

            if not raw:
                # Clear all outputs (bytes + groups)
                self.str_text_byte_btns.set_values([])
                return

            endian = self.endian_var.get()
            mode = self.str_group_mode_var.get()

            # ----- Byte view -----
            hex_vals = [f"{b:02X}" for b in raw]
            bin_vals = [f"{b:08b}" for b in raw]

            self.str_bytes_grid.set_values([hex_vals, bin_vals])
            self.str_text_byte_btns.set_values(bytes_to_ascii_runs(raw))

            # ----- Group view -----
            # Build groups consistent with hex grouping (apply endianness within each group)
            if mode == "custom":
                sizes = parse_groups_pattern(self.str_custom_groups_var.get())
                # build chunks by sizes
                chunks = []
                i = 0
                for sz in sizes:
                    if i >= len(raw): break
                    ch = raw[i:i+sz]
                    chunks.append(ch[::-1] if endian == "little" else ch)
                    i += sz
                if i < len(raw) and sizes:
                    ch = raw[i:]
                    chunks.append(ch[::-1] if endian == "little" else ch)
            else:
                g = int(mode)
                chunks = [raw[i:i+g] for i in range(0, len(raw), g)]
                if endian == "little":
                    chunks = [ch[::-1] for ch in chunks]

            # Groups
            hex_groups = [" ".join(f"{b:02X}" for b in ch) for ch in chunks]
            bin_groups = [" ".join(f"{b:08b}" for b in ch) for ch in chunks]
            text_groups = ["".join(bytes_to_ascii_runs(ch)) for ch in chunks] 
            self.str_groups_grid.set_values([hex_groups, bin_groups, text_groups])

        except Exception as exc:
            self.str_error_var.set(str(exc))
            self.str_text_byte_btns.set_values([])


def run() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


def main() -> None:
    run()