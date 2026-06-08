"""Unit tests for testing the window merging logic on shutdown."""
import sys
from main import _merge_windows

def test_merge_windows():
    # 1. State representing the last auto-saved snapshot (taken when everything was normally open)
    last_saved = [
        {
            "title": "Projects",
            "exe_path": "C:\\Windows\\explorer.exe",
            "exe_name": "explorer.exe",
            "explorer_path": "C:\\Projects",
            "x": 100, "y": 100, "width": 800, "height": 600,
            "minimized": False, "state": "normal"
        },
        {
            "title": "Google Chrome",
            "exe_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "exe_name": "chrome.exe",
            "x": 200, "y": 200, "width": 1024, "height": 768,
            "minimized": False, "state": "normal"
        },
        {
            "title": "untitled.txt - Notepad",
            "exe_path": "C:\\Windows\\System32\\notepad.exe",
            "exe_name": "notepad.exe",
            "x": 50, "y": 50, "width": 400, "height": 300,
            "minimized": False, "state": "normal"
        }
    ]

    # 2. State representing the shutdown snapshot (where Explorer and Chrome closed early)
    # Notepad has moved, and a new Calculator window was opened
    current = [
        {
            "title": "untitled.txt - Notepad",
            "exe_path": "C:\\Windows\\System32\\notepad.exe",
            "exe_name": "notepad.exe",
            "x": 60, "y": 60, "width": 410, "height": 310,  # updated position
            "minimized": False, "state": "normal"
        },
        {
            "title": "Calculator",
            "exe_path": "C:\\Windows\\System32\\calc.exe",
            "exe_name": "calc.exe",
            "x": 500, "y": 500, "width": 300, "height": 400,
            "minimized": False, "state": "normal"
        }
    ]

    merged = _merge_windows(current, last_saved)

    # We expect 4 windows:
    # - Explorer (preserved from last_saved)
    # - Chrome (preserved from last_saved)
    # - Notepad (updated from current)
    # - Calculator (added from current)
    assert len(merged) == 4, f"Expected 4 windows, got {len(merged)}"

    # Find the windows in the merged result
    explorer = next((w for w in merged if w["exe_name"] == "explorer.exe"), None)
    chrome = next((w for w in merged if w["exe_name"] == "chrome.exe"), None)
    notepad = next((w for w in merged if w["exe_name"] == "notepad.exe"), None)
    calculator = next((w for w in merged if w["exe_name"] == "calc.exe"), None)

    assert explorer is not None, "Explorer window should be preserved"
    assert explorer["explorer_path"] == "C:\\Projects"
    assert explorer["x"] == 100, "Explorer position should be kept as-is"

    assert chrome is not None, "Chrome window should be preserved"
    assert chrome["x"] == 200, "Chrome position should be kept as-is"

    assert notepad is not None, "Notepad window should exist"
    assert notepad["x"] == 60, "Notepad position should be updated from the current shutdown snapshot"

    assert calculator is not None, "Calculator window should exist"
    assert calculator["x"] == 500, "Calculator window should be retained"

    print("[OK] _merge_windows logic behaves correctly under simulated shutdown conditions!")

if __name__ == "__main__":
    try:
        test_merge_windows()
        print("=== MERGE TESTS PASSED ===")
        sys.exit(0)
    except AssertionError as e:
        print(f"=== MERGE TESTS FAILED ===\n{e}")
        sys.exit(1)
