"""Input controls wrappers (mouse/keyboard) using pyautogui."""
try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None


def click(x: int, y: int, clicks: int = 1, interval: float = 0.0) -> None:
    if pyautogui is None:
        return
    pyautogui.click(x=x, y=y, clicks=clicks, interval=interval)


def move_to(x: int, y: int, duration: float = 0.0) -> None:
    if pyautogui is None:
        return
    pyautogui.moveTo(x, y, duration=duration)


def press(key: str) -> None:
    if pyautogui is None:
        return
    pyautogui.press(key)


def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.4) -> None:
    """Perform a left-click drag from (from_x, from_y) to (to_x, to_y)."""
    if pyautogui is None:
        return
    try:
        pyautogui.moveTo(from_x, from_y)
        pyautogui.dragTo(to_x, to_y, duration=duration, button='left')
    except Exception:
        try:
            pyautogui.mouseDown(from_x, from_y)
            pyautogui.moveTo(to_x, to_y, duration=duration)
            pyautogui.mouseUp()
        except Exception:
            pass
