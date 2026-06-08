"""
RememberWindowsState — scheduler.py
Runs a callback at a fixed interval in a daemon background thread.
"""

import threading

from app_logger import get_logger

log = get_logger(__name__)


class WindowScheduler:
    def __init__(self, callback, interval: int = 30):
        self._callback  = callback
        self._interval  = int(interval)
        self._stop_evt  = threading.Event()
        self._thread: threading.Thread | None = None
        self._running   = False

    # ---------------------------------------------------------- public API
    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, value: int):
        self._interval = int(value)

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            log.debug('Scheduler already running — start() ignored')
            return
        self._stop_evt.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name='WindowScheduler',
        )
        self._thread.start()
        log.info('Scheduler started — interval: %ds', self._interval)

    def stop(self):
        self._stop_evt.set()
        self._running = False
        log.info('Scheduler stopped')

    def trigger_now(self):
        """Fire the callback immediately in its own thread."""
        log.info('Manual snapshot triggered')
        threading.Thread(
            target=lambda: self._safe_call(is_manual=True),
            daemon=True,
            name='SchedulerManualTrigger',
        ).start()

    # --------------------------------------------------------- internals
    def _loop(self):
        tick = 0
        while not self._stop_evt.is_set():
            tick += 1
            log.debug('Scheduler tick #%d', tick)
            self._safe_call(is_manual=False)
            # wait for next interval, but wake early on stop
            self._stop_evt.wait(self._interval)

    def _safe_call(self, is_manual: bool = False):
        try:
            try:
                self._callback(is_manual)
            except TypeError:
                self._callback()
        except Exception as exc:
            log.exception('Scheduler callback raised an exception: %s', exc)
