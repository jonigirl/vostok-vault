import ctypes
import sys
from pathlib import Path

FONT_ATKINSON = "Atkinson Hyperlegible"
FONT_OPENDYSLEXIC = "OpenDyslexic"
FONT_FALLBACK = "Segoe UI"

_app_font: str = FONT_FALLBACK


def _fonts_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / "fonts"
    return Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"


def _load_font_windows(ttf_path: Path) -> bool:
    if sys.platform != "win32":
        return False
    try:
        added = ctypes.windll.gdi32.AddFontResourceW(str(ttf_path))
        if added > 0:
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001D, 0, 0, 0, 1000, None
            )
            return True
    except Exception:
        return False
    return False


_loaded_font_paths: list[Path] = []


def _load_bundled_fonts() -> None:
    fonts_dir = _fonts_dir()
    for name in ("AtkinsonHyperlegible-Regular.ttf", "AtkinsonHyperlegible-Bold.ttf"):
        f = fonts_dir / name
        if f.exists() and _load_font_windows(f):
            _loaded_font_paths.append(f)


def unload_bundled_fonts() -> None:
    if sys.platform != "win32" or not _loaded_font_paths:
        return
    try:
        for path in _loaded_font_paths:
            ctypes.windll.gdi32.RemoveFontResourceW(str(path))
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001D, 0, 0, 0, 1000, None)
    except Exception:
        pass


def init_font(preferred: str | None = None) -> str:
    global _app_font
    _load_bundled_fonts()
    try:
        import tkinter as tk
        import tkinter.font as tkfont

        _tmp = tk.Tk()
        _tmp.withdraw()
        families = tkfont.families()
        _tmp.destroy()
    except Exception:
        families = ()

    if preferred == FONT_OPENDYSLEXIC and FONT_OPENDYSLEXIC in families:
        _app_font = FONT_OPENDYSLEXIC
    elif FONT_ATKINSON in families:
        _app_font = FONT_ATKINSON
    else:
        _app_font = FONT_FALLBACK
    return _app_font


def get_font() -> str:
    return _app_font
