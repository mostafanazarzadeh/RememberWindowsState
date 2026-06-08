"""
RememberWindowsState — app_logger.py
Centralised logging setup.

  • File  : %APPDATA%\\RememberWindowsState\\logs\\app.log
             Rotated at 200 KB, keeps 5 back-ups
  • Console: shown when a terminal is attached (debug / development)

Usage in any module:
    from app_logger import get_logger
    log = get_logger(__name__)
    log.info('Hello')
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME     = 'RememberWindowsState'
LOG_SUBDIR   = 'logs'
LOG_FILENAME = 'test.log' if (sys.argv and 'test' in os.path.basename(sys.argv[0]).lower()) else 'app.log'
MAX_BYTES    = 200 * 1024        # 200 KB per file
BACKUP_COUNT = 5                  # keep up to 5 rotated files

_LOG_FMT  = '%(asctime)s  %(levelname)-8s  %(name)-28s  %(message)s'
_DATE_FMT = '%Y-%m-%d %H:%M:%S'

_initialised = False


def _log_dir() -> str:
    """Return (and create if needed) the log directory inside APPDATA."""
    base = os.environ.get('APPDATA', os.path.expanduser('~'))
    path = os.path.join(base, APP_NAME, LOG_SUBDIR)
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging(level: int = logging.DEBUG) -> str:
    """
    Configure the root logger once.
    Returns the absolute path to the log file.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _initialised
    if _initialised:
        return os.path.join(_log_dir(), LOG_FILENAME)

    log_path = os.path.join(_log_dir(), LOG_FILENAME)

    root_log = logging.getLogger()
    root_log.setLevel(level)

    formatter = logging.Formatter(_LOG_FMT, datefmt=_DATE_FMT)

    # ── Rotating file handler ─────────────────────────────────────────────
    fh = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8',
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root_log.addHandler(fh)

    # ── Console handler (only when stdout is a real terminal or pipe) ──────
    if sys.stdout is not None:
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(errors='backslashreplace')
            except Exception:
                pass
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        root_log.addHandler(ch)

    _initialised = True

    # First log lines
    root_log.info('=' * 72)
    root_log.info('%s  —  logging started', APP_NAME)
    root_log.info('Log file : %s', log_path)
    root_log.info('Python   : %s', sys.version.split()[0])
    root_log.info('Platform : %s', sys.platform)
    root_log.info('=' * 72)

    return log_path


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  setup_logging() is called automatically
    if it hasn't been called yet.
    """
    setup_logging()
    return logging.getLogger(name)
