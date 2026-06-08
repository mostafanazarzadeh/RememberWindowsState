"""
RememberWindowsState — window_tracker.py
Enumerates visible, meaningful windows using pywin32 + psutil,
and saves/loads snapshots as JSON.
Also manages a multi-entry history file (history.json).

Window state values stored in each record:
  'normal'    — regular visible window
  'minimized' — minimized to taskbar (IsIconic)
  'maximized' — maximized / zoomed window (IsZoomed)
  'tray'      — app running with no normal/minimized window (tray-only)
"""

import os
import json
from datetime import datetime

import win32gui
import win32process
import win32con
import psutil

from app_logger import get_logger

log = get_logger(__name__)

# ── Executables to always ignore ──────────────────────────────────────────────
SYSTEM_EXES = {
    'explorer.exe', 'searchhost.exe', 'startmenuexperiencehost.exe',
    'shellexperiencehost.exe', 'runtimebroker.exe', 'svchost.exe',
    'taskhostw.exe', 'sihost.exe', 'ctfmon.exe', 'dwm.exe',
    'fontdrvhost.exe', 'lsass.exe', 'services.exe', 'smss.exe',
    'csrss.exe', 'wininit.exe', 'winlogon.exe', 'conhost.exe',
    'dllhost.exe', 'applicationframehost.exe', 'textinputhost.exe',
    'lockapp.exe', 'logonui.exe', 'userinit.exe',
    'rememberwindowsstate.exe',   # don't track ourselves
    'taskmgr.exe',
}


def get_open_windows(blacklist: list | None = None, track_explorer: bool = False) -> list[dict]:
    """
    Return a list of dicts describing every meaningful top-level window
    or tray-only process currently open, including minimized windows.

    Each record contains:
      title, exe_path, exe_name, x, y, width, height,
      minimized (bool), state ('normal' | 'minimized' | 'tray')
    """
    if blacklist is None:
        blacklist = []

    blacklist_lower = {b.lower() for b in blacklist}
    seen_exe_paths: set[str] = set()
    windows: list[dict] = []

    hwnd_to_folder_path = {}
    if track_explorer:
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            shell_windows = shell.Windows()
            log.debug("COM shell windows count: %s", len(shell_windows) if shell_windows is not None else "None")
            if shell_windows is not None:
                for window in shell_windows:
                    try:
                        name = window.Name
                        log.debug("COM window inspect: Name=%s, HWND=%s", name, getattr(window, 'HWND', 'N/A'))
                        if name in ("File Explorer", "Windows Explorer"):
                            hwnd = window.HWND
                            doc_path = window.Document.Folder.Self.Path
                            if hwnd and doc_path:
                                hwnd_to_folder_path[hwnd] = doc_path
                    except Exception as e:
                        log.debug("COM window error: %s", e)
        except Exception as e:
            log.error("COM initialization error: %s", e)

    def _enum_callback(hwnd, _):
        # Accept both visible and minimized (iconic) windows.
        # IsWindowVisible returns True for minimized windows too,
        # but we explicitly check IsIconic to handle either case.
        is_iconic = bool(win32gui.IsIconic(hwnd))
        if not win32gui.IsWindowVisible(hwnd) and not is_iconic:
            return

        title = win32gui.GetWindowText(hwnd)
        if not title.strip():
            return

        # Ignore background helper windows such as OfficePowerManagerWindow
        title_lower = title.lower()
        ignore_keywords = {'officepowermanagerwindow'}
        if any(kw in title_lower for kw in ignore_keywords):
            return
        try:
            class_name = win32gui.GetClassName(hwnd).lower()
            if any(kw in class_name for kw in ignore_keywords):
                return
        except Exception:
            pass

        # Only real top-level windows (no parent)
        if win32gui.GetParent(hwnd) != 0:
            return

        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # Skip child windows
        if style & win32con.WS_CHILD:
            return

        # Skip tool windows (small floating utilities)
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            exe_name = os.path.basename(exe_path).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return

        if exe_name in SYSTEM_EXES:
            if exe_name == 'explorer.exe' and track_explorer and hwnd in hwnd_to_folder_path:
                pass
            else:
                return
        if exe_name in blacklist_lower:
            return

        # De-duplicate: one entry per exe path (or explorer folder path)
        exe_key = exe_path.lower()
        explorer_path = None
        if exe_name == 'explorer.exe':
            explorer_path = hwnd_to_folder_path.get(hwnd)
            if not explorer_path:
                return  # ignore system explorer windows
            exe_key = f"explorer:{explorer_path.lower()}"

        if exe_key in seen_exe_paths:
            return
        seen_exe_paths.add(exe_key)

        rect = win32gui.GetWindowRect(hwnd)
        x, y, right, bottom = rect
        w = right - x
        h = bottom - y

        # Minimized windows have a special placement rect (-32000, -32000).
        # We still record them; restore will use ShowWindow(SW_RESTORE).
        if not is_iconic and (w <= 0 or h <= 0):
            return

        is_zoomed = bool(style & win32con.WS_MAXIMIZE)
        if is_iconic:
            state = 'minimized'
        elif is_zoomed:
            state = 'maximized'
        else:
            state = 'normal'

        win_record = {
            'title':     title,
            'exe_path':  exe_path,
            'exe_name':  exe_name,
            'x':         x,
            'y':         y,
            'width':     w,
            'height':    h,
            'minimized': is_iconic,
            'state':     state,
        }
        if explorer_path:
            win_record['explorer_path'] = explorer_path

        windows.append(win_record)

    win32gui.EnumWindows(_enum_callback, None)

    # ── Also capture tray-only processes (running but no visible window) ───────
    _add_tray_processes(blacklist_lower, seen_exe_paths, windows)

    log.debug('get_open_windows — found %d window(s) (incl. minimized/tray)',
              len(windows))
    return windows


def _add_tray_processes(
        blacklist_lower: set,
        seen_exe_paths: set,
        windows: list[dict],
) -> None:
    """
    Walk all running processes and add an entry for any executable that:
      - has an open window handle (even hidden / tray-only)
      - is NOT already captured by EnumWindows (i.e., truly tray-only)
    """
    # Collect pids that own at least one window (any state)
    pids_with_any_window: set[int] = set()

    def _any_win_cb(hwnd, _):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pids_with_any_window.add(pid)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_any_win_cb, None)
    except Exception:
        pass

    for pid in pids_with_any_window:
        try:
            proc = psutil.Process(pid)
            exe_path = proc.exe()
            exe_name = os.path.basename(exe_path).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue

        if exe_name in SYSTEM_EXES:
            continue
        if exe_name in blacklist_lower:
            continue

        exe_key = exe_path.lower()
        if exe_key in seen_exe_paths:
            continue   # already captured as normal/minimized
        seen_exe_paths.add(exe_key)

        # Try to get a name from the process cmdline or exe
        try:
            name = proc.name()
        except Exception:
            name = exe_name

        windows.append({
            'title':     name,
            'exe_path':  exe_path,
            'exe_name':  exe_name,
            'x':         0,
            'y':         0,
            'width':     0,
            'height':    0,
            'minimized': False,
            'state':     'tray',
        })


def save_snapshot(windows: list[dict], state_file: str) -> None:
    """Persist window list to JSON."""
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'windows':   windows,
    }
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        log.info('Snapshot written to: %s  (%d windows)', state_file, len(windows))
    except Exception as e:
        log.error('Snapshot save error: %s', e)


def load_snapshot(state_file: str) -> dict | None:
    """Load the most recent snapshot, or return None."""
    if not os.path.exists(state_file):
        log.debug('No snapshot file found at: %s', state_file)
        return None
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        log.debug('Snapshot loaded — %d window(s), timestamp: %s',
                  len(data.get('windows', [])), data.get('timestamp', '?'))
        return data
    except Exception as e:
        log.error('Snapshot load error: %s', e)
        return None


# ── History (multiple snapshots) ──────────────────────────────────────────────
_HISTORY_MAX = 50   # keep at most this many entries


def _history_path(state_file: str) -> str:
    """Derive the history file path from the state file path."""
    d = os.path.dirname(state_file)
    return os.path.join(d, 'history.json')


def trim_history(state_file: str, limit: int) -> None:
    """Trim the history file to keep at most `limit` entries."""
    hist_file = _history_path(state_file)
    if not os.path.exists(hist_file):
        return
    entries = load_history(state_file)
    if len(entries) > limit:
        trimmed = entries[-limit:]
        try:
            with open(hist_file, 'w', encoding='utf-8') as f:
                json.dump(trimmed, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'[Tracker] history trim error: {e}')


def save_to_history(windows: list[dict], state_file: str,
                    label: str = '', limit: int = _HISTORY_MAX) -> None:
    """
    Append a new snapshot entry to history.json.
    Trims older entries so the list never exceeds the specified limit.
    """
    hist_file = _history_path(state_file)
    entries = load_history(state_file)

    entry = {
        'timestamp': datetime.now().isoformat(),
        'label':     label,
        'windows':   windows,
    }
    entries.append(entry)

    # Keep only the most recent limit entries
    if len(entries) > limit:
        entries = entries[-limit:]

    try:
        with open(hist_file, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'[Tracker] history save error: {e}')


def load_history(state_file: str) -> list[dict]:
    """Return the list of history entries (newest last), or [] on error."""
    hist_file = _history_path(state_file)
    if not os.path.exists(hist_file):
        return []
    try:
        with open(hist_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def get_window_exe_set(windows: list[dict]) -> frozenset:
    """
    Return a frozenset of unique keys from a window list.
    Used to compare two states and detect open/close changes.
    """
    keys = []
    for w in windows:
        exe_name = w.get('exe_name', '').lower()
        if exe_name == 'explorer.exe' and 'explorer_path' in w:
            keys.append(f"explorer:{w['explorer_path'].lower()}")
        else:
            keys.append(w.get('exe_path', '').lower())
    return frozenset(keys)
