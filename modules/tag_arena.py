"""Tag Arena module: similar to arena.py but for tag team battles.

Follows steps:
- Ensure homescreen
- Click Battle button
- Click Arena button
- Click Tag Team Arena
- Loop: find TagBattleButton, click, select champions, battle, return
- Max 10 battles, then 24hr cooldown
"""
from threading import Event
import time
import os
from typing import Optional, Tuple, List

from utils.screen import locate_on_screen
from utils.controls import click, press
from utils.popup import close_popup_if_present


def _find_template(name: str) -> Optional[str]:
    """Search repo for template file."""
    root = os.path.abspath(os.path.dirname(__file__))
    for dirpath, dirnames, filenames in os.walk(root):
        if name in filenames:
            return os.path.join(dirpath, name)
    # also check repo root
    repo_root = os.path.abspath(os.path.join(root, '..'))
    for dirpath, dirnames, filenames in os.walk(repo_root):
        if name in filenames:
            return os.path.join(dirpath, name)
    return None


def _log_fn(log, message: str) -> None:
    """Send log to callback or print."""
    if callable(log):
        try:
            log(f"[tag_arena] {message}")
        except Exception:
            pass
    else:
        print(f"[tag_arena] {message}")


def tag_arena_loop(stop_event: Event, log=None) -> None:
    """Run tag arena battles in sequence, max 10 battles per session.
    
    After 10 battles, indicates no more tokens (24hr cooldown).
    """
    # templates used
    homescreen_tpl = 'homescreenCheck.png'
    back_tpl = 'BackButton.png'
    battle_tpl = 'BattleButton.png'
    arena_btn_tpl = 'ArenaButton.png'
    tag_arena_tpl = 'TagTeamArena.png'  # button to enter tag arena
    tag_battle_tpl = 'TagBattleButton.png'  # the opponent team button
    tag_start_tpl = 'TagStartButton.png'  # start battle button
    tag_battle_over_tpl = 'Tagbattleoverbutton.png'  # battle over button
    tag_return_tpl = 'TagReturnButton.png'  # return button
    close_tpl = 'CloseAd.png'

    def ensure_homescreen():
        _log_fn(log, 'ensuring homescreen')
        while not stop_event.is_set():
            loc = _find_template(homescreen_tpl)
            if loc and locate_on_screen(loc):
                _log_fn(log, 'homescreen detected')
                return True
            # try Back button
            back = _find_template(back_tpl)
            if back and locate_on_screen(back):
                _log_fn(log, 'BackButton found, clicking')
                click(*locate_on_screen(back))
                time.sleep(0.8)
                continue
            # try closing popup
            closep = _find_template(close_tpl)
            if closep:
                closed = close_popup_if_present(log=log, templates=[closep])
                if closed:
                    time.sleep(0.6)
                    continue
            # nothing found, wait and retry
            _log_fn(log, 'homescreen not found, retrying...')
            time.sleep(1.0)
        return False

    def find_and_click_with_popup_retry(template_name: str, max_cycles: int = 3) -> Optional[Tuple[int, int]]:
        """Try to find and click a template, closing popup if necessary."""
        tpl_path = _find_template(template_name)
        if not tpl_path:
            _log_fn(log, f"template not found: {template_name}")
            return None
        for cycle in range(max_cycles):
            loc = locate_on_screen(tpl_path)
            if loc:
                try:
                    click(*loc)
                    _log_fn(log, f"clicked {template_name}")
                    return (int(loc[0]), int(loc[1]))
                except Exception as e:
                    _log_fn(log, f"click failed: {e}")
            # try close popup then retry
            closep = _find_template(close_tpl)
            if closep:
                closed = close_popup_if_present(log=log, templates=[closep])
                if closed:
                    time.sleep(0.6)
                    continue
            time.sleep(0.8)
        _log_fn(log, f"failed to find {template_name} after retries")
        return None

    # main routine - run one complete session (10 battles max), then exit
    # ensure homescreen
    if not ensure_homescreen():
        _log_fn(log, 'stopping: could not ensure homescreen')
        return

    # find and click Battle button
    if not find_and_click_with_popup_retry(battle_tpl, max_cycles=5):
        _log_fn(log, 'BattleButton not found after retries; exiting')
        return

    time.sleep(0.8)
    # click Arena button
    if not find_and_click_with_popup_retry(arena_btn_tpl, max_cycles=5):
        _log_fn(log, 'ArenaButton not found; exiting')
        return

    time.sleep(0.8)
    # click Tag Team Arena
    if not find_and_click_with_popup_retry(tag_arena_tpl, max_cycles=5):
        _log_fn(log, 'TagTeamArena button not found; exiting')
        return

    time.sleep(0.8)
    # Now repeatedly perform up to 10 battles
    battles_done = 0
    last_y = None
    used_battle_positions: List[Tuple[int, int]] = []
    
    while not stop_event.is_set() and battles_done < 10:
            # find tag battle button candidates
            tbt = _find_template(tag_battle_tpl)
            if not tbt:
                _log_fn(log, 'TagBattleButton template missing')
                break
            
            # use locate_all_on_screen when available
            try:
                from utils.screen import locate_all_on_screen
            except Exception:
                locate_all_on_screen = None

            candidates = []
            if locate_all_on_screen:
                try:
                    candidates = locate_all_on_screen(tbt, debug=True)
                    _log_fn(log, f'locate_all_on_screen found {len(candidates)} candidates: {candidates}')
                except Exception as e:
                    _log_fn(log, f'locate_all_on_screen error: {e}')
                    candidates = []
            
            # fallback to single locate
            if not candidates:
                loc = locate_on_screen(tbt)
                if loc:
                    _log_fn(log, f'fallback locate_on_screen found: {loc}')
                    candidates = [(int(loc[0]), int(loc[1]))]

            chosen = None
            if candidates:
                _log_fn(log, f'evaluating {len(candidates)} candidates, used_positions={used_battle_positions}')
                for c in candidates:
                    too_close = any(abs(c[0] - u[0]) < 30 and abs(c[1] - u[1]) < 30 for u in used_battle_positions)
                    _log_fn(log, f'candidate {c} too_close={too_close}')
                    if not too_close:
                        chosen = c
                        _log_fn(log, f'selected candidate: {chosen}')
                        break

            if not chosen:
                _log_fn(log, 'no fresh TagBattleButton found; trying popup/refresh/scroll fallback')
                # try closing popup
                closep = _find_template(close_tpl)
                if closep:
                    closed = close_popup_if_present(log=log, templates=[closep])
                    if closed:
                        time.sleep(0.6)
                        if locate_all_on_screen:
                            candidates = locate_all_on_screen(tbt)
                        else:
                            loc = locate_on_screen(tbt)
                            candidates = [(int(loc[0]), int(loc[1]))] if loc else []
                        for c in candidates:
                            if not any(abs(c[0] - u[0]) < 30 and abs(c[1] - u[1]) < 30 for u in used_battle_positions):
                                chosen = c
                                break
                # try refresh button
                if not chosen:
                    refresh_tpl = _find_template('RefreshButton.png')
                    if refresh_tpl:
                        rloc = locate_on_screen(refresh_tpl)
                        if rloc:
                            try:
                                click(int(rloc[0]), int(rloc[1]))
                                _log_fn(log, 'clicked RefreshButton; clearing used positions')
                                used_battle_positions.clear()
                                time.sleep(1.0)
                                if locate_all_on_screen:
                                    candidates = locate_all_on_screen(tbt)
                                else:
                                    loc = locate_on_screen(tbt)
                                    candidates = [(int(loc[0]), int(loc[1]))] if loc else []
                                if candidates:
                                    chosen = candidates[0]
                            except Exception as e:
                                _log_fn(log, f'Refresh click failed: {e}')
                # if still not chosen after refresh, try scroll down
                if not chosen:
                    _log_fn(log, 'scrolling down to search for more teams')
                    try:
                        press('pagedown')
                    except Exception:
                        try:
                            from utils.controls import drag
                            drag(600, 900, 600, 450, duration=0.35)
                        except Exception:
                            pass
                    time.sleep(0.8)
                    used_battle_positions.clear()
                    if locate_all_on_screen:
                        try:
                            candidates = locate_all_on_screen(tbt)
                        except Exception:
                            candidates = []
                    else:
                        loc = locate_on_screen(tbt)
                        candidates = [(int(loc[0]), int(loc[1]))] if loc else []
                    if candidates:
                        chosen = candidates[0]
                        _log_fn(log, 'found candidates after scroll')
                # final drag fallback if refresh button doesn't exist and scroll didn't work
                if not chosen and not refresh_tpl:
                    # No explicit refresh button: attempt up to 4 upward drag gestures
                    _log_fn(log, 'RefreshButton not found; attempting up to 4 drag-up gestures to reveal new teams')
                    try:
                        from utils.controls import drag
                    except Exception:
                        drag = None
                    for di in range(4):
                        if stop_event.is_set():
                            break
                        _log_fn(log, f'attempting drag-up {di+1}/4')
                        try:
                            if drag:
                                drag(600, 900, 600, 450, duration=0.35)
                            else:
                                try:
                                    press('pagedown')
                                except Exception:
                                    pass
                            time.sleep(0.8)
                        except Exception as e:
                            _log_fn(log, f'drag attempt failed: {e}')
                        # after each drag, clear used positions and re-check
                        used_battle_positions.clear()
                        if locate_all_on_screen:
                            try:
                                candidates = locate_all_on_screen(tbt)
                            except Exception:
                                candidates = []
                        else:
                            loc = locate_on_screen(tbt)
                            candidates = [(int(loc[0]), int(loc[1]))] if loc else []
                        if candidates:
                            chosen = candidates[0]
                            _log_fn(log, f'found candidates after drag {di+1}')
                            break

            if not chosen:
                _log_fn(log, 'TagBattleButton still not found; no more battles available')
                break

            bx, by = int(chosen[0]), int(chosen[1])
            _log_fn(log, f'raw chosen center: ({bx}, {by})')
            # Click directly at detected center
            click_x = bx
            click_y = by
            _log_fn(log, f'clicking TagBattleButton at screen position ({click_x}, {click_y})')
            # Save debug screenshot
            try:
                from utils.screen import save_debug_screenshot
                debug_path = os.path.join(os.path.dirname(__file__), '..', 'debug_tag_arena_battle.png')
                save_debug_screenshot(debug_path, template_path=tbt, matches=[(click_x, click_y)])
            except Exception:
                pass
            try:
                click(click_x, click_y)
                _log_fn(log, f'click executed at ({click_x}, {click_y})')
            except Exception as e:
                _log_fn(log, f'click failed: {e}'); click(bx, by)

            # record this battle position to avoid re-clicking
            used_battle_positions.append((bx, by))
            if len(used_battle_positions) > 3:
                used_battle_positions = used_battle_positions[-3:]
            last_y = by

            time.sleep(0.8)

            # now on champion select: click tag_start
            if not find_and_click_with_popup_retry(tag_start_tpl, max_cycles=6):
                _log_fn(log, 'tag start button not found; aborting battle attempt')
                break

            # wait for battle to finish: poll every 30s for battle over button
            elapsed_wait = 0
            while not stop_event.is_set():
                time.sleep(30)
                elapsed_wait += 30
                over_tpl = _find_template(tag_battle_over_tpl)
                if over_tpl and locate_on_screen(over_tpl):
                    _log_fn(log, f'battle over detected after {elapsed_wait}s')
                    click(*locate_on_screen(over_tpl))
                    time.sleep(1.0)
                    break
                else:
                    _log_fn(log, f'battle still running (waited {elapsed_wait}s)')

            # click return button
            if not find_and_click_with_popup_retry(tag_return_tpl, max_cycles=6):
                _log_fn(log, 'TagReturnButton not found; attempting to continue')
            else:
                _log_fn(log, 'returned from battle stats')

            battles_done += 1
            _log_fn(log, f'battles_done={battles_done}')
            time.sleep(1.0)

    # After 10 battles, indicate session complete (24hr cooldown applies)
    _log_fn(log, 'tag arena finished; no more tokens available (24hr cooldown)')

    # return to homescreen
    _log_fn(log, 'returning to homescreen')
    while not stop_event.is_set():
        homes = _find_template(homescreen_tpl)
        if homes and locate_on_screen(homes):
            _log_fn(log, 'homescreen reached')
            break
        back = _find_template(back_tpl)
        if back and locate_on_screen(back):
            click(*locate_on_screen(back))
            time.sleep(0.6)
            continue
        # try closing popup
        closep = _find_template(close_tpl)
        if closep:
            close_popup_if_present(log=log, templates=[closep])
        time.sleep(1.0)

    time.sleep(1.0)


if __name__ == "__main__":
    tag_arena_loop(Event())
