import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_manager import BotManager
from modules.campaign import campaign_loop
import time


def main():
    mgr = BotManager()

    def gui_log(msg: str) -> None:
        print("[GUI_LOG]", msg)

    mgr.register_module("campaign", campaign_loop, log_func=gui_log)
    mgr.start_module("campaign")
    try:
        time.sleep(3)
    finally:
        mgr.stop_module("campaign")
        print("[exercise] stopped")


if __name__ == "__main__":
    main()
