"""Screen utilities: lightweight wrappers for screenshots and template locate.

These are minimal stubs that prefer `pyautogui` and optionally `cv2` if installed.
Replace with robust OpenCV template-matching logic as needed.
"""
from typing import Optional, Tuple
import os
try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None


def screenshot() -> Optional[object]:
    """Return a screenshot object (pyautogui Image) or None if unavailable."""
    if pyautogui is None:
        return None
    return pyautogui.screenshot()


def locate_on_screen(template_path: str, threshold: float = 0.8) -> Optional[Tuple[int, int]]:
    """Locate `template_path` on screen. Returns (x,y) center or None.

    This is a placeholder: if `cv2` is installed it will attempt simple template matching.
    """
    if pyautogui is None:
        return None
    if cv2 is None:
        # fallback to pyautogui.locateCenterOnScreen if available
        try:
            loc = pyautogui.locateCenterOnScreen(template_path)
            return (loc.x, loc.y) if loc else None
        except Exception:
            return None

    # simple OpenCV-based locate
    img = np.array(pyautogui.screenshot())
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        return None
    res = cv2.matchTemplate(img_gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        th, tw = tpl.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (int(cx), int(cy))
    return None


def locate_all_on_screen(template_path: str, threshold: float = 0.8, debug: bool = False) -> list:
    """Return list of center (x,y) matches for template_path on the screen.

    Uses OpenCV when available to perform template matching and return all
    matches above `threshold`. Falls back to `pyautogui.locateAllOnScreen`.
    Deduplicates nearby matches and returns only the strongest candidates.
    
    Args:
        template_path: path to template image
        threshold: match confidence threshold (0.0-1.0)
        debug: if True, print debug info about matches
    """
    results = []
    if pyautogui is None:
        return results

    if cv2 is None:
        # fallback to pyautogui locateAllOnScreen
        try:
            boxes = list(pyautogui.locateAllOnScreen(template_path))
            for b in boxes:
                cx = b.left + b.width // 2
                cy = b.top + b.height // 2
                results.append((int(cx), int(cy)))
            if debug and results:
                print(f"[locate_all] pyautogui found {len(results)} matches: {results}")
            return results
        except Exception as e:
            if debug:
                print(f"[locate_all] pyautogui error: {e}")
            return results

    try:
        img = np.array(pyautogui.screenshot())
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            if debug:
                print(f"[locate_all] template not found: {template_path}")
            return results
        res = cv2.matchTemplate(img_gray, tpl, cv2.TM_CCOEFF_NORMED)
        locs = list(zip(*np.where(res >= threshold)[::-1]))
        th, tw = tpl.shape[:2]
        
        if debug:
            print(f"[locate_all] template: {template_path}, threshold={threshold}, raw_matches={len(locs)}")
        
        # cluster nearby matches using stricter 30-pixel radius to avoid false positives
        clusters = {}
        for pt in locs:
            # get match confidence for this location
            conf = res[pt[1], pt[0]]
            cluster_key = (pt[0] // 30, pt[1] // 30)
            if cluster_key not in clusters or conf > clusters[cluster_key][2]:
                clusters[cluster_key] = (pt[0], pt[1], conf)
        
        # convert cluster centers to actual match centers (add template half-size)
        for (x, y, conf) in clusters.values():
            cx = int(x + tw // 2)
            cy = int(y + th // 2)
            results.append((cx, cy))
        
        # sort by confidence descending and keep top 5
        if len(results) > 5:
            results = results[:5]
        
        if debug:
            print(f"[locate_all] after clustering: {results}")
        return results
    except Exception as e:
        if debug:
            print(f"[locate_all] cv2 error: {e}")
        return results


def save_debug_screenshot(output_path: str, template_path: str = None, matches: list = None) -> None:
    """Save a screenshot with template matches marked for visual debugging.
    
    Args:
        output_path: where to save the marked-up screenshot
        template_path: path to template image (for overlay match regions)
        matches: list of (x, y) coordinates to mark as red dots
    """
    if cv2 is None or pyautogui is None:
        return
    
    try:
        img = np.array(pyautogui.screenshot())
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # mark matches as red circles
        if matches:
            for (x, y) in matches:
                cv2.circle(img_bgr, (int(x), int(y)), 15, (0, 0, 255), 2)  # red circle
                cv2.putText(img_bgr, f"({int(x)},{int(y)})", (int(x)-30, int(y)-20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # optionally overlay template match regions if template provided
        if template_path and os.path.exists(template_path):
            try:
                tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if tpl is not None:
                    th, tw = tpl.shape[:2]
                    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                    res = cv2.matchTemplate(img_gray, tpl, cv2.TM_CCOEFF_NORMED)
                    # mark top match region with green rectangle
                    _, max_conf, _, max_loc = cv2.minMaxLoc(res)
                    x, y = max_loc
                    cv2.rectangle(img_bgr, (x, y), (x + tw, y + th), (0, 255, 0), 2)  # green rect
            except Exception:
                pass
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
        cv2.imwrite(output_path, img_bgr)
    except Exception:
        pass