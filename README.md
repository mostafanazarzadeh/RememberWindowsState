# RememberWindowsState

> **Never lose your workspace again.** RememberWindowsState automatically saves your open windows and restores them after a restart, shutdown, or crash — silently running in the System Tray.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?logo=windows)](https://www.microsoft.com/windows)
[![Latest Release](https://img.shields.io/github/v/release/mostafanazarzadeh/RememberWindowsState?logo=github)](https://github.com/mostafanazarzadeh/RememberWindowsState/releases)
[![Downloads](https://img.shields.io/github/downloads/mostafanazarzadeh/RememberWindowsState/total?logo=github)](https://github.com/mostafanazarzadeh/RememberWindowsState/releases)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Stable-brightgreen)]()

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Use Prebuilt Installer](#use-prebuilt-installer)
  - [Build from Source](#build-from-source)
    - [Requirements](#requirements)
  - [Build Installer (.exe)](#build-installer-exe)
- [Usage](#usage)
- [Configuration](#configuration)
- [Data & Storage](#data--storage)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Contributing](#contributing)
- [Privacy](#privacy)
- [License](#license)

---

## Overview

RememberWindowsState is a lightweight Windows utility that periodically snapshots your open application windows (title, executable path, and position) and restores them on demand. It is designed to be completely unobtrusive — living in the System Tray with zero visible footprint while you work.

Whether you've experienced an unexpected shutdown, a Windows Update reboot, or simply want to pick up exactly where you left off, RememberWindowsState has you covered.

---

## Features

| Feature | Description |
|---|---|
| ⏱ **Auto-Save Snapshots** | Automatically captures your open windows at configurable intervals (10 seconds → 30 minutes) |
| 🔄 **Smart Restore** | At startup, shows only windows that are not already open — no duplicates |
| 🚀 **Run at Windows Login** | Optional autostart via Windows Registry |
| 🖥 **System Tray Icon** | Runs silently in the background with a clean tray menu |
| 🚫 **Application Blacklist** | Exclude specific apps (by `.exe` name) from being tracked |
| 📜 **Snapshot History** | View the last saved snapshot directly from the tray |
| 🔒 **Single-Instance Guard** | Prevents multiple instances from running simultaneously |
| 💾 **Local Storage Only** | All data is stored exclusively on your local machine — no cloud, no telemetry |

---

## Installation

### Use Prebuilt Installer

The easiest way to get started is to download the prebuilt installer:

1. Download the latest installer (`RememberWindowsState-Setup.exe`) from the [Releases](https://github.com/mostafanazarzadeh/RememberWindowsState/releases) page.
2. Run the installer and follow the setup wizard.
3. The application will launch and run silently in your System Tray.

### Build from Source

#### Requirements

- **OS**: Windows 10 or Windows 11 (64-bit)
- **Python**: 3.10 or higher
- **Dependencies** (auto-installed via `pip`):

```
pywin32 >= 306
psutil  >= 5.9.0
pystray >= 0.19.5
Pillow  >= 10.0.0
```

> For building an installer from source, [Inno Setup 6](https://jrsoftware.org/isdl.php) is also required.

#### Setup Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/mostafanazarzadeh/RememberWindowsState.git
   cd RememberWindowsState
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the application**

   ```bash
   python main.py
   ```

### Build Installer (.exe)

Build a standalone Windows executable and Inno Setup installer with a single command:

```bash
build.bat
```

This will:
1. Run **PyInstaller** to package the app into a single `.exe`
2. Run **Inno Setup** to produce a `.exe` installer in `dist/`

> Make sure [Inno Setup 6](https://jrsoftware.org/isdl.php) is installed at its default location before running the build script.

---

## Usage

### System Tray Menu

Right-click the tray icon to access:

| Action | Description |
|---|---|
| 💾 **Save Now** | Immediately take a snapshot of all open windows |
| 🔄 **Restore Windows** | Show a list of previously saved windows to reopen |
| ⚙️ **Settings** | Open the settings panel |
| ❌ **Exit** | Quit the application |

### Restore Dialog

When RememberWindowsState launches manually (not via Windows startup), it automatically checks whether any previously saved windows are not currently open. If so, it presents a **Restore Dialog** where you can:

- Select individual windows to reopen
- Select all with one click
- Dismiss and continue without restoring

### Launch Modes

| Command | Behavior |
|---|---|
| `python main.py` | Manual launch — shows restore dialog if unclosed windows exist |
| `python main.py --startup` | Startup launch — skips restore dialog, tracks silently |

---

## Configuration

Open **Settings** from the tray icon to configure:

| Setting | Default | Description |
|---|---|---|
| **Save Interval** | 30 seconds | How often to snapshot open windows |
| **Run at Windows Startup** | Off | Add/remove from Windows Registry autostart |
| **Blacklist** | *(empty)* | List of `.exe` filenames to exclude from tracking |

Settings are persisted automatically to `config.json`.

---

## Data & Storage

All data is stored **locally on your machine** under:

```
%APPDATA%\RememberWindowsState\
├── config.json          ← Application settings
├── windows_state.json   ← Latest window snapshot
└── logs/
    └── app.log          ← Application log file (rotated at 200 KB)
```

**On Windows, this typically resolves to:**

```
C:\Users\<YourName>\AppData\Roaming\RememberWindowsState\
```

The `windows_state.json` file stores:
- Window **title**
- Executable **path** (`exe`)
- Window **position and size** (`rect`)

No personal data, keystrokes, or screen content is ever captured.

---

## Project Structure

```
RememberWindowsState/
│
├── main.py               ← Application entry point & orchestration
├── config.py             ← Settings management (JSON persistence)
├── window_tracker.py     ← Win32 API window enumeration & snapshotting
├── window_restorer.py    ← Subprocess-based window launching & filtering
├── scheduler.py          ← Background timer for periodic snapshots
├── startup.py            ← Windows Registry autostart integration
├── restore_dialog.py     ← Tkinter restore selection dialog
├── settings_gui.py       ← Tkinter settings panel
├── tray_app.py           ← pystray System Tray integration
├── create_icon.py        ← Pillow-based icon generation utility
│
├── RememberWindowsState.spec  ← PyInstaller build spec
├── installer.iss              ← Inno Setup installer script
├── build.bat                  ← One-click build script
├── requirements.txt           ← Python dependencies
│
└── assets/
    ├── icon.png          ← Application icon (source)
    └── icon.ico          ← Application icon (Windows)
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                     RememberWindowsState                    │
│                                                             │
│  ┌──────────────┐   every N sec   ┌───────────────────┐    │
│  │  Scheduler   │ ──────────────► │  Window Tracker   │    │
│  └──────────────┘                 │  (Win32 EnumWindows│    │
│                                   │   + psutil)        │    │
│                                   └────────┬──────────┘    │
│                                            │ snapshot       │
│                                            ▼               │
│                                   ┌───────────────────┐    │
│                                   │  windows_state.json│    │
│                                   └────────┬──────────┘    │
│                                            │ on launch      │
│                                            ▼               │
│                                   ┌───────────────────┐    │
│                                   │  Restore Dialog   │    │
│                                   │  (Tkinter UI)     │    │
│                                   └───────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

1. **Track**: `window_tracker.py` uses the Win32 `EnumWindows` API (via `pywin32`) along with `psutil` to enumerate all visible, non-system windows.
2. **Snapshot**: Each window's title, executable path, and screen coordinates are serialised to `windows_state.json`.
3. **Schedule**: `scheduler.py` calls the snapshot function on a configurable timer in a background daemon thread.
4. **Restore**: On next launch, `window_restorer.py` compares the snapshot against currently running processes and offers to relaunch any that are missing.

---

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages and keep pull requests focused on a single concern.

### Reporting Bugs

Please open a GitHub Issue if you run into any problems, such as:
- Any applications that are supposed to be restored/opened but fail to launch.
- Any internal background helper windows (such as `OfficePowerManagerWindow` or other hidden system components) mistakenly showing up in your tracked window list or restore dialogs.

When reporting bugs, **please attach/include your log file**. You can find it at:
`%APPDATA%\RememberWindowsState\logs\app.log`
*(Typically: `C:\Users\<YourName>\AppData\Roaming\RememberWindowsState\logs\app.log`)*

When reporting, please include:
- Your Windows version
- Python version
- Steps to reproduce
- The name, title, or class of any background window that shouldn't have been tracked (if applicable)
- The name/executable path of any application that failed to restore (if applicable)
- Any error messages from the console or log files

---

## Privacy

RememberWindowsState collects **no personal data** and makes **no network connections**. See [PRIVACY.md](PRIVACY.md) for full details.

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Made with ❤️ in Iran for Windows power users who hate losing their workspace.
</p>
