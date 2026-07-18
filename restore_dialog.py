"""
RememberWindowsState — restore_dialog.py
Beautiful dark-themed dialog that shows saved windows and asks the user
which ones to restore.  Must be called from the main tkinter thread.
"""

import os
import tkinter as tk
from datetime import datetime

from gui_tokens import BG, SURFACE, SURFACE2, BTN_BG, ACCENT, ACCENT_H, TEXT, TEXT_DIM, DANGER, BORDER
from gui_utils import set_window_icon


class RestoreDialog:
    """
    Modal-like Toplevel that shows unclosed saved windows and returns
    the ones the user selected for restoration.
    """

    def __init__(self, master: tk.Tk, snapshot: dict, not_open: list[dict], config=None):
        self._master    = master
        self._snapshot  = snapshot
        self._not_open  = not_open
        self._config    = config
        self._check_vars: list[tk.BooleanVar] = []
        self._result: list[dict] = []

        self._win = tk.Toplevel(master)
        self._win.title('RememberWindowsState')
        self._win.configure(bg=BG)
        self._win.resizable(False, False)
        self._win.protocol('WM_DELETE_WINDOW', self._skip)

        W, H = 580, 540
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f'{W}x{H}+{(sw-W)//2}+{(sh-H)//2}')

        set_window_icon(self._win)
        self._build()
        self._win.grab_set()      # modal

    # ──────────────────────────────────────────────── UI construction
    def _build(self):
        # Accent stripe at top
        tk.Frame(self._win, bg=ACCENT, height=4).pack(fill='x')

        # ── Header ──────────────────────────────────────────────────
        hdr = tk.Frame(self._win, bg=SURFACE, padx=22, pady=14)
        hdr.pack(fill='x')

        tk.Label(hdr, text='🔄', font=('Segoe UI Emoji', 26),
                 bg=SURFACE, fg=ACCENT).pack(side='left', padx=(0, 12))

        txt = tk.Frame(hdr, bg=SURFACE)
        txt.pack(side='left')

        tk.Label(txt, text='Restore Previous Windows',
                 font=('Segoe UI', 14, 'bold'), bg=SURFACE, fg=TEXT
                 ).pack(anchor='w')

        ts = self._snapshot.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(ts)
            label = dt.strftime('Last saved: %Y/%m/%d  —  %H:%M:%S')
        except Exception:
            label = f'Last saved: {ts}'

        tk.Label(txt, text=label, font=('Segoe UI', 9),
                 bg=SURFACE, fg=TEXT_DIM).pack(anchor='w')

        # ── Sub-title ────────────────────────────────────────────────
        sub = tk.Frame(self._win, bg=BG, padx=22, pady=8)
        sub.pack(fill='x')
        n = len(self._not_open)
        tk.Label(sub, text=f'{n} application(s) not currently running:',
                 font=('Segoe UI', 10), bg=BG, fg=TEXT_DIM).pack(anchor='w')

        # ── Scrollable window list ────────────────────────────────────
        list_outer = tk.Frame(self._win, bg=SURFACE, padx=2, pady=2)
        list_outer.pack(fill='both', expand=True, padx=22, pady=(0, 10))

        canvas = tk.Canvas(list_outer, bg=SURFACE,
                           highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(list_outer, orient='vertical',
                           command=canvas.yview)
        inner = tk.Frame(canvas, bg=SURFACE)
        inner.bind('<Configure>',
                   lambda e: canvas.configure(
                       scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side='left', fill='both', expand=True)
        if n > 7:
            vsb.pack(side='right', fill='y')

        for idx, win in enumerate(self._not_open):
            var = tk.BooleanVar(value=True)
            self._check_vars.append(var)
            row_bg = SURFACE if idx % 2 == 0 else SURFACE2

            row = tk.Frame(inner, bg=row_bg, pady=9, padx=10)
            row.pack(fill='x')

            tk.Checkbutton(row, variable=var,
                           bg=row_bg, activebackground=row_bg,
                           selectcolor=SURFACE, fg=ACCENT,
                           highlightthickness=0, bd=0,
                           cursor='hand2').pack(side='left')

            info = tk.Frame(row, bg=row_bg)
            info.pack(side='left', fill='x', expand=True, padx=(6, 0))

            app_label = os.path.splitext(
                win.get('exe_name', 'Unknown'))[0].replace('_', ' ').title()
            title_txt = win.get('title', '')

            if win.get('exe_name', '').lower() == 'explorer.exe' and 'explorer_path' in win:
                app_label = "File Explorer"
                title_txt = win['explorer_path']

            tk.Label(info, text=f'  {app_label}',
                     font=('Segoe UI', 10, 'bold'),
                     bg=row_bg, fg=TEXT, anchor='w').pack(fill='x')

            if len(title_txt) > 65:
                title_txt = title_txt[:62] + '…'
            tk.Label(info, text=f'  {title_txt}',
                     font=('Segoe UI', 8), bg=row_bg,
                     fg=TEXT_DIM, anchor='w').pack(fill='x')

            # Blacklist button on the right
            if self._config:
                def _blacklist_row(win_entry=win, r=row, v=var):
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
                        if v in self._check_vars:
                            self._check_vars.remove(v)
                        if win_entry in self._not_open:
                            self._not_open.remove(win_entry)
                        r.destroy()

                bl_btn = tk.Button(row, text='🚫', bg=row_bg, fg=DANGER,
                                   font=('Segoe UI Emoji', 9), relief='flat',
                                   cursor='hand2', padx=6, pady=2, bd=0)
                bl_btn.pack(side='right', padx=(6, 0))
                bl_btn.configure(command=_blacklist_row)

                # Bind hover effects locally
                bl_btn.bind('<Enter>', lambda e, b=bl_btn: b.configure(bg='#ffe5e5', fg=DANGER))
                bl_btn.bind('<Leave>', lambda e, b=bl_btn, bg=row_bg: b.configure(bg=bg, fg=DANGER))

        # Mouse-wheel scroll
        def _wheel(evt):
            try:
                canvas.yview_scroll(-1 * (evt.delta // 120), 'units')
            except Exception:
                pass
        # Scope mouse wheel to this canvas only (avoid global leak)
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _wheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        canvas.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # ── Select-all / none ─────────────────────────────────────────
        sel_row = tk.Frame(self._win, bg=BG, padx=22)
        sel_row.pack(fill='x')

        def _btn(parent, text, cmd):
            b = tk.Button(parent, text=text, command=cmd,
                          bg=BTN_BG, fg=TEXT_DIM,
                          font=('Segoe UI', 9), relief='flat',
                          cursor='hand2', padx=10, pady=4, bd=0)
            b.pack(side='left', padx=(0, 6))
            b.bind('<Enter>', lambda e: b.configure(bg='#cfcfcf', fg=TEXT))
            b.bind('<Leave>', lambda e: b.configure(bg=BTN_BG, fg=TEXT_DIM))

        _btn(sel_row, 'Select All',
             lambda: [v.set(True) for v in self._check_vars])
        _btn(sel_row, 'Deselect All',
             lambda: [v.set(False) for v in self._check_vars])

        # ── Action buttons ────────────────────────────────────────────
        btn_row = tk.Frame(self._win, bg=BG, padx=22, pady=14)
        btn_row.pack(fill='x')

        skip = tk.Button(btn_row, text='Skip', command=self._skip,
                         bg=BTN_BG, fg=TEXT_DIM,
                         font=('Segoe UI', 10), relief='flat',
                         cursor='hand2', padx=18, pady=9, bd=0)
        skip.pack(side='right', padx=(8, 0))
        skip.bind('<Enter>', lambda e: skip.configure(bg='#cfcfcf', fg=TEXT))
        skip.bind('<Leave>', lambda e: skip.configure(bg=BTN_BG, fg=TEXT_DIM))

        restore = tk.Button(btn_row, text='✅  Restore Selected',
                            command=self._restore,
                            bg=ACCENT, fg='white',
                            font=('Segoe UI', 10, 'bold'), relief='flat',
                            cursor='hand2', padx=18, pady=9, bd=0)
        restore.pack(side='right')
        restore.bind('<Enter>', lambda e: restore.configure(bg=ACCENT_H))
        restore.bind('<Leave>', lambda e: restore.configure(bg=ACCENT))

    # ──────────────────────────────────────────────── actions
    def _restore(self):
        self._result = [
            w for w, v in zip(self._not_open, self._check_vars)
            if v.get()
        ]
        self._win.grab_release()
        self._win.destroy()

    def _skip(self):
        self._result = []
        self._win.grab_release()
        self._win.destroy()

    def show(self) -> list[dict]:
        """Block until the user dismisses the dialog. Returns selected windows."""
        self._master.wait_window(self._win)
        return self._result



