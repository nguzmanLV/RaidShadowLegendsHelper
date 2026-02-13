import sys
import os
import time

# ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_manager import BotManager
from modules.campaign import campaign_loop


def main():
    mgr = BotManager()

    def gui_log(msg: str):
        print('[GUI_LOG]', msg)

    name = 'campaign'
    mgr.register_module(name, campaign_loop, log_func=gui_log)

    print('[exercise] starting 1st run')
    mgr.start_module(name)
    time.sleep(1.2)
    print('[exercise] stopping 1st run')
    mgr.stop_module(name)
    time.sleep(0.4)

    print('[exercise] starting 2nd run')
    mgr.start_module(name)
    time.sleep(1.2)
    print('[exercise] stopping 2nd run')
    mgr.stop_module(name)

    print('[exercise] finished')


if __name__ == '__main__':
    main()
