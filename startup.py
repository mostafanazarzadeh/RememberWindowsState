"""
RememberWindowsState — startup.py
Adds / removes the app from the Windows user-level startup Registry key.
"""

import os
import sys
import winreg

from app_logger import get_logger

log = get_logger(__name__)

APP_NAME = 'RememberWindowsState'
RUN_KEY  = r'Software\Microsoft\Windows\CurrentVersion\Run'


def _startup_command() -> str:
    """Return the command string to store in the Registry."""
    if getattr(sys, 'frozen', False):
        # Running as a compiled .exe
        return f'"{sys.executable}" --startup'
    # Running as a plain Python script
    script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'main.py')
    )
    return f'"{sys.executable}" "{script}" --startup'


def enable_startup() -> bool:
    """Register the app to run at Windows login. Returns True on success."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        cmd = _startup_command()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        log.info('Startup enabled — registry value set: %s', cmd)
        return True
    except Exception as exc:
        log.error('Failed to enable startup: %s', exc)
        return False


def disable_startup() -> bool:
    """Remove the app from Windows startup. Returns True on success."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
            log.info('Startup disabled — registry value removed')
        except FileNotFoundError:
            log.debug('Startup disable — registry value was not present')
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        log.error('Failed to disable startup: %s', exc)
        return False


def is_startup_enabled() -> bool:
    """Return True if a startup Registry entry already exists."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False
