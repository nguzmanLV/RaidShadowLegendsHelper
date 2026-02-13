"""Popup helpers: detect common in-game popups and click their close (X) button.

Strategy:
- Prefer image/template matching of the close button (user provides a PNG).
- If multiple templates are provided, try each until one matches.
- On match, click the center of the matched region (with a small offset if needed).
- Return True if a popup was detected and closed, False otherwise.
"""
from typing import List, Optional
import time

from .screen import locate_on_screen
from .controls import click


def close_popup_if_present(log: Optional[callable] = None,
                           templates: Optional[List[str]] = None,
                           threshold: float = 0.8,
                           max_attempts: int = 3,
                           pause: float = 0.3) -> bool:
    """Try to find and click a popup close button using provided templates.

    - `templates`: list of file paths to template images (close icons).
    - `threshold`: matching threshold (used by locate_on_screen when OpenCV is available).
    - Returns True if a click was performed, False otherwise.
    """
    if templates is None:
        return False

    if not templates:
        if callable(log):
            try:
                log("[popup] no templates provided")
            except Exception:
                pass
        return False

    for attempt in range(1, max_attempts + 1):
        if callable(log):
            try:
                log(f"[popup] attempt {attempt}/{max_attempts}")
            except Exception:
                pass

        for tpl in templates:
            if not tpl:
                continue
            try:
                import os
                exists = os.path.exists(tpl)
            except Exception:
                exists = False
            if callable(log):
                try:
                    log(f"[popup] checking template: {tpl} (exists={exists})")
                except Exception:
                    pass

            try:
                loc = locate_on_screen(tpl, threshold=threshold)
            except Exception as e:
                loc = None
                if callable(log):
                    try:
                        log(f"[popup] locate_on_screen error for {tpl}: {e}")
                    except Exception:
                        pass

            if loc:
                x, y = loc
                try:
                    click(int(x), int(y))
                    if callable(log):
                        try:
                            log(f"[popup] clicked template {tpl} at ({x},{y})")
                        except Exception:
                            pass
                    # small pause to allow UI to update
                    time.sleep(pause)
                    return True
                except Exception as exc:
                    if callable(log):
                        try:
                            log(f"[popup] click failed: {exc}")
                        except Exception:
                            pass
        # nothing found; short wait before next attempt
        time.sleep(pause)

    if callable(log):
        try:
            log("[popup] no popup detected by templates")
        except Exception:
            pass
    return False
