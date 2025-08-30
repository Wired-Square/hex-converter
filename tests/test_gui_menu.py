# tests/test_gui_menu.py

import pytest
from hex_converter.gui_menu import _resolve_shortcut

# Fake platform keycfgs so tests are deterministic
MAC_CFG = {
    "MOD": "Command",     "MOD_LABEL": "Cmd",
    "CTRL": "Control",    "CTRL_LABEL": "Ctrl",
    "CMD": "Command",     "CMD_LABEL": "Cmd",
    "ALT": "Option",      "ALT_LABEL": "Opt",
    "SHIFT": "Shift",     "SHIFT_LABEL": "Shift",
}

WINLINUX_CFG = {
    "MOD": "Control",     "MOD_LABEL": "Ctrl",
    "CTRL": "Control",    "CTRL_LABEL": "Ctrl",
    "CMD": "Control",     "CMD_LABEL": "Ctrl",  # treated as Control
    "ALT": "Alt",         "ALT_LABEL": "Alt",
    "SHIFT": "Shift",     "SHIFT_LABEL": "Shift",
}


@pytest.mark.parametrize("shortcut,cfg,expected_label,expected_bind", [
    # Simple MOD+letter
    ("MOD+L", MAC_CFG,       "Cmd+L",     "<Command-l>"),
    ("MOD+L", WINLINUX_CFG,  "Ctrl+L",    "<Control-l>"),

    # Multiple modifiers (order should be Cmd/Ctrl, Alt, Shift, then key)
    ("MOD+SHIFT+S", MAC_CFG,      "Cmd+Shift+S",   "<Command-Shift-s>"),
    ("CTRL+ALT+SHIFT+X", MAC_CFG, "Ctrl+Opt+Shift+X", "<Control-Option-Shift-x>"),
    ("CMD+ALT+K", MAC_CFG,        "Cmd+Opt+K",     "<Command-Option-k>"),
    ("CTRL+ALT+K", WINLINUX_CFG,  "Ctrl+Alt+K",    "<Control-Alt-k>"),

    # Named keysyms
    ("MOD+ENTER", MAC_CFG,        "Cmd+Enter",     "<Command-Return>"),
    ("MOD+ESC", WINLINUX_CFG,     "Ctrl+Esc",      "<Control-Escape>"),
    ("SHIFT+F5", MAC_CFG,         "Shift+F5",      "<Shift-F5>"),
    ("ALT+TAB", WINLINUX_CFG,     "Alt+Tab",       "<Alt-Tab>"),

    # Punctuation/named symbols
    ("MOD+COMMA", MAC_CFG,        "Cmd+,",         "<Command-comma>"),
    ("CTRL+PERIOD", WINLINUX_CFG, "Ctrl+.",        "<Control-period>"),
    ("SHIFT+SLASH", MAC_CFG,      "Shift+/",       "<Shift-slash>"),

    # Fallback: unknown token treated as keysym name (title-cased for label, raw for bind)
    ("MOD+MYKEY", MAC_CFG,        "Cmd+Mykey",     "<Command-MYKEY>"),
])
def test_resolve_shortcut_variants(shortcut, cfg, expected_label, expected_bind):
    label, bind = _resolve_shortcut(shortcut, cfg)
    assert label == expected_label
    assert bind == expected_bind


def test_resolve_shortcut_letter_case_rules():
    # Letter keys: label upper, bind lower
    label, bind = _resolve_shortcut("CTRL+a", WINLINUX_CFG)
    assert label == "Ctrl+A"
    assert bind == "<Control-a>"

    label, bind = _resolve_shortcut("MOD+z", MAC_CFG)
    assert label == "Cmd+Z"
    assert bind == "<Command-z>"


def test_resolve_shortcut_modifiers_only():
    # Degenerate but should not crash; returns just modifiers
    label, bind = _resolve_shortcut("CTRL+SHIFT", WINLINUX_CFG)
    assert label == "Ctrl+Shift"
    assert bind == "<Control-Shift>"


@pytest.mark.parametrize("shortcut,cfg", [
    ("SPACE", MAC_CFG),
    ("TAB", WINLINUX_CFG),
    ("BACKSPACE", MAC_CFG),
    ("DELETE", WINLINUX_CFG),
    ("UP", MAC_CFG),
    ("DOWN", WINLINUX_CFG),
    ("LEFT", MAC_CFG),
    ("RIGHT", WINLINUX_CFG),
])
def test_resolve_shortcut_navigation_named_keys(shortcut, cfg):
    # Just ensure it returns something sensible and well-formed
    label, bind = _resolve_shortcut(shortcut, cfg)
    assert label  # non-empty
    assert bind.startswith("<") and bind.endswith(">")
