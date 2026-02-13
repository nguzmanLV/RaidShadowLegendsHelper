"""Bot manager: register/start/stop module worker threads."""
from threading import Thread, Event
from typing import Callable, Dict, Optional
import inspect
import time


class BotManager:
    def __init__(self) -> None:
        # store per-module info: { name: { target, log_func, thread, stop_event } }
        self._modules: Dict[str, Dict] = {}
        # track last completion timestamp per module for cooldown checking
        self._last_completed: Dict[str, float] = {}
        # cooldown durations per module (in seconds)
        self._cooldowns: Dict[str, float] = {
            'arena': 15 * 60,  # 15 minutes for arena
            'tag_arena': 24 * 3600,  # 24 hours for tag arena
        }

    def register_module(self, name: str, target: Callable, log_func: Optional[Callable[[str], None]] = None) -> None:
        """Register a module target without creating the thread yet.

        The `target` may accept either one argument `(stop_event)` or two `(stop_event, log_func)`.
        """
        if name in self._modules:
            raise ValueError(f"Module '{name}' already registered")
        self._modules[name] = {
            'target': target,
            'log_func': log_func,
            'thread': None,
            'stop_event': None,
        }

    def start_module(self, name: str) -> None:
        info = self._modules[name]
        thread = info.get('thread')
        # if already running, nothing to do
        if thread is not None and thread.is_alive():
            return

        # create fresh stop event and thread wrapper
        stop_event = Event()
        target = info['target']
        log_func = info.get('log_func')

        sig = inspect.signature(target)
        params = len(sig.parameters)

        def _runner():
            try:
                if params >= 2:
                    target(stop_event, log_func)
                else:
                    target(stop_event)
            except Exception as exc:
                if callable(log_func):
                    try:
                        log_func(f"[module:{name}] exception: {exc}")
                    except Exception:
                        pass

        new_thread = Thread(target=_runner, name=name, daemon=True)
        info['thread'] = new_thread
        info['stop_event'] = stop_event
        new_thread.start()

    def stop_module(self, name: str, timeout: float = 5.0) -> None:
        info = self._modules.get(name)
        if not info:
            return
        thread = info.get('thread')
        stop_event = info.get('stop_event')
        if stop_event is not None:
            stop_event.set()
        if thread is not None:
            thread.join(timeout=timeout)
        # clear thread reference so it can be started again later
        info['thread'] = None
        info['stop_event'] = None

    def start_all(self) -> None:
        for name in list(self._modules.keys()):
            self.start_module(name)

    def stop_all(self) -> None:
        for name in list(self._modules.keys()):
            self.stop_module(name)

    def is_registered(self, name: str) -> bool:
        return name in self._modules

    def is_running(self, name: str) -> bool:
        info = self._modules.get(name)
        if not info:
            return False
        thread = info.get('thread')
        return thread is not None and thread.is_alive()

    def mark_completed(self, name: str) -> None:
        """Mark a module as completed; stores current timestamp for cooldown tracking."""
        self._last_completed[name] = time.time()

    def get_cooldown_remaining(self, name: str) -> float:
        """Return seconds remaining until module can run again, or 0.0 if ready.
        
        Returns 0.0 if module has no cooldown or cooldown has elapsed.
        Returns positive value (seconds) if module is still on cooldown.
        """
        cooldown_duration = self._cooldowns.get(name, 0)
        if cooldown_duration <= 0:
            return 0.0
        
        last_time = self._last_completed.get(name)
        if last_time is None:
            return 0.0  # never run, so not on cooldown
        
        elapsed = time.time() - last_time
        remaining = cooldown_duration - elapsed
        return max(0.0, remaining)


if __name__ == "__main__":
    # simple smoke test
    from modules.campaign import campaign_loop

    mgr = BotManager()
    mgr.register_module("campaign", campaign_loop)
    mgr.start_all()
    try:
        time.sleep(1)
    finally:
        mgr.stop_all()
