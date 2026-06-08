"""
RememberWindowsState — gui_utils.py
Shared GUI helper functions.
"""

import os
import tkinter as tk

def set_window_icon(window: tk.BaseWidget):
    """Attempt to set the window icon from assets/icon.ico."""
    try:
        ico = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'assets', 'icon.ico')
        if os.path.exists(ico):
            window.iconbitmap(ico)
    except Exception:
        pass


def draw_section_header(parent: tk.Widget, text: str, bg: str, accent: str, border: str):
    """Draw a styled section header with an underline."""
    f = tk.Frame(parent, bg=bg)
    f.pack(fill='x', pady=(2, 0))
    tk.Label(f, text=text, font=('Segoe UI', 9, 'bold'),
             bg=bg, fg=accent).pack(anchor='w')
    tk.Frame(f, bg=border, height=1).pack(fill='x', pady=(4, 8))
