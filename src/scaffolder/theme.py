"""Shared brand colours and optional styling for interactive terminal sessions."""
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TextIO, TypeVar

CREAM = "#F0E8D0"
GOLD = "#B09050"
RED = "#A02838"
BURGUNDY = "#6A1828"
INK = "#200808"

_stream: ContextVar[TextIO | None] = ContextVar("theme_stream", default=None)
_P = ParamSpec("_P")
_R = TypeVar("_R")


def _colour(value: str, background: bool = False) -> str:
    channels = ";".join(str(int(value[i:i + 2], 16)) for i in (1, 3, 5))
    return f"\033[{48 if background else 38};2;{channels}m"


_BASE = _colour(CREAM) + _colour(INK, background=True)
_ROLES = {
    "heading": _colour(GOLD) + _colour(INK, background=True),
    "panel": _colour(CREAM) + _colour(BURGUNDY, background=True),
    "action": _colour(CREAM) + _colour(RED, background=True),
}


def _enable_terminal() -> Callable[[], None] | None:
    """Enable Windows virtual-terminal output, restoring its previous mode later."""
    if os.name != "nt":
        return lambda: None
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.GetStdHandle.argtypes = [wintypes.DWORD]
    api.GetStdHandle.restype = wintypes.HANDLE
    api.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    api.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = api.GetStdHandle(wintypes.DWORD(-11))
    mode = wintypes.DWORD()
    if not api.GetConsoleMode(handle, ctypes.byref(mode)):
        return None
    if not api.SetConsoleMode(handle, mode.value | 0x0004):
        return None
    return lambda: api.SetConsoleMode(handle, mode.value)


@contextmanager
def terminal_theme() -> Iterator[None]:
    """Style supported terminals only; preserve plain logs and nested sessions."""
    out = sys.stdout
    if (_stream.get() is out or not out.isatty() or "NO_COLOR" in os.environ
            or os.environ.get("TERM") == "dumb"):
        yield
        return
    restore = _enable_terminal()
    if restore is None:
        yield
        return
    token = _stream.set(out)
    try:
        out.write(_BASE)
        out.flush()
        yield
    finally:
        try:
            out.write("\033[0m")
            out.flush()
        finally:
            _stream.reset(token)
            restore()


def paint(text: str, role: str = "heading", out: TextIO | None = None) -> str:
    """Colour a UI label only when its destination is the active themed stream."""
    destination = sys.stdout if out is None else out
    if _stream.get() is not destination:
        return text
    return _ROLES[role] + text + _BASE


def themed(function: Callable[_P, _R]) -> Callable[_P, _R]:
    """Run a public menu or CLI entry point in a safely restored theme session."""
    @wraps(function)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with terminal_theme():
            return function(*args, **kwargs)
    return wrapped
