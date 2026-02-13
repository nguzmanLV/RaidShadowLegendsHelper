"""Window utilities for Windows: locate and move/resize the game window.

This module uses `win32gui`/`win32con` when available to find a window by title
or by HWND resolved from a screen point (from image matching). It retries a few
times to improve robustness and logs progress via the provided `log` callable.
"""
from typing import Optional
import platform
import time
import ctypes
from ctypes import wintypes

from .screen import locate_on_screen

WINDOW_TARGET_WIDTH = 1280
WINDOW_TARGET_HEIGHT = 720


def _is_windows() -> bool:
    return platform.system().lower() == 'windows'


def _window_set_pos_win32(hwnd, x: int, y: int, w: int, h: int) -> bool:
    try:
        import win32con
        import win32gui
        # Use HWND_TOPMOST to keep the window on top
        flags = win32con.SWP_SHOWWINDOW
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, int(x), int(y), int(w), int(h), flags)
        return True
    except Exception:
        # Fallback to ctypes SetWindowPos
        try:
            # HWND_TOPMOST = -1, SWP_SHOWWINDOW = 0x0040
            HWND_TOPMOST = -1
            SWP_SHOWWINDOW = 0x0040
            return bool(ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, int(x), int(y), int(w), int(h), SWP_SHOWWINDOW))
        except Exception:
            return False


def _find_hwnd_by_title(title_substr: str):
    try:
        import win32gui
    except Exception:
        return None

    result = None

    def _cb(hwnd, _):
        nonlocal result
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            text = win32gui.GetWindowText(hwnd) or ''
        except Exception:
            text = ''
        if title_substr.lower() in text.lower():
            result = hwnd
            return False  # stop enumeration
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        return None
    return result


def _hwnd_from_point(x: int, y: int):
    try:
        pt = wintypes.POINT(int(x), int(y))
        return ctypes.windll.user32.WindowFromPoint(pt)
    except Exception:
        return None


def ensure_game_window(log: Optional[callable] = None,
                       title: str = 'Raid: Shadow Legends',
                       template_path: Optional[str] = None,
                       target_w: int = WINDOW_TARGET_WIDTH,
                       target_h: int = WINDOW_TARGET_HEIGHT,
                       retries: int = 5,
                       retry_delay: float = 0.8) -> bool:
    """Ensure the game window is at (0,0) sized to target.

    Tries multiple strategies with retries and logs progress.
    """
    if callable(log):
        try:
            log("[init] starting window initiation")
        except Exception:
            pass

    if not _is_windows():
        if callable(log):
            try:
                log("[init] non-Windows OS; window positioning not supported")
            except Exception:
                pass
        return False

    for attempt in range(1, retries + 1):
        if callable(log):
            try:
                log(f"[init] attempt {attempt}/{retries}")
            except Exception:
                pass

        # Strategy 1: find by window title substring (fast and reliable if correct)
        try:
            hwnd = _find_hwnd_by_title(title)
            if hwnd:
                ok = _window_set_pos_win32(hwnd, 0, 0, target_w, target_h)
                if callable(log):
                    try:
                        log(f"[init] title match -> moved={ok}")
                    except Exception:
                        pass
                if ok:
                    if callable(log):
                        try:
                            log("[init] initiation complete")
                        except Exception:
                            pass
                    return True
        except Exception as exc:
            if callable(log):
                try:
                    log(f"[init] title-matching error: {exc}")
                except Exception:
                    pass

        # Strategy 2: image/template matching to locate an in-window point
        if template_path:
            try:
                loc = locate_on_screen(template_path)
                if loc:
                    x, y = loc
                    hwnd = _hwnd_from_point(int(x), int(y))
                    if hwnd:
                        ok = _window_set_pos_win32(hwnd, 0, 0, target_w, target_h)
                        if callable(log):
                            try:
                                log(f"[init] image match -> moved={ok}")
                            except Exception:
                                pass
                        if ok:
                            if callable(log):
                                try:
                                    log("[init] initiation complete")
                                except Exception:
                                    pass
                            return True
            except Exception as exc:
                if callable(log):
                    try:
                        log(f"[init] image-matching error: {exc}")
                    except Exception:
                        pass

        # Strategy 3: try the center point (useful if game is active fullscreen/windowed)
        try:
            import pyautogui
            sw, sh = pyautogui.size()
            cx, cy = sw // 2, sh // 2
            hwnd = _hwnd_from_point(cx, cy)
            if hwnd:
                ok = _window_set_pos_win32(hwnd, 0, 0, target_w, target_h)
                if callable(log):
                    try:
                        log(f"[init] center-point -> moved={ok}")
                    except Exception:
                        pass
                if ok:
                    if callable(log):
                        try:
                            log("[init] initiation complete")
                        except Exception:
                            pass
                    return True
        except Exception:
            pass

        # Wait before retrying
        time.sleep(retry_delay)

    if callable(log):
        try:
            log("[init] failed to position the game window after retries")
        except Exception:
            pass
    # As an aid to debugging, enumerate visible windows and log a few titles
    try:
        import win32gui
        titles = []

        def _collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    txt = win32gui.GetWindowText(hwnd)
                except Exception:
                    txt = ''
                if txt:
                    titles.append(txt)
            return True

        win32gui.EnumWindows(_collect, None)
        sample = titles[:30]
        if callable(log):
            try:
                log(f"[init] visible windows sample: {sample}")
            except Exception:
                pass
    except Exception:
        pass
    return False
