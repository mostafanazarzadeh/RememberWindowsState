"""
RememberWindowsState — settings_gui_blacklist.py
Blacklist settings tab class.
"""

import tkinter as tk
from config import Config
from gui_tokens import BG, SURFACE, ENTRY_BG, TEXT, TEXT_DIM, ACCENT, DANGER


class BlacklistTab:
    """Blacklist Tab for managing ignored executables."""

    def __init__(self, parent_frame: tk.Frame, config: Config):
        self._parent = parent_frame
        self._config = config
        self._build()

    def _build(self):
        inner = tk.Frame(self._parent, bg=BG, padx=22, pady=18)
        inner.pack(fill='both', expand=True)

        tk.Label(inner,
                 text='Executable names (.exe) you do not want to track:',
                 font=('Segoe UI', 9), bg=BG, fg=TEXT_DIM
                 ).pack(anchor='w', pady=(0, 8))

        # List box
        lb_frame = tk.Frame(inner, bg=SURFACE)
        lb_frame.pack(fill='both', expand=True, pady=(0, 8))

        vsb = tk.Scrollbar(lb_frame, orient='vertical')
        vsb.pack(side='right', fill='y')

        self._lb = tk.Listbox(
            lb_frame, yscrollcommand=vsb.set,
            bg=SURFACE, fg=TEXT, selectbackground=ACCENT,
            selectforeground='white', font=('Consolas', 10),
            relief='flat', bd=0, highlightthickness=0)
        self._lb.pack(fill='both', expand=True, padx=6, pady=6)
        vsb.configure(command=self._lb.yview)

        for item in self._config.blacklist:
            self._lb.insert(tk.END, item)

        # Input row
        inp_row = tk.Frame(inner, bg=BG)
        inp_row.pack(fill='x')

        self._bl_entry = tk.Entry(
            inp_row, bg=ENTRY_BG, fg=TEXT,
            insertbackground=TEXT, font=('Consolas', 10),
            relief='flat', bd=0)
        self._bl_entry.insert(0, 'chrome.exe')
        self._bl_entry.configure(fg=TEXT_DIM)
        self._bl_entry.bind('<FocusIn>',  self._entry_in)
        self._bl_entry.bind('<FocusOut>', self._entry_out)
        self._bl_entry.bind('<Return>',   lambda e: self._bl_add())
        self._bl_entry.pack(side='left', fill='x', expand=True,
                            ipady=7, padx=(0, 8))

        def _mk_btn(txt, cmd, color):
            b = tk.Button(inp_row, text=txt, command=cmd,
                          bg=color, fg='white',
                          font=('Segoe UI', 9), relief='flat',
                          cursor='hand2', padx=12, pady=7, bd=0)
            b.pack(side='left', padx=(0, 4))

        _mk_btn('➕ Add',    self._bl_add, ACCENT)
        _mk_btn('🗑 Remove',  self._bl_remove, DANGER)

    def _entry_in(self, _):
        if self._bl_entry.get() == 'chrome.exe':
            self._bl_entry.delete(0, tk.END)
            self._bl_entry.configure(fg=TEXT)

    def _entry_out(self, _):
        if not self._bl_entry.get().strip():
            self._bl_entry.insert(0, 'chrome.exe')
            self._bl_entry.configure(fg=TEXT_DIM)

    def _bl_add(self):
        val = self._bl_entry.get().strip()
        if not val or val == 'chrome.exe':
            return
        bl = self._config.blacklist
        if val not in bl:
            bl.append(val)
            self._config.blacklist = bl
            self._lb.insert(tk.END, val)
        self._bl_entry.delete(0, tk.END)

    def _bl_remove(self):
        sel = self._lb.curselection()
        if not sel:
            return
        idx = sel[0]
        val = self._lb.get(idx)
        bl = self._config.blacklist
        if val in bl:
            bl.remove(val)
            self._config.blacklist = bl
        self._lb.delete(idx)
