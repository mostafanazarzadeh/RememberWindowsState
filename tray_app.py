"""
RememberWindowsState — tray_app.py
System-tray icon using pystray.  Runs in a daemon thread while tkinter
lives on the main thread.  UI operations are dispatched via ui_queue.

Left-click on the tray icon → opens the History window.
Right-click menu → History | Settings | Blacklist | Save Now | Restore | Quit
"""

import os
import queue
import threading

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item, Menu

from app_logger import get_logger

log = get_logger(__name__)


# ── Icon helpers ──────────────────────────────────────────────────────────────
def _load_or_draw_icon() -> Image.Image:
    """Load assets/icon.png, or draw a fallback icon programmatically."""
    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'assets', 'icon.png')

    if os.path.exists(icon_path):
        return Image.open(icon_path).convert('RGBA').resize((64, 64))

    # Fallback: draw a simple purple icon with a clock hand
    img  = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill='#7c6af7')
    draw.rectangle([14, 20, 50, 46], outline='white', width=3)
    draw.line([32, 24, 32, 33], fill='white', width=3)
    draw.line([32, 33, 42, 33], fill='white', width=3)
    return img


def _fmt(seconds: int) -> str:
    return f'{seconds}s' if seconds < 60 else f'{seconds // 60}m'


# ── TrayApp ───────────────────────────────────────────────────────────────────
class TrayApp:
    """
    Wraps a pystray.Icon.  Should be started in a daemon thread via .run().
    All tkinter UI operations are submitted through ui_queue so they execute
    on the main thread.

    Left-click on the icon → History window.
    Right-click menu items:
        📋 History | ⚙️ Settings | 🚫 Blacklist
        ──────────
        💾 Save Now | 🔄 Restore Windows…
        ──────────
        ❌ Quit
    """

    def __init__(self, config, scheduler, ui_queue: queue.Queue, root=None):
        self._config    = config
        self._scheduler = scheduler
        self._queue     = ui_queue
        self._root      = root          # main tkinter root (main thread)
        self._icon: pystray.Icon | None = None

    # ─────────────────────────────────────────────── public
    def run(self):
        img = _load_or_draw_icon()
        self._icon = pystray.Icon(
            'RememberWindowsState',
            img,
            'RememberWindowsState',
            menu=self._make_menu(),
        )
        # Left-click on tray icon opens History
        self._icon.default_action = self._on_history
        self._icon.run()

    def stop(self):
        if self._icon:
            self._icon.stop()

    # ─────────────────────────────────────────────── menu
    def _make_menu(self) -> Menu:
        return Menu(
            item('RememberWindowsState', None, enabled=False),
            Menu.SEPARATOR,
            item('📋  History',              self._on_history, default=True),
            item('⚙️  Settings',             self._on_settings),
            item('🚫  Blacklist',            self._on_blacklist),
            Menu.SEPARATOR,
            item(self._interval_label, None, enabled=False),
            item('💾  Save Now',             self._on_save),
            item('🔄  Restore Windows…',    self._on_restore),
            Menu.SEPARATOR,
            item('❌  Quit',                 self._on_quit),
        )

    def _interval_label(self, _item) -> str:
        return f'⏱  Every  {_fmt(self._config.interval)}'

    # ─────────────────────────────────────────────── callbacks (tray thread)
    def _on_history(self, *_):
        log.info('Tray → History clicked')
        self._queue.put(self._ui_history)

    def _on_settings(self, *_):
        log.info('Tray → Settings clicked')
        self._queue.put(self._ui_settings)

    def _on_blacklist(self, *_):
        log.info('Tray → Blacklist clicked')
        self._queue.put(self._ui_blacklist)

    def _on_save(self, *_):
        log.info('Tray → Save Now clicked')
        self._scheduler.trigger_now()

    def _on_restore(self, *_):
        log.info('Tray → Restore Windows clicked')
        self._queue.put(self._ui_restore)

    def _on_quit(self, *_):
        log.info('Tray → Quit clicked')
        self._queue.put(self._ui_quit)

    # ─────────────────────────────────────────────── UI tasks (main thread)
    def _ui_history(self):
        """Open the History window on the main thread."""
        from settings_gui import SettingsWindow
        SettingsWindow.show_window(self._root, self._config, self._scheduler, tab="history")

    def _ui_settings(self):
        """Open Settings window on the main thread."""
        from settings_gui import SettingsWindow
        SettingsWindow.show_window(self._root, self._config, self._scheduler, tab="general")

    def _ui_blacklist(self):
        """Open Blacklist window on the main thread."""
        from settings_gui import SettingsWindow
        SettingsWindow.show_window(self._root, self._config, self._scheduler, tab="blacklist")

    def _ui_restore(self):
        """Show restore dialog on the main thread."""
        from window_tracker   import load_snapshot
        from window_restorer  import filter_not_open, restore_windows
        from restore_dialog   import RestoreDialog
        from tkinter import messagebox

        root = self._root

        if hasattr(self, '_active_restore_win') and self._active_restore_win is not None:
            try:
                if self._active_restore_win.winfo_exists():
                    self._active_restore_win.deiconify()
                    self._active_restore_win.lift()
                    self._active_restore_win.focus_force()
                    return
            except Exception:
                pass

        snapshot = load_snapshot(self._config.state_file)
        if not snapshot or not snapshot.get('windows'):
            messagebox.showinfo(
                'RememberWindowsState',
                'No windows have been saved yet.',
                parent=root)
            return

        not_open = filter_not_open(snapshot['windows'])
        if not not_open:
            messagebox.showinfo(
                'RememberWindowsState',
                'All saved applications are already running!',
                parent=root)
            return

        dlg = RestoreDialog(root, snapshot, not_open, self._config)
        self._active_restore_win = dlg._win
        selected = dlg.show()
        self._active_restore_win = None

        if selected:
            threading.Thread(
                target=lambda: restore_windows(selected),
                daemon=True).start()

    def _ui_quit(self):
        import os
        log.info('Application shutting down — saving final state then exiting')
        # Stop background tasks first so they don't overwrite our final save
        try:
            self._scheduler.stop()
        except Exception:
            pass
        # Save a final snapshot so the quit-time state is available on next launch
        try:
            from window_tracker import get_open_windows, save_snapshot, save_to_history
            windows = get_open_windows(
                blacklist=self._config.blacklist,
                track_explorer=self._config.track_explorer,
            )
            save_snapshot(windows, self._config.state_file)
            save_to_history(
                windows, self._config.state_file,
                label='\u274c Quit',
                limit=self._config.history_limit,
            )
            log.info('Final state saved on quit \u2014 %d window(s)', len(windows))
        except Exception as exc:
            log.exception('Final state save on quit failed: %s', exc)
        os._exit(0)
