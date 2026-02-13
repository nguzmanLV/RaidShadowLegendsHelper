"""Campaign module stub - loop that can be run in a thread."""
from threading import Event
import time


def campaign_loop(stop_event: Event, log=None) -> None:
    """Example campaign loop. Accepts optional `log` callable to send GUI messages."""
    while not stop_event.is_set():
        msg = "[campaign] tick"
        if callable(log):
            try:
                log(msg)
            except Exception:
                print(msg)
        else:
            print(msg)
        time.sleep(0.5)


if __name__ == "__main__":
    e = Event()
    try:
        campaign_loop(e)
    except KeyboardInterrupt:
        e.set()
