"""
RememberWindowsState — main.py
Entry point.

Launch modes
────────────
  python main.py            →  manual launch
                               • single-instance guard
                               • show restore dialog if unclosed windows exist
                               • start tray + scheduler

  python main.py --startup  →  launched by Windows at login
                               • single-instance guard
                               • skip restore dialog, track silently
"""

import os
import sys

# Ensure the directory containing this script is always on the path,
# so sibling modules (tray_app, config, etc.) are found regardless of
# the current working directory (double-click, shortcut, PyInstaller, etc.)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ctypes
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import win32gui
import win32con

from app_logger      import setup_logging, get_logger
from config          import Config
from scheduler       import WindowScheduler
from window_tracker  import (get_open_windows, save_snapshot, load_snapshot,
                              save_to_history, get_window_exe_set)
from tray_app        import TrayApp

log = get_logger(__name__)


# ── Window-change watcher ────────────────────────────────────────────────
class WindowChangeWatcher:
    """
    Polls visible windows every POLL_INTERVAL seconds.
    When the SET of exe paths changes (window opened or closed),
    records a new entry in history.json.
    Move / resize events are intentionally ignored.
    """
    POLL_INTERVAL = 2   # seconds

    def __init__(self, config: Config):
        self._config   = config
        self._last_set: frozenset = frozenset()
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        # Seed the initial state without saving
        try:
            wins = get_open_windows(blacklist=self._config.blacklist, track_explorer=self._config.track_explorer)
            self._last_set = get_window_exe_set(wins)
        except Exception:
            pass

        self._thread = threading.Thread(
            target=self._loop, daemon=True, name='WindowChangeWatcher')
        self._thread.start()

    def stop(self):
        self._stop_evt.set()

    def _loop(self):
        while not self._stop_evt.is_set():
            self._stop_evt.wait(self.POLL_INTERVAL)
            if self._stop_evt.is_set():
                break
            try:
                wins     = get_open_windows(blacklist=self._config.blacklist, track_explorer=self._config.track_explorer)
                cur_set  = get_window_exe_set(wins)
                if cur_set != self._last_set:
                    opened = cur_set - self._last_set
                    closed = self._last_set - cur_set
                    
                    def _get_friendly_names(keys):
                        names_list = []
                        for p in keys:
                            if p.startswith('explorer:'):
                                folder = p.split(':', 1)[1]
                                if folder.startswith('::'):
                                    if folder == '::{20d04fe0-3aea-1069-a2d8-08002b30309d}':
                                        names_list.append("This PC")
                                    else:
                                        names_list.append("File Explorer")
                                else:
                                    names_list.append(os.path.basename(folder))
                            else:
                                names_list.append(os.path.basename(p))
                        return ', '.join(names_list)

                    if opened:
                        names = _get_friendly_names(opened)
                        label = f'➕ Opened: {names}'
                    else:
                        names = _get_friendly_names(closed)
                        label = f'❌ Closed: {names}'
                    save_to_history(wins, self._config.state_file, label=label, limit=self._config.history_limit)
                    self._last_set = cur_set
                    log.info('[Watcher] history entry saved — %s', label)
            except Exception as exc:
                log.error('[Watcher] error: %s', exc)


# ── Single-instance mutex ─────────────────────────────────────────────────────
_MUTEX_NAME = 'RememberWindowsStateMutex_2025'
_mutex_handle = None


def _already_running() -> bool:
    global _mutex_handle
    try:
        import win32event
        import win32api
        _mutex_handle = win32event.CreateMutex(None, False, _MUTEX_NAME)
        return win32api.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception as exc:
        log.error('Mutex creation error: %s', exc)
        return False


# ── Snapshot save callback ────────────────────────────────────────────────────
def _do_save(config: Config, is_manual: bool = False) -> None:
    try:
        windows = get_open_windows(blacklist=config.blacklist, track_explorer=config.track_explorer)
        save_snapshot(windows, config.state_file)
        log.info('Snapshot saved — %d window(s) recorded', len(windows))
        if is_manual:
            save_to_history(windows, config.state_file, label='💾 Manually Saved', limit=config.history_limit)
            log.info('Manual snapshot appended to history')
    except Exception as exc:
        log.exception('Snapshot save failed: %s', exc)


def _merge_windows(current_windows: list[dict], last_saved_windows: list[dict]) -> list[dict]:
    """
    Merge the newly captured window list with the last saved snapshot.
    Preserves any windows that were present in the last snapshot but are missing
    in the new snapshot (likely closed early by OS shutdown / restart).
    Updates positions and states of windows still present.
    """
    def get_window_key(w: dict) -> str:
        exe_name = w.get('exe_name', '').lower()
        if exe_name == 'explorer.exe' and 'explorer_path' in w:
            return f"explorer:{w['explorer_path'].lower()}"
        return w.get('exe_path', '').lower()

    current_lookup = {get_window_key(w): w for w in current_windows if get_window_key(w)}
    merged = []
    
    # Process windows from the last saved snapshot
    for w in last_saved_windows:
        key = get_window_key(w)
        if not key:
            continue
        if key in current_lookup:
            # Window is still open, use the latest captured state/position
            merged.append(current_lookup[key])
            del current_lookup[key]
        else:
            # Window is missing (likely closed by Windows shutdown), preserve it
            merged.append(w)
            
    # Add any newly opened windows that weren't in the last saved snapshot
    for w in current_lookup.values():
        merged.append(w)
        
    return merged


# ── Save state before shutdown/restart ────────────────────────────────────────
_shutdown_saved = False

def _save_state_before_shutdown(
        config: Config,
        watcher: 'WindowChangeWatcher',
        scheduler: WindowScheduler,
) -> None:
    """
    Called when Windows sends WM_QUERYENDSESSION or WM_ENDSESSION.
    Stops background tasks immediately so no empty post-shutdown state is
    recorded, then writes a final snapshot + history entry.
    """
    global _shutdown_saved
    if _shutdown_saved:
        log.info('Shutdown/restart state already saved — ignoring subsequent save request')
        return

    _shutdown_saved = True
    log.info('Shutdown/restart detected — saving final state')
    try:
        watcher.stop()
    except Exception:
        pass
    try:
        scheduler.stop()
    except Exception:
        pass
    try:
        # Load the last saved snapshot to merge with the new state
        last_snap = load_snapshot(config.state_file)
        last_windows = last_snap.get('windows', []) if last_snap else []

        windows = get_open_windows(
            blacklist=config.blacklist,
            track_explorer=config.track_explorer,
        )
        
        if last_windows:
            windows = _merge_windows(windows, last_windows)
            log.info('Merged shutdown windows with last saved snapshot: final count %d', len(windows))

        save_snapshot(windows, config.state_file)
        save_to_history(
            windows, config.state_file,
            label='🔄 Session Before Restart',
            limit=config.history_limit,
        )
        log.info('Final state saved — %d window(s)', len(windows))
    except Exception as exc:
        log.exception('Final state save failed: %s', exc)


def _resume_after_cancelled_shutdown(
        watcher: 'WindowChangeWatcher',
        scheduler: WindowScheduler,
) -> None:
    """
    Called if WM_ENDSESSION indicates that the shutdown was cancelled.
    Resets the shutdown flag and restarts the background tasks.
    """
    global _shutdown_saved
    if not _shutdown_saved:
        return

    log.info('Shutdown/restart was cancelled — resuming background tasks')
    _shutdown_saved = False
    try:
        watcher.start()
    except Exception as exc:
        log.error('Failed to restart watcher: %s', exc)
    try:
        scheduler.start()
    except Exception as exc:
        log.error('Failed to restart scheduler: %s', exc)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log_path = setup_logging()
    is_startup = '--startup' in sys.argv

    log.info('Launch mode : %s', '--startup (silent)' if is_startup else 'manual (interactive)')
    log.info('Log file    : %s', log_path)

    # ── Guard: one instance only ──────────────────────────────────────────────
    if _already_running():
        log.warning('Another instance is already running — exiting')
        if not is_startup:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                'RememberWindowsState',
                'RememberWindowsState is already running.\n'
                'Find the icon in the System Tray.')
            root.destroy()
        return

    # ── Init config & scheduler ───────────────────────────────────────────────
    config    = Config()
    scheduler = WindowScheduler(
        callback=lambda is_manual=False: _do_save(config, is_manual),
        interval=config.interval,
    )

    # ── UI queue: tray → main thread ──────────────────────────────────────────
    ui_queue: queue.Queue = queue.Queue()

    # ── Hidden main tkinter root ──────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()
    root.title('RememberWindowsState')
    root.update()   # initialise the Win32 frame so wm_frame() is valid

    # ── Hook WndProc to intercept WM_QUERYENDSESSION ──────────────────────────
    # We keep a module-level reference to the new proc so Python's GC does not
    # collect the callback while the window is alive.
    _wnd_proc_ref = [None]   # mutable container so the closure can read it
    _old_wnd_proc  = [None]

    def _wnd_proc(hwnd, msg, wparam, lparam):
        if msg == win32con.WM_QUERYENDSESSION:
            _save_state_before_shutdown(config, watcher, scheduler)
        elif msg == win32con.WM_ENDSESSION:
            # wparam is a boolean indicating if the session is actually ending
            is_ending = bool(wparam)
            if not is_ending:
                # Shutdown was cancelled! Resume normal operations.
                _resume_after_cancelled_shutdown(watcher, scheduler)
            else:
                # Session is ending, make sure we save if we haven't already
                _save_state_before_shutdown(config, watcher, scheduler)

        return win32gui.CallWindowProc(
            _old_wnd_proc[0], hwnd, msg, wparam, lparam)

    try:
        hwnd = int(root.wm_frame(), 16)
        _old_wnd_proc[0] = win32gui.SetWindowLong(
            hwnd, win32con.GWL_WNDPROC, _wnd_proc)
        _wnd_proc_ref[0] = _wnd_proc   # keep alive
        log.info('WndProc hooked — WM_QUERYENDSESSION will trigger state save')
    except Exception as exc:
        log.warning('WndProc hook failed (non-fatal): %s', exc)

    # Poll the queue every 150 ms and dispatch UI tasks on the main thread
    def _poll_queue():
        while True:
            try:
                task = ui_queue.get_nowait()
                if callable(task):
                    task()
            except queue.Empty:
                break
        root.after(150, _poll_queue)

    root.after(150, _poll_queue)

    # ── Initialise watcher (started later in startup mode) ────────────────────
    watcher = WindowChangeWatcher(config)

    # ── Show History window / startup dialog ──────────────────────────────
    def _maybe_restore():
        if is_startup:
            # ── Startup mode: show history so user can choose a state ──────
            from window_tracker import load_history, load_snapshot, get_window_exe_set
            from startup_history_dialog import StartupHistoryDialog

            entries = load_history(config.state_file)   # oldest → newest
            latest_snap = load_snapshot(config.state_file)

            if latest_snap and latest_snap.get('windows'):
                latest_entry = {
                    'timestamp': latest_snap.get('timestamp', ''),
                    'label': '💻 Last Session (Auto-Saved)',
                    'windows': latest_snap.get('windows', []),
                }
                
                # Check if the newest history entry is identical to the last saved snapshot
                if entries:
                    set_snap = get_window_exe_set(latest_entry['windows'])
                    set_hist = get_window_exe_set(entries[-1].get('windows', []))
                    if set_snap == set_hist:
                        entries[-1]['label'] = '💻 Last Session (Auto-Saved)'
                    else:
                        entries.append(latest_entry)
                else:
                    entries.append(latest_entry)

            entries_newest_first = list(reversed(entries))

            log.info(
                'Startup mode — showing history dialog (%d entries)',
                len(entries_newest_first),
            )
            dlg = StartupHistoryDialog(root, entries_newest_first, config)
            dlg.show()

            # ── Only start background tracking AFTER the dialog is dismissed ──
            log.info('Startup dialog closed — starting watcher and scheduler')
            watcher.start()
            log.info('Starting scheduler — interval: %ds', config.interval)
            scheduler.start()
        else:
            # ── Manual launch: open the Settings window directly on History ──
            log.info('Manual launch — opening Settings window (History tab)')
            from settings_gui import SettingsWindow
            SettingsWindow.show_window(root, config, scheduler, tab="history")
            
            # Start immediately for manual launch
            watcher.start()
            log.info('Starting scheduler — interval: %ds', config.interval)
            scheduler.start()

    # Show history window / startup dialog after the event loop starts
    root.after(300, _maybe_restore)

    # ── Start tray in daemon thread ───────────────────────────────────────────
    log.info('Starting system tray icon')
    tray = TrayApp(config, scheduler, ui_queue, root=root)
    tray_thread = threading.Thread(
        target=tray.run,
        daemon=True,
        name='TrayThread',
    )
    tray_thread.start()
    log.info('Application ready — running in system tray')

    # ── Run tkinter event loop (main thread) ──────────────────────────────────
    root.mainloop()
    log.info('Event loop exited — process terminating')
    sys.exit(0)


if __name__ == '__main__':
    main()
