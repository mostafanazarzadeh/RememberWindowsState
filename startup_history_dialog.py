"""
RememberWindowsState — startup_history_dialog.py

A dialog that appears after Windows startup (or any auto-launch).
It shows the recorded history so the user can pick a state to restore,
or simply close/skip without restoring anything.
"""

import os
import threading
import tkinter as tk
from datetime import datetime

from window_restorer import get_running_state_caches, get_open_explorer_paths

# ── Design tokens (match the rest of the app) ─────────────────────────────────
from gui_tokens import BG, SURFACE, SURFACE2, BTN_BG, ACCENT, ACCENT_H, TEXT, TEXT_DIM, DANGER, BORDER, SUCCESS
from gui_utils import set_window_icon


class StartupHistoryDialog:
    """
    Shows the window-state history on startup so the user can choose
    which snapshot to restore (or skip).

    Usage:
        dlg = StartupHistoryDialog(root, history_entries, config)
        dlg.show()   # blocks until user closes the window
    """

    def __init__(self, master: tk.Tk, entries: list[dict], config):
        self._master  = master
        self._entries = entries          # list of history dicts (newest first)
        self._config  = config
        self._card_vars = {}

        try:
            self._exe_to_pids, self._pids_with_visible_window = get_running_state_caches()
            self._running_explorers = get_open_explorer_paths()
        except Exception:
            self._exe_to_pids = {}
            self._pids_with_visible_window = set()
            self._running_explorers = set()

        self._win = tk.Toplevel(master)
        self._win.title('RememberWindowsState — Restore State')
        self._win.configure(bg=BG)
        self._win.resizable(True, True)
        self._win.protocol('WM_DELETE_WINDOW', self._skip)

        W, H = 620, 580
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f'{W}x{H}+{(sw-W)//2}+{(sh-H)//2}')
        self._win.minsize(480, 400)

        set_window_icon(self._win)
        self._build()
        self._win.grab_set()   # modal

    # ──────────────────────────────────────────── UI construction
    def _build(self):
        # ── Accent stripe ──────────────────────────────────────────────────
        tk.Frame(self._win, bg=ACCENT, height=4).pack(fill='x')

        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self._win, bg=SURFACE, padx=22, pady=14)
        hdr.pack(fill='x')

        tk.Label(hdr, text='🔄', font=('Segoe UI Emoji', 26),
                 bg=SURFACE, fg=ACCENT).pack(side='left', padx=(0, 14))

        txt_frame = tk.Frame(hdr, bg=SURFACE)
        txt_frame.pack(side='left', fill='x', expand=True)

        tk.Label(txt_frame, text='Restore Windows after Startup',
                 font=('Segoe UI', 13, 'bold'), bg=SURFACE, fg=TEXT
                 ).pack(anchor='w')
        tk.Label(txt_frame,
                 text='Select a state to restore, or click "Skip".',
                 font=('Segoe UI', 9), bg=SURFACE, fg=TEXT_DIM
                 ).pack(anchor='w')

        # Skip button in header
        skip_btn = tk.Button(
            hdr, text='✕  Skip',
            command=self._skip,
            bg=BTN_BG, fg=TEXT_DIM,
            font=('Segoe UI', 9), relief='flat',
            cursor='hand2', padx=14, pady=7, bd=0)
        skip_btn.pack(side='right')
        skip_btn.bind('<Enter>', lambda e: skip_btn.configure(bg='#cfcfcf', fg=TEXT))
        skip_btn.bind('<Leave>', lambda e: skip_btn.configure(bg=BTN_BG, fg=TEXT_DIM))

        # ── Sub-header ─────────────────────────────────────────────────────
        sub = tk.Frame(self._win, bg=BG, padx=22)
        sub.pack(fill='x', pady=(10, 4))

        count = len(self._entries)
        tk.Label(sub, text=f'📋  {count} saved states  (newest first)',
                 font=('Segoe UI', 9), bg=BG, fg=TEXT_DIM
                 ).pack(side='left')

        # ── Scrollable list of history cards ───────────────────────────────
        outer = tk.Frame(self._win, bg=BG)
        outer.pack(fill='both', expand=True, padx=0, pady=0)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        vsb    = tk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        inner   = tk.Frame(canvas, bg=BG)
        win_id  = canvas.create_window((0, 0), window=inner, anchor='nw')

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
        # Scope mouse wheel to this canvas only (avoid global leak)
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        canvas.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        if not self._entries:
            tk.Label(inner,
                     text='No states have been saved.',
                     font=('Segoe UI', 11), bg=BG, fg=TEXT_DIM,
                     justify='center').pack(expand=True, pady=40)
        else:
            for idx, entry in enumerate(self._entries):
                self._build_card(inner, entry, idx)

        # ── Bottom strip ───────────────────────────────────────────────────
        foot = tk.Frame(self._win, bg=SURFACE, padx=22, pady=10)
        foot.pack(fill='x', side='bottom')

        tk.Label(foot,
                 text='💡  Clicking "Restore" on any card will restore that state.',
                 font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM
                 ).pack(side='left')

    # ──────────────────────────────────────────── history card
    def _build_card(self, parent: tk.Frame, entry: dict, idx: int):
        ts_raw  = entry.get('timestamp', '')
        label   = entry.get('label', '')
        windows = entry.get('windows', [])
        total   = len(self._entries)

        try:
            dt     = datetime.fromisoformat(ts_raw)
            ts_str = dt.strftime('%Y/%m/%d  %H:%M:%S')
        except Exception:
            ts_str = ts_raw

        lbl_text = label if label else f'State #{total - idx}'
        if idx == 0:
            lbl_text = '⭐ Suggested: ' + lbl_text.replace('💻 ', '').replace(' (Auto-Saved)', '')

        # ── Card outer frame ───────────────────────────────────────────────
        card = tk.Frame(parent, bg=SURFACE, pady=0)
        card.pack(fill='x', padx=14, pady=(0, 8))

        # thin accent bar on the left (highlight suggested state with SUCCESS green)
        accent_color = SUCCESS if idx == 0 else ACCENT
        bar_width = 4 if idx == 0 else 3
        tk.Frame(card, bg=accent_color, width=bar_width).pack(side='left', fill='y')

        body = tk.Frame(card, bg=SURFACE)
        body.pack(side='left', fill='both', expand=True)

        # ── Header row (label + timestamp) ────────────────────────────────
        hdr = tk.Frame(body, bg=SURFACE, cursor='hand2')
        hdr.pack(fill='x', padx=10, pady=(10, 4))

        arrow_var = tk.StringVar(value='▶')
        arrow_lbl = tk.Label(hdr, textvariable=arrow_var,
                             font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM,
                             cursor='hand2')
        arrow_lbl.pack(side='left', padx=(0, 6))

        tk.Label(hdr, text=lbl_text,
                 font=('Segoe UI', 10, 'bold'), bg=SURFACE, fg=TEXT,
                 anchor='w', cursor='hand2'
                 ).pack(side='left', fill='x', expand=True)

        hdr_restore_btn = tk.Button(
            hdr, text='⚡ Restore',
            bg=ACCENT, fg='white',
            font=('Segoe UI', 8, 'bold'), relief='flat',
            cursor='hand2', padx=8, pady=3, bd=0)
        hdr_restore_btn.pack(side='right', padx=(10, 0))
        hdr_restore_btn.bind('<Enter>', lambda e: hdr_restore_btn.configure(bg=ACCENT_H))
        hdr_restore_btn.bind('<Leave>', lambda e: hdr_restore_btn.configure(bg=ACCENT))

        tk.Label(hdr, text=ts_str,
                 font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM,
                 cursor='hand2'
                 ).pack(side='right')

        # app count badge
        badge_txt = f'{len(windows)} apps'
        badge_lbl = tk.Label(body,
                 text=badge_txt,
                 font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM,
                 anchor='w'
                 )
        badge_lbl.pack(fill='x', padx=16, pady=(0, 4))

        # ── Collapsible detail panel ───────────────────────────────────────
        detail = tk.Frame(body, bg=SURFACE2)

        # We need to track the checkbox variables for this card
        self._card_vars[idx] = []
        _populated = [False]

        def _populate_detail():
            if windows:
                # Select/Deselect buttons row
                sel_row = tk.Frame(detail, bg=SURFACE2)
                sel_row.pack(fill='x', padx=16, pady=(6, 2))

                def _select_all(card_idx=idx):
                    for var in self._card_vars[card_idx]:
                        var.set(True)

                def _deselect_all(card_idx=idx):
                    for var in self._card_vars[card_idx]:
                        var.set(False)

                btn_sel = tk.Button(sel_row, text='Select All', command=_select_all,
                                    bg=SURFACE2, fg=ACCENT, activebackground=SURFACE2, activeforeground=ACCENT_H,
                                    font=('Segoe UI', 8, 'underline'), relief='flat', cursor='hand2', bd=0, padx=2, pady=0)
                btn_sel.pack(side='left')

                tk.Label(sel_row, text='|', font=('Segoe UI', 8), bg=SURFACE2, fg=BORDER).pack(side='left', padx=4)

                btn_desel = tk.Button(sel_row, text='Deselect All', command=_deselect_all,
                                      bg=SURFACE2, fg=ACCENT, activebackground=SURFACE2, activeforeground=ACCENT_H,
                                      font=('Segoe UI', 8, 'underline'), relief='flat', cursor='hand2', bd=0, padx=2, pady=0)
                btn_desel.pack(side='left')

                # app list inside detail
                list_frame = tk.Frame(detail, bg=SURFACE2)
                list_frame.pack(fill='x', padx=14, pady=(4, 4))

                for w in windows:
                    app   = os.path.splitext(w.get('exe_name', '?'))[0].title()
                    title = w.get('title', '')
                    if w.get('exe_name', '').lower() == 'explorer.exe' and 'explorer_path' in w:
                        app = "File Explorer"
                        title = w['explorer_path']
                    if len(title) > 55:
                        title = title[:52] + '…'

                    # Determine running state
                    exe_path = w.get('exe_path', '').lower()
                    exe_name = w.get('exe_name', '').lower()
                    is_running = False
                    if exe_name == 'explorer.exe' and 'explorer_path' in w:
                        if w['explorer_path'].lower() in self._running_explorers:
                            is_running = True
                    else:
                        from window_restorer import is_app_running_cached
                        if is_app_running_cached(exe_path, w.get('state', 'normal'), self._exe_to_pids, self._pids_with_visible_window):
                            is_running = True

                    var = tk.BooleanVar(value=not is_running)
                    self._card_vars[idx].append(var)

                    row = tk.Frame(list_frame, bg=SURFACE2)
                    row.pack(fill='x', pady=2)

                    cb = tk.Checkbutton(row, variable=var,
                                        bg=SURFACE2, activebackground=SURFACE2,
                                        selectcolor=SURFACE, fg=ACCENT,
                                        highlightthickness=0, bd=0,
                                        cursor='hand2')
                    cb.pack(side='left', padx=(2, 6))

                    lbl_text_app = f'{app}  —  {title}'
                    if is_running:
                        lbl_text_app += ' (Running)'

                    lbl = tk.Label(row, text=lbl_text_app,
                                   font=('Segoe UI', 9), bg=SURFACE2,
                                   fg=TEXT_DIM if is_running else TEXT, anchor='w')
                    lbl.pack(side='left')

                    # Bind clicking on the label to toggle the checkbox
                    def _toggle_cb(e, v=var):
                        v.set(not v.get())
                    lbl.bind('<Button-1>', _toggle_cb)

                # Restore button inside detail
                rest_btn = tk.Button(
                    detail,
                    text='⏪  Restore selected',
                    command=lambda card_idx=idx, wins=windows: self._do_restore_selected(card_idx, wins),
                    bg=ACCENT, fg='white',
                    font=('Segoe UI', 9, 'bold'), relief='flat',
                    cursor='hand2', padx=16, pady=8, bd=0)
                rest_btn.pack(anchor='e', padx=14, pady=(4, 12))
                rest_btn.bind('<Enter>', lambda e: rest_btn.configure(bg=ACCENT_H))
                rest_btn.bind('<Leave>', lambda e: rest_btn.configure(bg=ACCENT))

        # ── Toggle collapse ────────────────────────────────────────────────
        _expanded = [False]

        def _toggle(e=None):
            new_bg = SURFACE if _expanded[0] else SURFACE2
            card.configure(bg=new_bg)
            body.configure(bg=new_bg)
            hdr.configure(bg=new_bg)
            for widget in hdr.winfo_children():
                try:
                    if widget != hdr_restore_btn:
                        widget.configure(bg=new_bg)
                except Exception:
                    pass
            try:
                badge_lbl.configure(bg=new_bg)
            except Exception:
                pass

            if _expanded[0]:
                detail.pack_forget()
                arrow_var.set('▶')
                _expanded[0] = False
            else:
                if not _populated[0]:
                    _populate_detail()
                    _populated[0] = True
                detail.pack(fill='x')
                arrow_var.set('▼')
                _expanded[0] = True

        for widget in (hdr, arrow_lbl) + tuple(hdr.winfo_children()):
            if widget == hdr_restore_btn:
                continue
            widget.bind('<Button-1>', _toggle)
        hdr.bind('<Button-1>', _toggle)

        # Quick restore action
        def _quick_restore():
            if not _populated[0]:
                _populate_detail()
                _populated[0] = True
            self._do_restore_selected(idx, windows)

        hdr_restore_btn.configure(command=_quick_restore)

        if idx == 0:
            _toggle()

    # ──────────────────────────────────────────── actions
    def _do_restore_selected(self, card_idx: int, windows: list):
        """Restore only the checked applications for this history card."""
        from window_restorer import restore_windows
        from tkinter import messagebox

        selected_windows = []
        vars_list = self._card_vars.get(card_idx, [])
        for w, var in zip(windows, vars_list):
            if var.get():
                selected_windows.append(w)

        if not selected_windows:
            messagebox.showinfo(
                'RememberWindowsState',
                'No applications selected to restore!',
                parent=self._win)
            return

        # Restore the selected windows in a background thread
        threading.Thread(
            target=lambda: restore_windows(selected_windows),
            daemon=True).start()
        # Close startup dialog after restoring
        self._close()

    def _skip(self):
        self._close()

    def _close(self):
        try:
            self._win.grab_release()
            self._win.destroy()
        except Exception:
            pass

    def show(self):
        """Block the calling thread until the dialog is closed."""
        self._master.wait_window(self._win)
