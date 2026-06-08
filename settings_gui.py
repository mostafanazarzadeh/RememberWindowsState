"""
RememberWindowsState — settings_gui.py
Unified settings window managing General, Blacklist, and History tabs.
"""

import tkinter as tk
from config import Config
from scheduler import WindowScheduler
from gui_tokens import BG, SURFACE, TEXT, TEXT_DIM, ACCENT, BORDER
from gui_utils import set_window_icon
from settings_gui_general import GeneralTab
from settings_gui_blacklist import BlacklistTab
from settings_gui_history import HistoryTab

_active_window = None


class SettingsWindow:
    """Unified Settings Window with tabs for General, Blacklist, and History."""

    @classmethod
    def show_window(cls, master: tk.Tk, config: Config,
                    scheduler: WindowScheduler, tab: str = "history"):
        global _active_window
        if _active_window is not None:
            try:
                if _active_window.winfo_exists():
                    _active_window.instance.select_tab(tab)
                    _active_window.deiconify()
                    _active_window.lift()
                    _active_window.focus_force()
                    return _active_window.instance
            except Exception:
                pass

        inst = cls(master, config, scheduler, initial_tab=tab)
        inst._win.instance = inst
        _active_window = inst._win
        return inst

    def __init__(self, master: tk.Tk, config: Config,
                 scheduler: WindowScheduler, initial_tab: str = "history"):
        self._master    = master
        self._config    = config
        self._scheduler = scheduler
        self._active_tab = None

        self._win = tk.Toplevel(master)
        self._win.title('RememberWindowsState')
        self._win.configure(bg=BG)
        self._win.resizable(True, True)
        self._win.protocol('WM_DELETE_WINDOW', self._win.destroy)

        W, H = 580, 680
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f'{W}x{H}+{(sw-W)//2}+{(sh-H)//2}')
        self._win.minsize(500, 550)

        set_window_icon(self._win)
        self._build()
        self.select_tab(initial_tab)

    def _build(self):
        # Accent stripe
        tk.Frame(self._win, bg=ACCENT, height=4).pack(fill='x')

        # Header
        hdr = tk.Frame(self._win, bg=SURFACE, padx=20, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text='⚙️  RememberWindowsState',
                 font=('Segoe UI', 13, 'bold'),
                 bg=SURFACE, fg=TEXT).pack(side='left')
        tk.Label(hdr, text='v1.0.0',
                 font=('Segoe UI', 9),
                 bg=SURFACE, fg=TEXT_DIM).pack(side='right')

        # Custom Tab Bar
        tab_bar = tk.Frame(self._win, bg=SURFACE, bd=0)
        tab_bar.pack(fill='x')

        tab_container = tk.Frame(tab_bar, bg=SURFACE)
        tab_container.pack(anchor='w', padx=10)

        tabs_info = [
            ("history", "📋  History"),
            ("general", "⚙️  General"),
            ("blacklist", "🚫  Blacklist")
        ]

        self._tab_btns = {}
        self._tab_indicators = {}
        self._tab_frames = {}

        for name, title in tabs_info:
            f = tk.Frame(tab_container, bg=SURFACE)
            f.pack(side='left', padx=2)

            btn = tk.Button(
                f, text=title,
                font=('Segoe UI', 9, 'bold'),
                bg=SURFACE, fg=TEXT_DIM,
                activebackground=SURFACE, activeforeground=TEXT,
                relief='flat', bd=0, cursor='hand2',
                padx=15, pady=8
            )
            btn.pack()

            ind = tk.Frame(f, bg=SURFACE, height=3)
            ind.pack(fill='x')

            self._tab_btns[name] = btn
            self._tab_indicators[name] = ind
            btn.configure(command=lambda n=name: self.select_tab(n))

        # Thin border below tab bar
        tk.Frame(self._win, bg=BORDER, height=1).pack(fill='x')

        # Main content area
        self._content_area = tk.Frame(self._win, bg=BG)
        self._content_area.pack(fill='both', expand=True)

        # Tab Frames
        self._tab_frames["general"] = tk.Frame(self._content_area, bg=BG)
        self._tab_frames["blacklist"] = tk.Frame(self._content_area, bg=BG)
        self._tab_frames["history"] = tk.Frame(self._content_area, bg=BG)

        # Instantiate modular tab classes
        self._general_tab = GeneralTab(self._tab_frames["general"], self._config, self._scheduler)
        self._blacklist_tab = BlacklistTab(self._tab_frames["blacklist"], self._config)
        self._history_tab = HistoryTab(self._tab_frames["history"], self._config, self._win)

        # Footer
        foot = tk.Frame(self._win, bg=SURFACE, padx=16, pady=8)
        foot.pack(fill='x', side='bottom')
        tk.Label(foot,
                 text=f'📁  {self._config.app_data_dir}',
                 font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM,
                 cursor='hand2').pack(side='left')

    def select_tab(self, name: str):
        if self._active_tab == name:
            return

        if self._active_tab:
            self._tab_btns[self._active_tab].configure(fg=TEXT_DIM)
            self._tab_indicators[self._active_tab].configure(bg=SURFACE)
            self._tab_frames[self._active_tab].pack_forget()

        self._tab_btns[name].configure(fg=ACCENT)
        self._tab_indicators[name].configure(bg=ACCENT)
        self._tab_frames[name].pack(fill='both', expand=True)
        self._active_tab = name

        if name == "history":
            self._history_tab.render()

    def show(self):
        try:
            self._win.deiconify()
            self._win.lift()
            self._win.focus_force()
        except Exception:
            pass
