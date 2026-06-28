#!/usr/bin/env python3
"""Generate build_assets_manifest.txt for PyInstaller (referenced assets only)."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
MANIFEST = ROOT / "build_assets_manifest.txt"
SKIP_DIRS = {"build", "dist", ".git", "__pycache__", "tools"}


def collect_source_text() -> str:
    parts: list[str] = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if Path(root).resolve() == ASSETS.resolve():
            continue
        for name in files:
            if name.endswith((".py", ".spec")):
                parts.append((Path(root) / name).read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def build_referenced_names(text: str) -> set[str]:
    refs: set[str] = set()
    for m in re.finditer(r"assets/([\w\-.]+\.(?:png|ogg|wav|mp4|ttf))", text, re.I):
        refs.add(m.group(1))
    for m in re.finditer(r'["\']([\w\-.]+\.(?:png|ogg|wav|mp4|ttf))["\']', text, re.I):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r'load_image\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r'load_sound(?:_fn)?\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r'_load_first\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r',\s*["\']([\w\-.]+\.png)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for i in range(1, 9):
        refs.add(f"enemy_{i:02d}.png")
    for i in range(1, 5):
        refs.add(f"enemy_ace{i:02d}.png")
    for i in range(1, 8):
        refs.add(f"ending{i}.png")
    for d in ("easy", "normal", "hard", "nightmare"):
        for st in ("on", "off"):
            refs.add(f"diff_{d}_{st}.png")
    for key, fname in {
        "normal": "player.png",
        "up": "player_up.png",
        "down": "player_down.png",
        "left": "player_left.png",
        "right": "player_right.png",
        "shot": "player_shot.png",
    }.items():
        refs.add(fname)
    refs.add("icon.png")
    refs.add("NotoSansJP-Regular.ttf")
    refs.add("player_zanki.png")
    refs.add("ending.png")
    refs.add("player_shield_bar.png")
    for i in range(1, 6):
        refs.add(f"support_fighter_{i}.png")
    return refs


# EXE に同梱しない（実ファイルがあればコード側フォールバックで足りる）
OPTIONAL_BGM_FALLBACKS = {
    "bgm.ogg": "bgm_main.ogg",
    "bgm_boss123.ogg": ("boss1_bgm.ogg", "boss2_bgm.ogg", "boss3_bgm.ogg"),
}
# OpenCV なしビルドでは MP4 スプラッシュを使わない
EXE_EXCLUDE = {"splash_intro.mp4"}


def _drop_optional_fallbacks(names: set[str], on_disk: set[str]) -> set[str]:
    out = set(names)
    for fallback, primaries in OPTIONAL_BGM_FALLBACKS.items():
        if fallback not in out:
            continue
        if isinstance(primaries, str):
            primaries = (primaries,)
        if any(p in on_disk for p in primaries):
            out.discard(fallback)
    out -= EXE_EXCLUDE
    return out


def main() -> None:
    text = collect_source_text()
    refs = build_referenced_names(text)
    on_disk = {p.name for p in ASSETS.iterdir() if p.is_file()}
    manifest = sorted(_drop_optional_fallbacks(refs & on_disk, on_disk))
    missing = sorted(refs - on_disk)
    unused = sorted(on_disk - refs)

    MANIFEST.write_text("\n".join(manifest) + "\n", encoding="ascii")
    print(f"wrote {len(manifest)} files -> {MANIFEST.name}")
    if missing:
        print(f"missing ({len(missing)}):")
        for n in missing[:15]:
            print(f"  {n}")
    if unused:
        print(f"unused on disk ({len(unused)}):")
        total = 0
        for n in unused:
            sz = (ASSETS / n).stat().st_size
            total += sz
            print(f"  {sz/1024/1024:6.2f} MB  {n}")
        print(f"unused total: {total/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
