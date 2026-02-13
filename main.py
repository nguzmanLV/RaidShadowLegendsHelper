import FreeSimpleGUI as sg  # Changed from PySimpleGUI
import threading
import os
import time
from bot_manager import BotManager
from modules.campaign import campaign_loop
from modules.arena import arena_loop
from modules.tag_arena import tag_arena_loop
from utils.window import ensure_game_window
from utils.popup import close_popup_if_present

class BotThread(threading.Thread):
    def __init__(self, window, action, interval):
        super().__init__(daemon=True)
        self.window = window
        self.action = action
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        self._log(f"Bot started: action={self.action}, interval={self.interval}s")
        while not self._stop_event.is_set():
            self.perform_action()
            # Sleeping in small increments allows for a faster stop response
            for _ in range(max(1, int(self.interval * 10))):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)
        self._log("Bot stopped")

    def stop(self):
        self._stop_event.set()

    def perform_action(self):
        self._log(f"Performing action: {self.action}")
        # Placeholder for automation logic (e.g., PyAutoGUI or OpenCV)
        time.sleep(0.5)

    def _log(self, message):
        # Sends event to the GUI thread to safely update the window
        self.window.write_event_value('-THREAD_LOG-', message)


def main():
    # FreeSimpleGUI supports all the same themes as the original
    sg.theme('DarkBlue3')
    
    # Main and Settings tabs to keep template options out of primary view
    tab_main = [
        [sg.Text('Raid Shadow Legends Bot', font=('Any', 16))],
        [
            sg.Text('Action:'),
            sg.Listbox(values=['Farm Campaign', 'Arena', 'Tag Arena', 'Repeat Battles', 'Auto', 'Custom'], select_mode='multiple', size=(30,4), key='-ACTIONS-'),
            sg.Text('Interval (s):'),
            sg.Input('5', size=(6, 1), key='-INTERVAL-')
        ],
        [sg.Button('Start', key='-START-'), sg.Button('Stop', key='-STOP-', disabled=True), sg.Text('Runtime:'), sg.Text('00:00:00', key='-TIMER-'), sg.Button('Exit')]
    ]

    tab_settings = [
        [
            sg.Text('Window Title:'),
            sg.Input('Raid: Shadow Legends', size=(30, 1), key='-TITLE-')
        ],
        [
            sg.Text('Window Template (optional):'),
            sg.Input('', size=(40, 1), key='-TEMPLATE-'),
            sg.FileBrowse('Browse', file_types=(('PNG Images', '*.png'), ('All', '*.*')))
        ],
        [
            sg.Text('Close-Button Template (optional):'),
            sg.Input('', size=(40, 1), key='-TEMPLATE-CLOSE-'),
            sg.FileBrowse('Browse', file_types=(('PNG Images', '*.png'), ('All', '*.*')))
        ],
        [sg.Button('Test Close', key='-TEST-CLOSE-')],
        [sg.Text('Template Preview (Close-Button):')],
        [sg.Image(key='-TEMPLATE-THUMB-', size=(200, 150))]
    ]

    layout = [
        [sg.TabGroup([[sg.Tab('Main', tab_main), sg.Tab('Settings', tab_settings)]], key='-TABGROUP-')],
        [sg.Multiline(size=(80, 20), key='-LOG-', autoscroll=True, disabled=True, echo_stdout_stderr=False)]
    ]

    window = sg.Window('RSL Bot GUI', layout, finalize=True)
    bot = None
    manager = BotManager()
    current_module_name = None
    start_time = None
    running = False
    controller_ref = None

    # use a short timeout so we can update the runtime timer
    while True:
        event, values = window.read(timeout=200)
        
        if event in (sg.WINDOW_CLOSED, 'Exit'):
            if bot:
                bot.stop()
            if current_module_name:
                try:
                    manager.stop_module(current_module_name)
                except Exception:
                    pass
            manager.stop_all()
            break

        # update thumbnail preview when close template changes
        if event == '-TEMPLATE-CLOSE-' and isinstance(values, dict):
            tpl_path = values.get('-TEMPLATE-CLOSE-')
            if tpl_path and os.path.exists(tpl_path):
                try:
                    img_data = open(tpl_path, 'rb').read()
                    window['-TEMPLATE-THUMB-'].update(data=img_data)
                except Exception:
                    pass

        if event == '-TEST-CLOSE-':
            # Interactive test for close-template
            tpl = None
            if isinstance(values, dict):
                tpl = values.get('-TEMPLATE-CLOSE-')
            if not tpl:
                tpl = None
                candidate = None
                # search for CloseAd.png in repo
                root = os.path.abspath(os.path.dirname(__file__))
                for dirpath, dirnames, filenames in os.walk(root):
                    if 'CloseAd.png' in filenames:
                        candidate = os.path.join(dirpath, 'CloseAd.png')
                        break
                if candidate:
                    tpl = candidate
            window['-LOG-'].print(f"[popup-test] using template: {tpl}")
            found = close_popup_if_present(log=lambda m: window.write_event_value('-THREAD_LOG-', m), templates=[tpl] if tpl else [])
            window['-LOG-'].print(f"[popup-test] result: {found}")
            continue

        if event == '-START-':
            try:
                interval = float(values['-INTERVAL-'])
            except ValueError:
                sg.popup_error('Interval must be a number')
                continue

            # Map some actions to manager-controlled modules
            action_map = {
                'Farm Campaign': ('campaign', campaign_loop),
                'Arena': ('arena', arena_loop),
                'Tag Arena': ('tag_arena', tag_arena_loop),
            }

            # gather selections from the Listbox (-ACTIONS-) or legacy combo
            selections = []
            if isinstance(values, dict):
                sel = values.get('-ACTIONS-')
                if sel:
                    selections = sel
                else:
                    single = values.get('-ACTION-')
                    if single:
                        selections = [single]

            if not selections:
                sg.popup_error('No action selected')
                continue

            # convert selections into a list of (display_name, internal_name, target)
            seq = []
            for item in selections:
                if item in action_map:
                    seq.append((item, action_map[item][0], action_map[item][1]))
                else:
                    seq.append((item, None, None))

            # simple single non-module fallback
            if len(seq) == 1 and seq[0][1] is None:
                action = seq[0][0]
                # prepare window (close popups, position) before starting single BotThread
                try:
                    tpl = values.get('-TEMPLATE-') if isinstance(values, dict) else None
                    tpl = tpl if tpl else None
                    close_tpl = values.get('-TEMPLATE-CLOSE-') if isinstance(values, dict) else None
                    if not close_tpl:
                        # search for CloseAd.png
                        candidate = None
                        root = os.path.abspath(os.path.dirname(__file__))
                        for dirpath, dirnames, filenames in os.walk(root):
                            if 'CloseAd.png' in filenames:
                                candidate = os.path.join(dirpath, 'CloseAd.png')
                                break
                        if candidate:
                            close_tpl = candidate
                    if close_tpl:
                        close_popup_if_present(log=_module_log, templates=[close_tpl])
                    if tpl:
                        ensure_game_window(log=_module_log, template_path=tpl)
                    else:
                        ensure_game_window(log=_module_log)
                    if close_tpl:
                        close_popup_if_present(log=_module_log, templates=[close_tpl])
                except Exception as exc:
                    _module_log(f"[init] single-start prep error: {exc}")

                bot = BotThread(window, action, interval)
                bot.start()
                start_time = time.time()
                running = True
                window['-START-'].update(disabled=True)
                window['-STOP-'].update(disabled=False)
                continue

            # multi-module sequence
            modules_to_run = [(name_key, target) for (display, name_key, target) in seq if name_key]
            try:
                def _module_log(m: str):
                    window.write_event_value('-THREAD_LOG-', m)

                # prepare template paths
                tpl = values.get('-TEMPLATE-') if isinstance(values, dict) else None
                tpl = tpl if tpl else None
                close_tpl = values.get('-TEMPLATE-CLOSE-') if isinstance(values, dict) else None
                if not close_tpl:
                    # search repo for CloseAd.png as fallback
                    candidate = None
                    root = os.path.abspath(os.path.dirname(__file__))
                    for dirpath, dirnames, filenames in os.walk(root):
                        if 'CloseAd.png' in filenames:
                            candidate = os.path.join(dirpath, 'CloseAd.png')
                            break
                    if candidate:
                        close_tpl = candidate

                # controller to run modules sequentially and perform init checks between modules
                class SequenceController(threading.Thread):
                    def __init__(self, mgr, modules, win, log_func, tpl_path=None, close_path=None):
                        super().__init__(daemon=True)
                        self.mgr = mgr
                        self.modules = modules
                        self.win = win
                        self.log = log_func
                        self._stop = threading.Event()
                        self.current = None
                        self.tpl_path = tpl_path
                        self.close_path = close_path

                    def stop(self):
                        self._stop.set()
                        if self.current:
                            try:
                                self.mgr.stop_module(self.current)
                            except Exception:
                                pass

                    def _prepare_window(self):
                        # attempt to close popup, ensure window positioning, then close again
                        try:
                            if self.close_path:
                                close_popup_if_present(log=self.log, templates=[self.close_path])
                        except Exception:
                            pass
                        try:
                            if self.tpl_path:
                                ensure_game_window(log=self.log, template_path=self.tpl_path)
                            else:
                                ensure_game_window(log=self.log)
                        except Exception:
                            pass
                        try:
                            if self.close_path:
                                close_popup_if_present(log=self.log, templates=[self.close_path])
                        except Exception:
                            pass

                    def run(self):
                        for name, target in self.modules:
                            if self._stop.is_set():
                                break
                            
                            # Check if module is on cooldown
                            remaining = self.mgr.get_cooldown_remaining(name)
                            if remaining > 0:
                                mins, secs = divmod(int(remaining), 60)
                                self.log(f"[sequence] {name} is on cooldown for {mins}m {secs}s; skipping until next cycle")
                                self.win.write_event_value('-THREAD_LOG-', f"[sequence] skipping {name} (cooldown: {mins}m {secs}s)")
                                continue
                            
                            # prepare window before each module
                            self._prepare_window()
                            try:
                                if not self.mgr.is_registered(name):
                                    self.mgr.register_module(name, target, log_func=self.log)
                            except Exception:
                                pass
                            self.current = name
                            self.win.write_event_value('-MODULE_STARTED-', name)
                            self.mgr.start_module(name)
                            while not self._stop.is_set() and self.mgr.is_running(name):
                                time.sleep(0.2)
                            try:
                                self.mgr.stop_module(name)
                                # Mark module as completed for cooldown tracking
                                self.mgr.mark_completed(name)
                            except Exception:
                                pass
                            self.win.write_event_value('-MODULE_ENDED-', name)
                        self.win.write_event_value('-SEQUENCE_DONE-', True)

                controller = SequenceController(manager, modules_to_run, window, _module_log, tpl_path=tpl, close_path=close_tpl)
                controller_ref = controller
                controller.start()
                window['-LOG-'].print(f"[manager] started module sequence: {[n for n,_ in modules_to_run]}")
                window['-START-'].update(disabled=True)
                window['-STOP-'].update(disabled=False)
                start_time = time.time()
                running = True
            except Exception as exc:
                sg.popup_error(f"Failed to start module sequence: {exc}")

        elif event == '-STOP-':
            if current_module_name:
                try:
                    manager.stop_module(current_module_name)
                    window['-LOG-'].print(f"[manager] stopped module: {current_module_name}")
                except Exception:
                    window['-LOG-'].print(f"[manager] failed to stop: {current_module_name}")
                current_module_name = None
            if bot:
                bot.stop()
                bot = None
            # stop any running controller sequence
            if controller_ref:
                try:
                    controller_ref.stop()
                except Exception:
                    pass
                controller_ref = None
            # stop runtime timer and reset display
            running = False
            start_time = None
            window['-TIMER-'].update('00:00:00')
            window['-START-'].update(disabled=False)
            window['-STOP-'].update(disabled=True)

        elif event == '-THREAD_LOG-':
            # This catches the message sent from the BotThread or modules.
            msg = values['-THREAD_LOG-']
            # filter out frequent module ticks (they're noisy)
            try:
                s = str(msg).strip()
                if s.endswith('tick') or s.endswith('[tick]') or s.endswith(' tick'):
                    # ignore tick messages
                    pass
                else:
                    from datetime import datetime
                    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    window['-LOG-'].print(f"[{ts}] {msg}")
            except Exception:
                window['-LOG-'].print(msg)

        elif event == '-MODULE_STARTED-':
            name = values['-MODULE_STARTED-']
            current_module_name = name
            start_time = time.time()
            running = True
            window['-LOG-'].print(f"[sequence] module started: {name}")

        elif event == '-MODULE_ENDED-':
            name = values['-MODULE_ENDED-']
            window['-LOG-'].print(f"[sequence] module ended: {name}")
            current_module_name = None

        elif event == '-SEQUENCE_DONE-':
            window['-LOG-'].print('[sequence] all modules finished')
            running = False
            start_time = None
            current_module_name = None
            controller_ref = None
            window['-TIMER-'].update('00:00:00')
            window['-START-'].update(disabled=False)
            window['-STOP-'].update(disabled=True)

        # update runtime timer display every loop when running
        try:
            if running and start_time:
                elapsed = int(time.time() - start_time)
                hrs = elapsed // 3600
                mins = (elapsed % 3600) // 60
                secs = elapsed % 60
                window['-TIMER-'].update(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        except Exception:
            pass

    window.close()


if __name__ == '__main__':
    main()
