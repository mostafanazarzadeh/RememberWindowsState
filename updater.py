"""
RememberWindowsState — updater.py
Handles checking GitHub Releases for application updates.
"""

import json
import urllib.request
import webbrowser

APP_VERSION = '1.3.0'
GITHUB_RELEASES_URL = 'https://api.github.com/repos/mostafanazarzadeh/RememberWindowsState/releases/latest'
GITHUB_LATEST_RELEASE_PAGE = 'https://github.com/mostafanazarzadeh/RememberWindowsState/releases'


def parse_version(v_str: str) -> tuple[int, ...]:
    """Parse version string like 'v1.2.0' or '1.2.0' into a tuple of ints."""
    v_clean = str(v_str).strip().lstrip('vV')
    parts = []
    for p in v_clean.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts)


def check_for_updates(current_version: str = APP_VERSION) -> dict:
    """
    Checks GitHub releases for a newer version.
    Returns dict:
        - has_update (bool)
        - latest_version (str)
        - release_url (str)
        - release_notes (str)
        - error (str | None)
    """
    req = urllib.request.Request(
        GITHUB_RELEASES_URL,
        headers={'User-Agent': f'RememberWindowsState/{current_version}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                tag_name = data.get('tag_name', '')
                html_url = data.get('html_url', GITHUB_LATEST_RELEASE_PAGE)
                body = data.get('body', '')

                latest_tuple = parse_version(tag_name)
                current_tuple = parse_version(current_version)

                has_update = latest_tuple > current_tuple
                latest_ver_str = tag_name.lstrip('vV') if tag_name else current_version

                return {
                    'has_update': has_update,
                    'latest_version': latest_ver_str,
                    'release_url': html_url,
                    'release_notes': body,
                    'error': None
                }
            else:
                return {
                    'has_update': False,
                    'latest_version': current_version,
                    'release_url': GITHUB_LATEST_RELEASE_PAGE,
                    'release_notes': '',
                    'error': f'HTTP Error {response.status}'
                }
    except Exception as exc:
        return {
            'has_update': False,
            'latest_version': current_version,
            'release_url': GITHUB_LATEST_RELEASE_PAGE,
            'release_notes': '',
            'error': str(exc)
        }


def open_release_page(url: str = GITHUB_LATEST_RELEASE_PAGE):
    """Opens the GitHub release page in default browser."""
    webbrowser.open(url)
