# Changelog

All notable changes to **RememberWindowsState** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.3.1] — 2026-07-24

### Changed

- **License Update**: Relicensed the project under **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

## [1.3.0] — 2026-07-23

### Added & Improved

- **Automatic User-Opened Windows vs Background/Tray Filtering**:
  - Expanded default system blacklist (`SYSTEM_EXES` in `window_tracker.py`) with extensive Windows background services, helper utilities, and background tasks (`backgroundtaskhost.exe`, `searchapp.exe`, `widgets.exe`, `msedgewebview2.exe`, `smartscreen.exe`, etc.) to prevent silent background services from cluttering logs and history.
  - Implemented automatic tracking of user-opened applications (`USER_OPENED_EXES`): only processes that were opened with a visible/minimized window by the user are tracked when minimized/closed to tray. Uninvited background processes are completely ignored.
  - Added `[Tray]` badge and visual indicators in **History Tab** and **Startup History Dialog** for tray apps.

### Fixed

- **Blacklist Tab Real-time Synchronization**: Fixed listbox reload when switching to the Blacklist tab in Settings (`settings_gui.py`, `settings_gui_blacklist.py`), ensuring that items added to the blacklist directly from dialogs immediately appear in the list.

## [1.2.0] — 2026-07-23

### Added

- **Software Update Check in General Settings** — Added a dedicated "Check for Updates" section in the General tab (`settings_gui_general.py`, `updater.py`):
  - Fetches and checks the latest GitHub Release (`mostafanazarzadeh/RememberWindowsState`) asynchronously in a background thread to prevent UI freezing.
  - Displays current version status, success/error feedback, and a direct download button when a newer release is detected.

## [1.1.0] — 2026-07-18

### Added

- **Direct Blacklist Buttons in App Lists** — Added a convenient `🚫` button in front of every application displayed in:
  - **Restore Dialog** (`restore_dialog.py`)
  - **Startup History Dialog** (`startup_history_dialog.py`)
  - **Settings History Tab** (`settings_gui_history.py`)
  This enables users to immediately exclude any unwanted process/application from being tracked or restored, with a confirmation prompt.

## [1.0.0] — 2026-06-08

This is the initial stable release of **RememberWindowsState**, including a fully English user interface, robust system tray integration, automatic state persistence, window startup recovery, and custom user settings.

### Added

- **Minimized & Tray-Only Window Tracking** (`window_tracker.py`, `window_restorer.py`) — The app now correctly tracks and restores applications that are minimized to the taskbar or collapsed to the system tray:
  - `get_open_windows()` now captures minimized (iconic) windows that were previously skipped.
  - A new `_add_tray_processes()` helper walks process window handles (including hidden ones) to add tray-only apps.
  - Each window record includes a state field (`'normal'`, `'minimized'`, or `'tray'`).
  - `get_running_exe_paths()` collects all PIDs with any window handle, preventing running tray/minimized apps from being relaunch-offered.
  - `restore_window()` restores running minimized/tray apps by calling `ShowWindow(SW_RESTORE)` and bringing them to foreground, fallback to `subprocess.Popen` is only used when the app is not running.
- **Configurable History Limit** — Introduced a settings section to customize the maximum number of history snapshots saved:
  - Added `trim_history(state_file, limit)` helper function in `window_tracker.py` to immediately prune snapshots.
  - Added `history_limit` config field (defaulting to 50).
- **`WindowChangeWatcher`** (`main.py`) — A lightweight background thread that polls open windows every 2 seconds, automatically recording history entries when applications open or close (move/resize events are ignored).
- **Multi-Entry History** (`window_tracker.py`) — Introduced `history.json` to store labeled snapshots up to the configured history limit.
- **Redesigned History Dialogs** — Added collapsible card widgets to view and expand saved snapshot lists:
  - Expanded cards reveal the application list at that moment with an option to restore to that state.
  - Supports local mouse-wheel scrolling.
  - Contains a `🔄 Reload` button to refresh states.
- **`startup_history_dialog.py`** — Dark-themed dialog shown at Windows startup listing history snapshots so the user can choose which saved state to restore.
- **Post-Restart Failure Logging** (`app_logger.py`, `main.py`) — Centralized rotating file-based logging under `%APPDATA%\RememberWindowsState\logs\app.log` for easy troubleshooting.
- **Single-Instance Guard** (`main.py`) — Mutex check (`CreateMutexW`) to prevent running duplicate instances, alerting the user if an instance is already running.
- **`WindowScheduler`** (`scheduler.py`) — Background daemon thread that schedules periodic automatic saves.
- **System Tray menu** (`tray_app.py`) — A `pystray`-based tray application allowing on-demand actions (Save Now, Restore Windows, Settings, Blacklist, Quit).
- **Application Blacklist** (`config.py`, `settings_gui.py`) — Excludes user-defined executable names from being tracked.
- **Windows Registry Autostart** (`startup.py`) — Enable or disable launching on Windows login via the registry key.
- **Packaging & Builds** — Assets (`icon.png`/`icon.ico`), PyInstaller build specification (`RememberWindowsState.spec`), Inno Setup compiler script (`installer.iss`), and a `build.bat` script.
- **AI Rules Configuration** — Created `.clinerules` and `.cursorrules`.

### Changed

- **UI & Layout Reorganization**:
  - The history panel is now the main screen (`HistoryWindow`), which opens directly when clicking the tray icon or launching the app manually.
  - Settings window now focuses purely on General options (interval slider, startup toggle, and history limit).
  - Blacklist management is moved into a standalone `BlacklistWindow` class.
- **English UI Localization** — Translated all Persian UI text elements (window titles, status labels, buttons, headers, and badges) to English to ensure a fully localized English user interface.
- **Startup Restore flow** — When launched via `--startup`, the application displays the **Startup History Dialog** rather than executing silently, allowing full control over which state to load.

### Optimized & Fixed

- **Duplicate Shutdown State Saving** — Added a `_shutdown_saved` guard flag and integrated aborted shutdown handling in `main.py` so the window state snapshot is saved exactly once on `WM_QUERYENDSESSION`. This ensures fast-closing apps (like PotPlayer) are captured correctly.
- **Restored Merge Logic** — Resolved a concurrency conflict by properly integrating the `_merge_windows` helper inside the shutdown state saving routine.
- **Lazy Loading widgets** — History cards now populate their checkbox widgets on-demand when expanded. This eliminates lag and window delays when displaying many snapshots.
- **Global Event Leaks** — Resolved global Tkinter `MouseWheel` scroll event leaks by binding/unbinding event handlers locally to the canvas component on `<Enter>` and `<Leave>`.
- **Instance Caching** — Cached the active `RestoreDialog` instance to prevent spawning duplicate modal windows when clicked repeatedly.
- **History Tab crash** — Fixed a `TclError` caused by passing a tuple for `pady` directly to Tkinter constructors.

---

*Dates reflect local commit time (UTC+3:30).*
