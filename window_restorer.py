"""
RememberWindowsState — window_restorer.py
Detects which saved windows are not yet open and re-launches them.
Handles normal, minimized, maximized, and tray-only application states.
"""

import os
import time
import subprocess
import threading

import win32gui
import win32process
import win32con
import psutil

from app_logger import get_logger

log = get_logger(__name__)


def get_running_exe_paths() -> set[str]:
    """
    Return a set of lowercase exe paths for every process that is
    currently running AND has at least one window handle — whether the
    window is visible, minimized, or hidden (tray-only).

    Using psutil to scan all processes avoids the limitation of
    EnumWindows which can miss tray-only or minimized-but-hidden windows.
    """
    # Collect all PIDs that own at least one window (any visibility state)
    pids_with_window: set[int] = set()

    def _cb(hwnd, _):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pids_with_window.add(pid)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass

    open_exes: set[str] = set()
    for pid in pids_with_window:
        try:
            proc = psutil.Process(pid)
            open_exes.add(proc.exe().lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass

    return open_exes


def get_running_state_caches() -> tuple[dict[str, list[int]], set[int]]:
    """
    Fetches running processes and window handles once.
    Returns (exe_to_pids_map, pids_with_visible_window_set)
    """
    exe_to_pids = {}
    pids_with_visible_window = set()
    
    # Get all running exe paths and their PIDs
    for proc in psutil.process_iter(['pid', 'exe']):
        try:
            exe = proc.info['exe']
            if exe:
                exe_lower = exe.lower()
                if exe_lower not in exe_to_pids:
                    exe_to_pids[exe_lower] = []
                exe_to_pids[exe_lower].append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
            
    # Get PIDs with visible or iconic windows
    def _cb(hwnd, _):
        try:
            if win32gui.GetParent(hwnd) != 0:
                return
            
            # Must be visible or iconic (minimized)
            is_visible = bool(win32gui.IsWindowVisible(hwnd))
            is_iconic = bool(win32gui.IsIconic(hwnd))
            if not is_visible and not is_iconic:
                return
                
            title = win32gui.GetWindowText(hwnd)
            if not title.strip():
                return
                
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                return
                
            # Ignore background helper windows
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
                
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pids_with_visible_window.add(pid)
        except Exception:
            pass
            
    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
        
    return exe_to_pids, pids_with_visible_window


def is_app_running_cached(exe_path: str, state: str, exe_to_pids: dict[str, list[int]], pids_with_visible_window: set[int]) -> bool:
    """
    Check if the app is already running in the target state using cached data.
    """
    exe_path_lower = exe_path.lower()
    pids = exe_to_pids.get(exe_path_lower, [])
    if not pids:
        return False
        
    if state == 'tray':
        return True
        
    # Check if any PID for this exe has a visible/iconic window
    for pid in pids:
        if pid in pids_with_visible_window:
            return True
            
    return False


def get_open_explorer_paths() -> set[str]:
    """Return a set of lowercase folder paths for all currently open explorer windows."""
    paths = set()
    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        for window in shell.Windows():
            try:
                name = window.Name
                if name in ("File Explorer", "Windows Explorer"):
                    doc_path = window.Document.Folder.Self.Path
                    if doc_path:
                        paths.add(doc_path.lower())
            except Exception:
                pass
    except Exception:
        pass
    return paths


def _position_new_explorer_window(target_path: str, x: int, y: int, w: int, h: int, state: str):
    """Wait for a newly opened explorer window to match target_path and apply positions."""
    import time
    import win32gui
    import win32con
    import win32com.client
    import pythoncom
    
    hwnd = None
    shell = None
    
    for _ in range(25):  # 25 * 0.2s = 5s max wait
        time.sleep(0.2)
        try:
            if shell is None:
                pythoncom.CoInitialize()
                shell = win32com.client.Dispatch("Shell.Application")
            
            windows = shell.Windows()
            for window in windows:
                try:
                    name = window.Name
                    if name in ("File Explorer", "Windows Explorer"):
                        doc_path = window.Document.Folder.Self.Path
                        if doc_path and doc_path.lower() == target_path.lower():
                            hwnd = window.HWND
                            break
                except Exception:
                    pass
            if hwnd:
                break
        except Exception:
            pass
            
    if hwnd:
        try:
            if state == 'minimized':
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            elif state == 'maximized':
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
            else:
                win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        except Exception:
            pass


def _position_new_window(exe_path: str, state: str, x: int, y: int, w: int, h: int):
    """Wait for a newly opened window of exe_path to appear, then apply position and state."""
    import time
    import win32gui
    import win32process
    import win32con
    import psutil

    target_exe_path = exe_path.lower()
    hwnd = None

    for _ in range(50):  # 50 * 0.1s = 5s max wait
        time.sleep(0.1)
        
        def _enum_cb(h, _):
            nonlocal hwnd
            if hwnd:
                return
            
            if win32gui.GetParent(h) != 0:
                return
            
            try:
                ex_style = win32gui.GetWindowLong(h, win32con.GWL_EXSTYLE)
                if ex_style & win32con.WS_EX_TOOLWINDOW:
                    return
            except Exception:
                pass
            
            title = win32gui.GetWindowText(h)
            if not title.strip():
                return

            # Ignore background helper windows such as OfficePowerManagerWindow
            title_lower = title.lower()
            ignore_keywords = {'officepowermanagerwindow'}
            if any(kw in title_lower for kw in ignore_keywords):
                return
            try:
                class_name = win32gui.GetClassName(h).lower()
                if any(kw in class_name for kw in ignore_keywords):
                    return
            except Exception:
                pass
            
            try:
                _, pid = win32process.GetWindowThreadProcessId(h)
                proc = psutil.Process(pid)
                proc_exe = proc.exe().lower()
                if proc_exe == target_exe_path:
                    hwnd = h
            except Exception:
                pass

        try:
            win32gui.EnumWindows(_enum_cb, None)
        except Exception:
            pass

        if hwnd:
            break

    if hwnd:
        try:
            if state == 'tray':
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            elif state == 'minimized':
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            elif state == 'maximized':
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                win32gui.SetForegroundWindow(hwnd)
            else:
                time.sleep(0.05)  # small buffer for UI thread
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
                win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            log.debug("Failed to set window position/state for %s: %s", exe_path, e)


def filter_not_open(windows: list[dict]) -> list[dict]:
    """
    From a snapshot's window list, return only the entries whose
    executable is NOT currently running.
    De-duplicates by exe path (and explorer path) so we don't offer to open the same app/folder twice.
    """
    exe_to_pids, pids_with_visible_window = get_running_state_caches()
    running_explorer_paths = get_open_explorer_paths()
    seen: set[str] = set()
    result: list[dict] = []

    for w in windows:
        exe_path = w['exe_path'].lower()
        exe_name = w.get('exe_name', '').lower()

        if exe_name == 'explorer.exe' and 'explorer_path' in w:
            path = w['explorer_path'].lower()
            key = f"explorer:{path}"
            if key in seen:
                continue
            seen.add(key)
            if path not in running_explorer_paths:
                result.append(w)
        else:
            key = exe_path
            if key in seen:
                continue
            seen.add(key)
            state = w.get('state', 'normal')
            if not is_app_running_cached(exe_path, state, exe_to_pids, pids_with_visible_window):
                result.append(w)

    return result


def restore_window(window_info: dict) -> tuple[bool, str]:
    """Launch a single application (or bring it back if minimized/tray).
    Returns (success, message)."""
    exe_path = window_info.get('exe_path', '')
    exe_name = window_info.get('exe_name', '').lower()
    state    = window_info.get('state', 'normal')

    if not exe_path or not os.path.exists(exe_path):
        msg = f'Executable not found: {exe_path}'
        log.warning('Restore skipped — %s', msg)
        return False, msg

    # Handle Windows Explorer paths specially
    if exe_name == 'explorer.exe' and 'explorer_path' in window_info:
        target_path = window_info['explorer_path']
        
        # Check if an explorer window with the same folder path is already open
        hwnd = None
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            for window in shell.Windows():
                try:
                    name = window.Name
                    if name in ("File Explorer", "Windows Explorer"):
                        doc_path = window.Document.Folder.Self.Path
                        if doc_path and doc_path.lower() == target_path.lower():
                            hwnd = window.HWND
                            break
                except Exception:
                    pass
        except Exception:
            pass

        if hwnd:
            try:
                if state == 'minimized':
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                elif state == 'maximized':
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                    win32gui.SetForegroundWindow(hwnd)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    x, y, w, h = window_info['x'], window_info['y'], window_info['width'], window_info['height']
                    win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
                    win32gui.SetForegroundWindow(hwnd)
                log.info('Restored explorer folder ✓  %s', target_path)
                return True, 'restored from tray/minimized'
            except Exception as e:
                log.warning('Restore failed for Explorer window %s: %s', target_path, e)

        # Launch fresh explorer window at folder path
        try:
            subprocess.Popen(["explorer.exe", target_path])
            
            x, y, w, h = window_info['x'], window_info['y'], window_info['width'], window_info['height']
            threading.Thread(
                target=_position_new_explorer_window,
                args=(target_path, x, y, w, h, state),
                daemon=True
            ).start()
            
            log.info('Restored (launched) explorer folder ✓  %s', target_path)
            return True, 'OK'
        except Exception as exc:
            log.error('Restore failed for Explorer path %s: %s', target_path, exc)
            return False, str(exc)

    # If the app is already running (minimized, maximized, tray, or normal), restore its state & position
    exe_to_pids, pids_with_visible_window = get_running_state_caches()
    if is_app_running_cached(exe_path, state, exe_to_pids, pids_with_visible_window):
        if state == 'tray':
            log.info('App already running in tray: %s', exe_path)
            return True, 'restored running application'

        restored_window = False
        pids = exe_to_pids.get(exe_path.lower(), [])

        def _show_cb(hwnd, _):
            nonlocal restored_window
            try:
                if win32gui.GetParent(hwnd) != 0:
                    return
                is_visible = bool(win32gui.IsWindowVisible(hwnd))
                is_iconic = bool(win32gui.IsIconic(hwnd))
                if not is_visible and not is_iconic:
                    return
                title = win32gui.GetWindowText(hwnd)
                if not title.strip():
                    return
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if ex_style & win32con.WS_EX_TOOLWINDOW:
                    return
                # Ignore background helper windows
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
                
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid in pids:
                    if state == 'minimized':
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    elif state == 'maximized':
                        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                        win32gui.SetForegroundWindow(hwnd)
                    else:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        x, y, w, h = window_info.get('x', 0), window_info.get('y', 0), window_info.get('width', 0), window_info.get('height', 0)
                        win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
                        win32gui.SetForegroundWindow(hwnd)
                    restored_window = True
            except Exception:
                pass

        try:
            win32gui.EnumWindows(_show_cb, None)
            if restored_window:
                log.info('Restored state & position for running app ✓  %s', exe_path)
                return True, 'restored running application'
            else:
                log.warning('Failed to find matching window handle for running process: %s', exe_path)
        except Exception as exc:
            log.warning('State/position restore failed for running app %s: %s', exe_path, exc)

    # App is not running at all — launch it fresh
    try:
        cwd = os.path.dirname(exe_path) or None
        
        # Build startupinfo to launch in target state
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        if state == 'tray':
            startupinfo.wShowWindow = win32con.SW_HIDE
        elif state == 'minimized':
            startupinfo.wShowWindow = win32con.SW_SHOWMINNOACTIVE
        elif state == 'maximized':
            startupinfo.wShowWindow = win32con.SW_SHOWMAXIMIZED
        else:
            startupinfo.wShowWindow = win32con.SW_SHOWNORMAL

        subprocess.Popen(
            [exe_path],
            cwd=cwd,
            startupinfo=startupinfo,
            creationflags=(
                subprocess.DETACHED_PROCESS |
                subprocess.CREATE_NEW_PROCESS_GROUP
            ),
            close_fds=True,
        )
        
        # Start background thread to watch and apply precise layout/state
        x, y, w, h = window_info.get('x', 0), window_info.get('y', 0), window_info.get('width', 0), window_info.get('height', 0)
        threading.Thread(
            target=_position_new_window,
            args=(exe_path, state, x, y, w, h),
            daemon=True,
            name=f'PositionWatcher_{os.path.basename(exe_path)}'
        ).start()
        
        log.info('Restored (launched) ✓  %s (cwd: %s, state: %s)', exe_path, cwd, state)
        return True, 'OK'
    except Exception as exc:
        log.error('Restore failed ✗  %s  —  %s', exe_path, exc)
        return False, str(exc)


def restore_windows(windows: list[dict]) -> list[tuple]:
    """
    Restore a list of windows sequentially.
    Returns list of (window_info, success, message).
    """
    log.info('Restore session started — %d application(s) requested', len(windows))
    results = []
    for w in windows:
        success, msg = restore_window(w)
        results.append((w, success, msg))
        if success:
            time.sleep(0.4)   # small delay between launches
    ok  = sum(1 for _, s, _ in results if s)
    err = len(results) - ok
    log.info('Restore session complete — %d succeeded, %d failed', ok, err)
    return results
