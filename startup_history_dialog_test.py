"""Standalone test: run the StartupHistoryDialog with real history data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from config import Config
from window_tracker import load_history
from startup_history_dialog import StartupHistoryDialog

config  = Config()
entries = list(reversed(load_history(config.state_file)))
print(f'[test] {len(entries)} history entries loaded')

root = tk.Tk()
root.withdraw()

dlg = StartupHistoryDialog(root, entries, config)
dlg.show()

print('[test] dialog closed, exiting.')
root.destroy()
