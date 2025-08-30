# hex_converter/__about__.py

APP_NAME        = "Hex Converter"
APP_TITLE       = "Hex Bytes ⇆ Integer/Text Converter"   # window title / long name
BUNDLE_ID       = "com.wiredsquare.hexconverter"
AUTHOR          = "Wired Square"
COPYRIGHT_YEAR  = "2025"
COPYRIGHT       = f"© {COPYRIGHT_YEAR} {AUTHOR}"
HOMEPAGE        = "https://github.com/Wired-Square/hex-converter"


__version__ = "0.0.2.dev1"

__all__ = [
    "__version__",
    "APP_NAME", "APP_TITLE", "BUNDLE_ID",
    "AUTHOR", "COPYRIGHT_YEAR", "COPYRIGHT", "HOMEPAGE",
]

def about_text() -> str:
    return (
        f"{APP_TITLE}\n"
        f"Version {__version__}\n"
        f"{COPYRIGHT}\n"
        f"{HOMEPAGE}"
    )