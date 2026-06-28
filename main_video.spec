# -*- mode: python ; coding: utf-8 -*-
# Optional large build: MP4 splash + OpenCV (~+100MB). build.bat video

import os

from PyInstaller.utils.hooks import collect_all

cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")

block_cipher = None
_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_icon = os.path.join(_spec_dir, "assets", "icon.png")
_icon_arg = [_icon] if os.path.isfile(_icon) else []

_splash_mp4 = os.path.join(_spec_dir, "assets", "splash_intro.mp4")
if not os.path.isfile(_splash_mp4):
    raise SystemExit("BUILD ERROR: assets/splash_intro.mp4 required for video build.")


def _bundle_asset_datas():
    manifest_path = os.path.join(_spec_dir, "build_assets_manifest.txt")
    if not os.path.isfile(manifest_path):
        raise SystemExit(
            "BUILD ERROR: run tools/generate_build_assets.py first "
            "(or build_mp4.bat)."
        )
    datas = []
    splash = os.path.join(_spec_dir, "assets", "splash_intro.mp4")
    datas.append((splash, "assets"))
    with open(manifest_path, encoding="ascii") as f:
        for line in f:
            name = line.strip()
            if not name or name == "splash_intro.mp4":
                continue
            src = os.path.join(_spec_dir, "assets", name)
            if not os.path.isfile(src):
                raise SystemExit(f"BUILD ERROR: missing assets/{name}")
            datas.append((src, "assets"))
    return datas


a = Analysis(
    ["main.py"],
    pathex=[_spec_dir],
    binaries=cv2_binaries,
    datas=_bundle_asset_datas() + cv2_datas,
    hiddenimports=[
        "pygame",
        "splash_video",
        "splash_factory",
        "splash_audio",
        "splash_logo",
    ]
    + cv2_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
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
