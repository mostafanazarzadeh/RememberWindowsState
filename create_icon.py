"""
RememberWindowsState — create_icon.py
Converts the PNG icon to .ico format for PyInstaller & Windows.
Run once before building: python create_icon.py
"""

import os
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
PNG  = os.path.join(BASE, 'assets', 'icon.png')
ICO  = os.path.join(BASE, 'assets', 'icon.ico')


def make_ico():
    if not os.path.exists(PNG):
        print(f'ERROR: {PNG} not found.')
        return

    img = Image.open(PNG).convert('RGBA')
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    imgs  = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(ICO, format='ICO', sizes=sizes,
                 append_images=imgs[1:])
    print(f'Created: {ICO}')


if __name__ == '__main__':
    make_ico()
