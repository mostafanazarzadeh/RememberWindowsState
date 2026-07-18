"""
RememberWindowsState — settings_gui_history.py
History settings tab class.
"""

import os
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from config import Config
from gui_tokens import BG, SURFACE, SURFACE2, BTN_BG, ACCENT, ACCENT_H, TEXT, TEXT_DIM, BORDER, DANGER
from window_tracker import load_history, load_snapshot, get_window_exe_set
from window_restorer import get_running_state_caches, get_open_explorer_paths, restore_windows, is_app_running_cached


class HistoryTab:
    """History Tab for viewing, selecting, and restoring window state history."""

    def __init__(self, parent_frame: tk.Frame, config: Config, win: tk.Toplevel):
        self._parent = parent_frame
        self._config = config
        self._win = win

    def render(self):
        parent = self._parent
        for w in parent.winfo_children():
            w.destroy()

        entries = load_history(self._config.state_file)
        latest_snap = load_snapshot(self._config.state_file)

        if latest_snap and latest_snap.get('windows'):
            latest_entry = {
                'timestamp': latest_snap.get('timestamp', ''),
                'label': '💻 Last Session (Auto-Saved)',
                'windows': latest_snap.get('windows', []),
            }

            if entries:
                set_snap = get_window_exe_set(latest_entry['windows'])
                set_hist = get_window_exe_set(entries[-1].get('windows', []))
                if set_snap == set_hist:
                    entries[-1]['label'] = '💻 Last Session (Auto-Saved)'
                else:
                    entries.append(latest_entry)
            else:
                entries.append(latest_entry)

        # ── outer scaffold ─────────────────────────────────────────────────────
        header_row = tk.Frame(parent, bg=BG, padx=22)
        header_row.pack(fill='x', pady=(14, 4))

        tk.Label(header_row, text='📋  History Logs',
                 font=('Segoe UI', 11, 'bold'), bg=BG, fg=ACCENT
                 ).pack(side='left')

        ref_btn = tk.Button(
            header_row, text='🔄 Reload',
            command=self.render,
            bg=BTN_BG, fg=TEXT_DIM, font=('Segoe UI', 8),
            relief='flat', cursor='hand2', padx=10, pady=4, bd=0)
        ref_btn.pack(side='right')
        ref_btn.bind('<Enter>', lambda e: ref_btn.configure(bg='#cfcfcf', fg=TEXT))
        ref_btn.bind('<Leave>', lambda e: ref_btn.configure(bg=BTN_BG, fg=TEXT_DIM))

        if not entries:
            tk.Label(parent,
                     text='No changes have been recorded yet.\n'
                          'Open or close applications to start recording history.',
                     font=('Segoe UI', 10), bg=BG, fg=TEXT_DIM,
                     justify='center'
                     ).pack(expand=True)
            return

        tk.Label(header_row,
                 text=f'{len(entries)} recorded states',
                 font=('Segoe UI', 8), bg=BG, fg=TEXT_DIM
                 ).pack(side='right', padx=(0, 10))

        # ── scrollable canvas for entry cards ─────────────────────────────────
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill='both', expand=True, padx=0, pady=0)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        inner = tk.Frame(canvas, bg=BG)
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
        # Scope mouse wheel to this canvas only (avoid global leak)
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        canvas.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # Fetch running state once for all cards
        try:
            exe_to_pids, pids_with_visible_window = get_running_state_caches()
            running_explorers = get_open_explorer_paths()
        except Exception:
            exe_to_pids = {}
            pids_with_visible_window = set()
            running_explorers = set()

        # Store card checkbox vars keyed by card index
        card_vars: dict[int, list[tk.BooleanVar]] = {}

        # ── build entry cards (newest first) ──────────────────────────────────
        for idx, entry in enumerate(reversed(entries)):
            self._build_history_card(inner, entry, idx, len(entries),
                                     exe_to_pids, pids_with_visible_window, running_explorers, card_vars)

    def _build_history_card(self, parent, entry: dict, idx: int, total: int,
                             exe_to_pids: dict, pids_with_visible_window: set, running_explorers: set,
                             card_vars: dict):
        """Build one collapsible history card inside *parent*."""
        ts_raw  = entry.get('timestamp', '')
        label   = entry.get('label', '')
        windows = entry.get('windows', [])

        try:
            dt     = datetime.fromisoformat(ts_raw)
            ts_str = dt.strftime('%Y/%m/%d  %H:%M:%S')
        except Exception:
            ts_str = ts_raw

        # card container
        card = tk.Frame(parent, bg=SURFACE, pady=0)
        card.pack(fill='x', padx=14, pady=(0, 6))

        # thin accent bar on left
        tk.Frame(card, bg=ACCENT, width=3).pack(side='left', fill='y')

        body = tk.Frame(card, bg=SURFACE)
        body.pack(side='left', fill='both', expand=True)

        # ── header row (always visible, clickable) ─────────────────────────
        hdr = tk.Frame(body, bg=SURFACE, cursor='hand2')
        hdr.pack(fill='x', padx=10, pady=8)

        arrow_var = tk.StringVar(value='▶')
        arrow_lbl = tk.Label(hdr, textvariable=arrow_var,
                             font=('Segoe UI', 8), bg=SURFACE, fg=TEXT_DIM,
                             cursor='hand2')
        arrow_lbl.pack(side='left', padx=(0, 6))

        lbl_text = label if label else f'State #{total - idx}'
        tk.Label(hdr, text=lbl_text,
                 font=('Segoe UI', 9, 'bold'), bg=SURFACE, fg=TEXT,
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

        # ── detail panel (hidden by default) ───────────────────────────────
        detail = tk.Frame(body, bg=SURFACE2)

        # Initialise checkbox var list for this card
        card_vars[idx] = []
        _populated = [False]

        def _populate_detail():
            if windows:
                # ── Select / Deselect All row ───────────────────────────────────
                sel_row = tk.Frame(detail, bg=SURFACE2)
                sel_row.pack(fill='x', padx=16, pady=(6, 2))

                def _select_all(ci=idx):
                    for v in card_vars[ci]:
                        v.set(True)

                def _deselect_all(ci=idx):
                    for v in card_vars[ci]:
                        v.set(False)

                btn_sel = tk.Button(
                    sel_row, text='Select All', command=_select_all,
                    bg=SURFACE2, fg=ACCENT, activebackground=SURFACE2, activeforeground=ACCENT_H,
                    font=('Segoe UI', 8, 'underline'), relief='flat',
                    cursor='hand2', bd=0, padx=2, pady=0)
                btn_sel.pack(side='left')

                tk.Label(sel_row, text='|', font=('Segoe UI', 8),
                         bg=SURFACE2, fg=BORDER).pack(side='left', padx=4)

                btn_desel = tk.Button(
                    sel_row, text='Deselect All', command=_deselect_all,
                    bg=SURFACE2, fg=ACCENT, activebackground=SURFACE2, activeforeground=ACCENT_H,
                    font=('Segoe UI', 8, 'underline'), relief='flat',
                    cursor='hand2', bd=0, padx=2, pady=0)
                btn_desel.pack(side='left')

                # ── App list with checkboxes ────────────────────────────────────────
                list_frame = tk.Frame(detail, bg=SURFACE2)
                list_frame.pack(fill='x', padx=10, pady=(4, 6))

                for w in windows:
                    app   = os.path.splitext(w.get('exe_name', '?'))[0].title()
                    title = w.get('title', '')
                    if w.get('exe_name', '').lower() == 'explorer.exe' and 'explorer_path' in w:
                        app = "File Explorer"
                        title = w['explorer_path']
                    if len(title) > 52:
                        title = title[:49] + '…'

                    # Determine running state
                    exe_path = w.get('exe_path', '').lower()
                    exe_name_l = w.get('exe_name', '').lower()
                    is_running = False
                    if exe_name_l == 'explorer.exe' and 'explorer_path' in w:
                        if w['explorer_path'].lower() in running_explorers:
                            is_running = True
                    else:
                        if is_app_running_cached(exe_path, w.get('state', 'normal'), exe_to_pids, pids_with_visible_window):
                            is_running = True

                    v = tk.BooleanVar(value=not is_running)
                    card_vars[idx].append(v)

                    row = tk.Frame(list_frame, bg=SURFACE2)
                    row.pack(fill='x', pady=2)

                    cb = tk.Checkbutton(
                        row, variable=v,
                        bg=SURFACE2, activebackground=SURFACE2,
                        selectcolor=SURFACE, fg=ACCENT,
                        highlightthickness=0, bd=0,
                        cursor='hand2')
                    cb.pack(side='left', padx=(2, 6))

                    lbl_text_app = f'{app}  —  {title}'
                    if is_running:
                        lbl_text_app += ' (Running)'

                    row_lbl = tk.Label(
                        row, text=lbl_text_app,
                        font=('Segoe UI', 9), bg=SURFACE2,
                        fg=TEXT_DIM if is_running else TEXT, anchor='w')
                    row_lbl.pack(side='left')

                    # Bind clicking on the label to toggle the checkbox
                    def _toggle_cb(e, var_to_toggle=v):
                        var_to_toggle.set(not var_to_toggle.get())
                    row_lbl.bind('<Button-1>', _toggle_cb)

                    # Blacklist button on the right
                    if self._config:
                        def _blacklist_row(win_entry=w, r=row, var=v, w_list=windows, card_idx=idx):
                            exe_name = win_entry.get('exe_name', '')
                            if not exe_name:
                                return
                            from tkinter import messagebox
                            if messagebox.askyesno('RememberWindowsState', 
                                                   f"Are you sure you want to add '{exe_name}' to the blacklist?\n"
                                                   f"It will no longer be tracked or restored.", parent=self._win):
                                bl = self._config.blacklist
                                if not any(b.lower() == exe_name.lower() for b in bl):
                                    bl.append(exe_name)
                                    self._config.blacklist = bl
                                if var in card_vars[card_idx]:
                                    card_vars[card_idx].remove(var)
                                if win_entry in w_list:
                                    w_list.remove(win_entry)
                                r.destroy()

                        bl_btn = tk.Button(row, text='🚫', bg=SURFACE2, fg=DANGER,
                                           font=('Segoe UI Emoji', 9), relief='flat',
                                           cursor='hand2', padx=6, pady=2, bd=0)
                        bl_btn.pack(side='right', padx=(6, 0))
                        bl_btn.configure(command=_blacklist_row)

                        bl_btn.bind('<Enter>', lambda e, b=bl_btn: b.configure(bg='#ffe5e5', fg=DANGER))
                        bl_btn.bind('<Leave>', lambda e, b=bl_btn: b.configure(bg=SURFACE2, fg=DANGER))

                # ── Restore button ──────────────────────────────────────────────────
                rest_btn = tk.Button(
                    detail,
                    text='⏪  Restore selected',
                    command=lambda ci=idx, wins=windows: self._restore_selected(ci, wins, card_vars),
                    bg=ACCENT, fg='white',
                    font=('Segoe UI', 9, 'bold'), relief='flat',
                    cursor='hand2', padx=16, pady=7, bd=0)
                rest_btn.pack(anchor='e', padx=10, pady=(0, 10))
                rest_btn.bind('<Enter>', lambda e: rest_btn.configure(bg=ACCENT_H))
                rest_btn.bind('<Leave>', lambda e: rest_btn.configure(bg=ACCENT))

        # ── toggle logic ────────────────────────────────────────────────────
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
            self._restore_selected(idx, windows, card_vars)

        hdr_restore_btn.configure(command=_quick_restore)

    def _restore_selected(self, card_idx: int, windows: list, card_vars: dict):
        """Restore only the checked applications for this history card."""
        selected = [
            w for w, v in zip(windows, card_vars.get(card_idx, []))
            if v.get()
        ]
        if not selected:
            messagebox.showinfo(
                'RememberWindowsState',
                'No applications selected to restore!',
                parent=self._win)
            return

        threading.Thread(
            target=lambda: restore_windows(selected),
            daemon=True).start()
