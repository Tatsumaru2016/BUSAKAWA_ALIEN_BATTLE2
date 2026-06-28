# -*- mode: python ; coding: utf-8 -*-
# Release EXE: referenced assets only, no OpenCV (logo splash at startup).
# Build: build.bat  |  pyinstaller main.spec --noconfirm
# Video splash + MP4: use main_video.spec (larger, needs opencv-python-headless)

import os

block_cipher = None
_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_icon = os.path.join(_spec_dir, "assets", "icon.png")
_icon_arg = [_icon] if os.path.isfile(_icon) else []


def _bundle_asset_datas():
    manifest_path = os.path.join(_spec_dir, "build_assets_manifest.txt")
    if not os.path.isfile(manifest_path):
        raise SystemExit(
            "BUILD ERROR: run tools/generate_build_assets.py first "
            "(or build.bat which runs it)."
        )
    datas = []
    with open(manifest_path, encoding="ascii") as f:
        for line in f:
            name = line.strip()
            if not name:
                continue
            src = os.path.join(_spec_dir, "assets", name)
            if not os.path.isfile(src):
                raise SystemExit(f"BUILD ERROR: missing assets/{name}")
            datas.append((src, "assets"))
    return datas


a = Analysis(
    ["main.py"],
    pathex=[_spec_dir],
    binaries=[],
    datas=_bundle_asset_datas(),
    hiddenimports=[
        "pygame",
        "splash_video",
        "splash_factory",
        "splash_audio",
        "splash_logo",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "cv2",
        "opencv_python_headless",
        "numpy",
        "numpy.libs",
        "scipy",
        "pandas",
        "matplotlib",
        "OpenGL",
        "OpenGL_accelerate",
        "tkinter",
        "unittest",
        "pydoc",
        "doctest",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BusakawaAlienBattle2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_arg[0] if _icon_arg else None,
)
