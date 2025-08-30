# hex_converter/gui_menu.py

from __future__ import annotations

import platform
import tkinter as tk
import tkinter.messagebox as mbox


# Declarative menu spec.
# "shortcut" can be a string like "MOD+L" or a list of them (e.g., ["MOD+R", "F5"]).
# Valid tokens: MOD, CTRL, CMD, ALT, SHIFT, letters (A-Z), numbers (0-9),
# named keys like ENTER, ESC, F1-F24, UP, DOWN, LEFT, RIGHT, SPACE, etc.
MENU_SPEC = [
    {
        "menu": "View",
        "items": [
            {
                "label": "Hex View",
                "command": "_set_mode",
                "command_args": ["HEX"],
                "shortcut": "CTRL+H",
            },
            {
                "label": "Number View",
                "command": "_set_mode",
                "command_args": ["Number"],
                "shortcut": "CTRL+N",
            },
            {
                "label": "String View",
                "command": "_set_mode",
                "command_args": ["String"],
                "shortcut": "CTRL+S",
            },
            {
                "type": "separator",
            },
            {
                "label": "Toggle Endianness",
                "command": "_toggle_endian",
                "shortcut": "MOD+L",
            },
            {
                "type": "separator",
            },
            {
                "label": "Compact Bytes View",
                "command": "_toggle_compact",
                "shortcut": "SHIFT+C",
            },
        ],
    },
    {
        "menu": "Help",
        "items": [
            {
                "label": "About",
                "command": "_show_about",
            },
            {
                "label": "Shortcuts…",
                "command": "_show_shortcuts",
            },
        ],
    },
]

def _platform_keycfg():
    """
    Platform-aware names for Tk bindings and user-facing labels.
    Also exposes explicit CTRL/CMD/ALT/SHIFT tokens in addition to MOD.
    """
    if platform.system() == "Darwin":
        return {
            "MOD": "Command",     "MOD_LABEL": "Cmd",
            "CTRL": "Control",    "CTRL_LABEL": "Ctrl",
            "CMD": "Command",     "CMD_LABEL": "Cmd",
            "ALT": "Option",      "ALT_LABEL": "Opt",   # mac calls it Option
            "SHIFT": "Shift",     "SHIFT_LABEL": "Shift",
        }
    else:
        return {
            "MOD": "Control",     "MOD_LABEL": "Ctrl",
            "CTRL": "Control",    "CTRL_LABEL": "Ctrl",
            "CMD": "Control",     "CMD_LABEL": "Ctrl",  # treat CMD as Control on non-mac
            "ALT": "Alt",         "ALT_LABEL": "Alt",
            "SHIFT": "Shift",     "SHIFT_LABEL": "Shift",
        }

def _resolve_shortcut(shortcut: str, keycfg: dict[str, str]) -> tuple[str, str]:
    """
    Convert tokenized shortcuts (e.g., 'MOD+SHIFT+S') into:
      - a menu accelerator label (e.g., 'Cmd+Shift+S')
      - a Tk binding sequence (e.g., '<Command-Shift-s>')
    Supported modifier tokens: MOD, CTRL, CMD, ALT, SHIFT
    Other tokens are treated as the key (single letter or a named keysym).
    """
    # Normalize once
    parts = [p.strip().upper() for p in shortcut.split("+") if p.strip()]

    KEYSYM_MAP = {
        "ENTER":  ("Enter",  "Return"),
        "RETURN": ("Return", "Return"),
        "ESC":    ("Esc",    "Escape"),
        "ESCAPE": ("Escape", "Escape"),
        "SPACE":  ("Space",  "space"),
        "TAB":    ("Tab",    "Tab"),
        "BACKSPACE": ("Backspace", "BackSpace"),
        "DELETE": ("Delete", "Delete"),
        "HOME":   ("Home",   "Home"),
        "END":    ("End",    "End"),
        "PGUP":   ("PgUp",   "Prior"),
        "PGDN":   ("PgDn",   "Next"),
        "UP":     ("Up",     "Up"),
        "DOWN":   ("Down",   "Down"),
        "LEFT":   ("Left",   "Left"),
        "RIGHT":  ("Right",  "Right"),
        **{f"F{i}": (f"F{i}", f"F{i}") for i in range(1, 25)},
        "COMMA":  (",", "comma"),
        "PERIOD": (".", "period"),
        "SLASH":  ("/", "slash"),
        "SEMICOLON": (";", "semicolon"),
        "QUOTE":  ("'", "quoteright"),
        "BACKQUOTE": ("`", "grave"),
        "MINUS":  ("-", "minus"),
        "EQUAL":  ("=", "equal"),
        "BACKSLASH": ("\\", "backslash"),
        "BRACKETLEFT": ("[", "bracketleft"),
        "BRACKETRIGHT": ("]", "bracketright"),
    }

    MOD_TOKENS = {"MOD", "CTRL", "CMD", "ALT", "SHIFT"}

    mods: list[str] = []
    key_token: str | None = None
    for up in parts:
        if up in MOD_TOKENS:
            mods.append(up)
        else:
            key_token = up  # last non-mod wins

    # Drop MOD if CMD/CTRL present
    has_cmdctrl = ("CMD" in mods) or ("CTRL" in mods)
    if has_cmdctrl and "MOD" in mods:
        mods = [m for m in mods if m != "MOD"]

    # De-duplicate modifiers (order-preserving)
    seen = set()
    mods = [m for m in mods if not (m in seen or seen.add(m))]

    # Order: if CMD/CTRL present -> CMD, CTRL, ALT, SHIFT; else -> MOD, ALT, SHIFT
    ORDER = ["CMD", "CTRL", "ALT", "SHIFT"] if has_cmdctrl else ["MOD", "ALT", "SHIFT"]

    label_parts, bind_parts = [], []
    for m in ORDER:
        if m in mods:
            label_parts.append(keycfg.get(f"{m}_LABEL", m.title()))
            bind_parts.append(keycfg.get(m, m.title()))

    if key_token is None:
        label = "+".join(label_parts) if label_parts else ""
        bind = "<" + "-".join(bind_parts) + ">" if bind_parts else ""
        return label, bind

    if key_token in KEYSYM_MAP:
        nice_label, keysym = KEYSYM_MAP[key_token]
        label_parts.append(nice_label)
        bind_parts.append(keysym)
    else:
        if len(key_token) == 1:
            label_parts.append(key_token.upper())
            bind_parts.append(key_token.lower())
        else:
            label_parts.append(key_token.title())
            bind_parts.append(key_token)

    label = "+".join(label_parts)
    bind = "<" + "-".join(bind_parts) + ">"
    return label, bind

def build_menubar(root: tk.Tk, app: object, spec: list[dict] = MENU_SPEC) -> tk.Menu:
    """
    Create and attach a menubar to `root` using `spec`, binding shortcuts to methods on `app`.
    Returns the created menubar.
    """
    keycfg = _platform_keycfg()
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    for menu_def in spec:
        m = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label=menu_def["menu"], menu=m)

        for item in menu_def.get("items", []):
            if item.get("type") == "separator":
                m.add_separator()
                continue

            label = item["label"]
            cmd_name = item["command"]
            command = getattr(app, cmd_name, None) or (lambda *a, **k: None)
            cmd_args = item.get("command_args", [])
            cmd_kwargs = item.get("command_kwargs", {})

            def invoke(fn=command, args=cmd_args, kwargs=cmd_kwargs):
                fn(*args, **kwargs)

            # Shortcut(s)
            accel_for_menu = ""
            sc = item.get("shortcut")
            shortcuts = sc if isinstance(sc, (list, tuple)) else ([sc] if sc else [])
            seen_bindings = set()

            for idx, s in enumerate(shortcuts):
                accel_label, bind_seq = _resolve_shortcut(s, keycfg)
                if idx == 0:
                    accel_for_menu = accel_label
                if not bind_seq:
                    continue

                # Collect variants to be robust to Caps Lock / Shift letter case
                variants = {bind_seq}
                try:
                    # Extract and edit only the final keysym
                    inner = bind_seq[1:-1]              # strip < >
                    parts = inner.split("-")            # e.g. ["Command", "Shift", "s"]
                    key = parts[-1]

                    if len(key) == 1 and key.isalpha():
                        # lower-case variant
                        parts_lower = parts[:]
                        parts_lower[-1] = key.lower()
                        v_lower = "<" + "-".join(parts_lower) + ">"
                        variants.add(v_lower)

                        # upper-case variant
                        parts_upper = parts[:]
                        parts_upper[-1] = key.upper()
                        v_upper = "<" + "-".join(parts_upper) + ">"
                        variants.add(v_upper)
                except Exception:
                    pass

                for v in variants:
                    if v in seen_bindings:
                        continue
                    seen_bindings.add(v)
                    try:
                        root.unbind_all(v)
                    except Exception:
                        pass
                    # IMPORTANT: call the wrapper with args/kwargs
                    root.bind_all(v, lambda e, inv=invoke: (inv(), "break"))

            m.add_command(label=label, command=invoke, accelerator=accel_for_menu)

    return menubar

def show_about_dialog(app, root):
    mbox.showinfo(
        "About Hex Converter",
        "Hex Bytes ⇆ Integer/Text Converter\n"
        "Version 1.0.0\n"
        "© 2025 Wired Square"
    )

def show_shortcuts_dialog(app, root):
    """
    Show a popup with the list of shortcuts from MENU_SPEC.
    """
    keycfg = _platform_keycfg()
    lines = []
    for menu in MENU_SPEC:
        for item in menu.get("items", []):
            if item.get("type") == "separator":
                continue
            label = item["label"]
            shortcut = item.get("shortcut")
            if not shortcut:
                continue

            shortcuts = shortcut if isinstance(shortcut, (list, tuple)) else [shortcut]
            shortcut_labels = [
                _resolve_shortcut(s, keycfg)[0]
                for s in shortcuts
            ]
            lines.append(f"{label}: {', '.join(shortcut_labels)}")

    mbox.showinfo("Keyboard Shortcuts", "\n".join(lines), parent=root)
