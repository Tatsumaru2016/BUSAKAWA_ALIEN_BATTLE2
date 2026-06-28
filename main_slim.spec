# -*- mode: python ; coding: utf-8 -*-
# 軽量ビルド: pyinstaller main_slim.spec
# EXE 本体は小さく、assets フォルダは dist/BusakawaAlienBattle2/ に同梱（build.bat slim）

import os

block_cipher = None
_icon = os.path.join('assets', 'icon.png')
_icon_arg = [_icon] if os.path.isfile(_icon) else []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pygame'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'numpy',
        'numpy.libs',
        'cv2',
        'cv2.cv2',
        'opencv_python_headless',
        'scipy',
        'pandas',
        'matplotlib',
        'OpenGL',
        'OpenGL_accelerate',
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BusakawaAlienBattle2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_arg[0] if _icon_arg else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BusakawaAlienBattle2',
)
