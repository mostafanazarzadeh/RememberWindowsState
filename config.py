"""
RememberWindowsState — config.py
Manages persistent application settings stored in %APPDATA%\\RememberWindowsState\\config.json
"""

import json
import os

DEFAULT_CONFIG = {
    'interval': 30,                     # seconds between snapshots
    'startup_with_windows': False,      # launch at Windows boot
    'blacklist': [],                    # list of exe names to ignore
    'history_limit': 50,                # max saved snapshots in history
    'track_explorer': True,             # track explorer folder paths
}


class Config:
    def __init__(self):
        self.app_data_dir = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'RememberWindowsState'
        )
        os.makedirs(self.app_data_dir, exist_ok=True)

        self.config_path = os.path.join(self.app_data_dir, 'config.json')
        self.state_path  = os.path.join(self.app_data_dir, 'windows_state.json')

        self._data = dict(DEFAULT_CONFIG)
        self.load()

    # ------------------------------------------------------------------ I/O
    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception:
                pass

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f'[Config] save error: {e}')

    # ----------------------------------------------------------- properties
    @property
    def interval(self) -> int:
        return int(self._data.get('interval', 30))

    @interval.setter
    def interval(self, value: int):
        self._data['interval'] = int(value)
        self.save()

    @property
    def startup_with_windows(self) -> bool:
        return bool(self._data.get('startup_with_windows', False))

    @startup_with_windows.setter
    def startup_with_windows(self, value: bool):
        self._data['startup_with_windows'] = bool(value)
        self.save()

    @property
    def blacklist(self) -> list:
        return list(self._data.get('blacklist', []))

    @blacklist.setter
    def blacklist(self, value: list):
        self._data['blacklist'] = list(value)
        self.save()

    @property
    def history_limit(self) -> int:
        return int(self._data.get('history_limit', 50))

    @history_limit.setter
    def history_limit(self, value: int):
        self._data['history_limit'] = int(value)
        self.save()

    @property
    def track_explorer(self) -> bool:
        return bool(self._data.get('track_explorer', True))

    @track_explorer.setter
    def track_explorer(self, value: bool):
        self._data['track_explorer'] = bool(value)
        self.save()

    @property
    def state_file(self) -> str:
        return self.state_path
