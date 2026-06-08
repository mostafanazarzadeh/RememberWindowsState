"""
RememberWindowsState — settings_gui_general.py
General settings tab class.
"""

import tkinter as tk
from tkinter import messagebox
from config import Config
from scheduler import WindowScheduler
from startup import enable_startup, disable_startup, is_startup_enabled
from window_tracker import trim_history
from gui_tokens import BG, SURFACE, BTN_BG, ACCENT, ACCENT_H, TEXT, TEXT_DIM, BORDER
from gui_utils import draw_section_header


def _fmt_interval(seconds: int) -> str:
    if seconds < 60:
        return f'{seconds} sec'
    m, s = divmod(seconds, 60)
    return f'{m} min{" " + str(s) + " sec" if s else ""}'


class GeneralTab:
    """General Tab for adjusting save interval, history limits, startup, and explorer tracking."""

    def __init__(self, parent_frame: tk.Frame, config: Config, scheduler: WindowScheduler):
        self._parent = parent_frame
        self._config = config
        self._scheduler = scheduler
        self._build()

    def _build(self):
        # Add internal padding
        inner = tk.Frame(self._parent, bg=BG, padx=22, pady=18)
        inner.pack(fill='both', expand=True)

        # Section: interval
        draw_section_header(inner, '⏱  Save Interval', BG, ACCENT, BORDER)

        self._interval_label = tk.Label(
            inner, text=_fmt_interval(self._config.interval),
            font=('Segoe UI', 24, 'bold'), bg=BG, fg=ACCENT)
        self._interval_label.pack(pady=(6, 2))

        self._iv = tk.IntVar(value=self._config.interval)
        slider = tk.Scale(
            inner, variable=self._iv, from_=10, to=1800,
            orient='horizontal', bg=BG, fg=TEXT,
            troughcolor=SURFACE, activebackground=ACCENT,
            highlightthickness=0, sliderrelief='flat',
            sliderlength=18, bd=0, showvalue=False, length=460,
            command=self._on_interval)
        slider.pack(fill='x', pady=(0, 4))

        # Preset buttons
        presets_row = tk.Frame(inner, bg=BG)
        presets_row.pack(pady=(2, 14))
        for lbl, val in [('10s', 10), ('30s', 30),
                         ('1m', 60), ('5m', 300), ('30m', 1800)]:
            b = tk.Button(presets_row, text=lbl,
                          command=lambda v=val: self._set_preset(v),
                          bg=BTN_BG, fg=TEXT_DIM,
                          font=('Segoe UI', 8), relief='flat',
                          cursor='hand2', padx=10, pady=3, bd=0)
            b.pack(side='left', padx=2)
            b.bind('<Enter>', lambda e, btn=b: btn.configure(bg='#cfcfcf', fg=TEXT))
            b.bind('<Leave>', lambda e, btn=b: btn.configure(bg=BTN_BG, fg=TEXT_DIM))

        # Section: history limit
        draw_section_header(inner, '📜  History Limit', BG, ACCENT, BORDER)

        self._limit_label = tk.Label(
            inner, text=f'{self._config.history_limit} states',
            font=('Segoe UI', 24, 'bold'), bg=BG, fg=ACCENT)
        self._limit_label.pack(pady=(6, 2))

        self._lv = tk.IntVar(value=self._config.history_limit)
        limit_slider = tk.Scale(
            inner, variable=self._lv, from_=10, to=300,
            orient='horizontal', bg=BG, fg=TEXT,
            troughcolor=SURFACE, activebackground=ACCENT,
            highlightthickness=0, sliderrelief='flat',
            sliderlength=18, bd=0, showvalue=False, length=460,
            command=self._on_history_limit)
        limit_slider.pack(fill='x', pady=(0, 4))

        # Preset buttons for history limit
        limit_presets_row = tk.Frame(inner, bg=BG)
        limit_presets_row.pack(pady=(2, 14))
        for lbl, val in [('50', 50), ('100', 100), ('150', 150), ('200', 200), ('300', 300)]:
            b = tk.Button(limit_presets_row, text=lbl,
                          command=lambda v=val: self._set_limit_preset(v),
                          bg=BTN_BG, fg=TEXT_DIM,
                          font=('Segoe UI', 8), relief='flat',
                          cursor='hand2', padx=10, pady=3, bd=0)
            b.pack(side='left', padx=2)
            b.bind('<Enter>', lambda e, btn=b: btn.configure(bg='#cfcfcf', fg=TEXT))
            b.bind('<Leave>', lambda e, btn=b: btn.configure(bg=BTN_BG, fg=TEXT_DIM))

        # Section: startup
        draw_section_header(inner, '🚀  Run with Windows', BG, ACCENT, BORDER)

        card = tk.Frame(inner, bg=SURFACE, padx=14, pady=12)
        card.pack(fill='x', pady=(0, 6))

        tk.Label(card, text='Run automatically at Windows startup',
                 font=('Segoe UI', 10), bg=SURFACE, fg=TEXT
                 ).pack(side='left')

        self._startup_var = tk.BooleanVar(value=is_startup_enabled())
        chk = tk.Checkbutton(
            card, variable=self._startup_var,
            command=self._on_startup,
            bg=SURFACE, activebackground=SURFACE,
            selectcolor=SURFACE, fg=ACCENT,
            highlightthickness=0, cursor='hand2', relief='flat')
        chk.pack(side='right')

        tk.Label(inner,
                 text=('If this option is disabled and you launch the app manually,\n'
                       'the list of saved windows will be shown.'),
                 font=('Segoe UI', 8), bg=BG, fg=TEXT_DIM,
                 justify='left').pack(anchor='w', pady=(0, 10))

        # Section: Explorer
        draw_section_header(inner, '📁  Windows Explorer', BG, ACCENT, BORDER)

        card_exp = tk.Frame(inner, bg=SURFACE, padx=14, pady=12)
        card_exp.pack(fill='x', pady=(0, 6))

        tk.Label(card_exp, text='Track and restore Windows Explorer folders',
                 font=('Segoe UI', 10), bg=SURFACE, fg=TEXT
                 ).pack(side='left')

        self._track_exp_var = tk.BooleanVar(value=self._config.track_explorer)
        chk_exp = tk.Checkbutton(
            card_exp, variable=self._track_exp_var,
            command=self._on_track_explorer,
            bg=SURFACE, activebackground=SURFACE,
            selectcolor=SURFACE, fg=ACCENT,
            highlightthickness=0, cursor='hand2', relief='flat')
        chk_exp.pack(side='right')

        tk.Frame(inner, bg=BG, height=8).pack()  # small space

        # Save-now button
        save_btn = tk.Button(
            inner, text='💾  Save Now',
            command=self._save_now,
            bg=ACCENT, fg='white',
            font=('Segoe UI', 10, 'bold'), relief='flat',
            cursor='hand2', padx=22, pady=10, bd=0)
        save_btn.pack()
        save_btn.bind('<Enter>',
                      lambda e: save_btn.configure(bg=ACCENT_H))
        save_btn.bind('<Leave>',
                      lambda e: save_btn.configure(bg=ACCENT))

    def _on_interval(self, val):
        v = int(val)
        self._interval_label.configure(text=_fmt_interval(v))
        self._config.interval = v
        self._scheduler.interval = v

    def _set_preset(self, val: int):
        self._iv.set(val)
        self._on_interval(val)

    def _on_history_limit(self, val):
        v = int(val)
        self._limit_label.configure(text=f'{v} states')
        self._config.history_limit = v
        trim_history(self._config.state_file, v)

    def _set_limit_preset(self, val: int):
        self._lv.set(val)
        self._on_history_limit(val)

    def _on_startup(self):
        if self._startup_var.get():
            if not enable_startup():
                messagebox.showerror('Error', 'Failed to enable run at Windows startup.')
                self._startup_var.set(False)
        else:
            disable_startup()
        self._config.startup_with_windows = self._startup_var.get()

    def _on_track_explorer(self):
        self._config.track_explorer = self._track_exp_var.get()

    def _save_now(self):
        self._scheduler.trigger_now()
        messagebox.showinfo('RememberWindowsState', '✅ Windows saved successfully!')
