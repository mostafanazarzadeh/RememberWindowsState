"""
RememberWindowsState — settings_gui_general.py
General settings tab class.
"""

import threading
import tkinter as tk
from tkinter import messagebox
from config import Config
from scheduler import WindowScheduler
from startup import enable_startup, disable_startup, is_startup_enabled
from window_tracker import trim_history
from gui_tokens import BG, SURFACE, BTN_BG, ACCENT, ACCENT_H, TEXT, TEXT_DIM, BORDER, DANGER, SUCCESS
from gui_utils import draw_section_header
from updater import APP_VERSION, check_for_updates, open_release_page



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
        # ── Scrollable canvas scaffold ─────────────────────────────────
        outer = tk.Frame(self._parent, bg=BG)
        outer.pack(fill='both', expand=True, padx=0, pady=0)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        inner = tk.Frame(canvas, bg=BG, padx=22, pady=18)
        win_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind('<Configure>', _on_resize)

        def _on_frame_resize(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
        inner.bind('<Configure>', _on_frame_resize)

        def _on_wheel(e):
            try:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
            except Exception:
                pass
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        canvas.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

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

        # Section: Updates
        draw_section_header(inner, '🔄  Software Updates', BG, ACCENT, BORDER)

        card_upd = tk.Frame(inner, bg=SURFACE, padx=14, pady=12)
        card_upd.pack(fill='x', pady=(0, 6))

        info_frame = tk.Frame(card_upd, bg=SURFACE)
        info_frame.pack(side='left', fill='x', expand=True)

        tk.Label(info_frame, text=f'Current Version: v{APP_VERSION}',
                 font=('Segoe UI', 10, 'bold'), bg=SURFACE, fg=TEXT
                 ).pack(anchor='w')

        self._update_status_label = tk.Label(
            info_frame, text='Check for available application updates.',
            font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM
        )
        self._update_status_label.pack(anchor='w', pady=(2, 0))

        self._update_btn = tk.Button(
            card_upd, text='Check for Updates',
            command=self._on_check_update,
            bg=BTN_BG, fg=TEXT,
            font=('Segoe UI', 9), relief='flat',
            cursor='hand2', padx=12, pady=5, bd=0
        )
        self._update_btn.pack(side='right')
        self._update_btn.bind('<Enter>', lambda e: self._on_update_btn_hover(True))
        self._update_btn.bind('<Leave>', lambda e: self._on_update_btn_hover(False))

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

    def _on_update_btn_hover(self, entering: bool):
        if self._update_btn.cget('state') == 'disabled':
            return
        if self._update_btn.cget('bg') in (ACCENT, ACCENT_H):
            self._update_btn.configure(bg=ACCENT_H if entering else ACCENT)
        else:
            self._update_btn.configure(bg='#cfcfcf' if entering else BTN_BG)

    def _on_check_update(self):
        self._update_btn.configure(state='disabled', text='Checking...', bg=BTN_BG)
        self._update_status_label.configure(text='Connecting to GitHub...', fg=TEXT_DIM)
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _check_update_thread(self):
        res = check_for_updates(APP_VERSION)
        self._parent.after(0, lambda: self._update_check_finished(res))

    def _update_check_finished(self, res: dict):
        self._update_btn.configure(state='normal')
        if res.get('error'):
            self._update_btn.configure(text='Check for Updates', bg=BTN_BG)
            self._update_status_label.configure(
                text=f'⚠️ Could not check for updates ({res["error"]})',
                fg=DANGER
            )
        elif res.get('has_update'):
            latest = res.get('latest_version', '')
            url = res.get('release_url', '')
            self._update_status_label.configure(
                text=f'🎉 New version available: v{latest}!',
                fg=ACCENT
            )
            self._update_btn.configure(
                text=f'⬇️ Get v{latest}',
                command=lambda: open_release_page(url),
                bg=ACCENT, fg='white'
            )
        else:
            self._update_btn.configure(text='Check for Updates', bg=BTN_BG)
            self._update_status_label.configure(
                text=f'✅ You are using the latest version (v{APP_VERSION}).',
                fg=SUCCESS
            )

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

