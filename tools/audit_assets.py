#!/usr/bin/env python3
"""List assets/ files not referenced by game source."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SKIP_DIRS = {"build", "dist", ".git", "__pycache__", "tools"}


def collect_source_text() -> str:
    parts: list[str] = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if Path(root).resolve() == ASSETS.resolve():
            continue
        for name in files:
            if name.endswith((".py", ".spec", ".txt", ".md")):
                parts.append((Path(root) / name).read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def build_referenced_names(text: str) -> set[str]:
    refs: set[str] = set()
    for m in re.finditer(r"assets/([\w\-.]+\.(?:png|ogg|wav|mp4|ttf))", text, re.I):
        refs.add(m.group(1))
    for m in re.finditer(r'load_image\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r'load_sound(?:_fn)?\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for m in re.finditer(r'_load_first\(["\']([^"\']+)["\']', text):
        refs.add(os.path.basename(m.group(1)))
    for i in range(1, 9):
        refs.add(f"enemy_{i:02d}.png")
    for i in range(1, 5):
        refs.add(f"enemy_ace{i:02d}.png")
    for i in range(1, 20):
        refs.add(f"ending{i}.png")
    for d in ("easy", "normal", "hard", "nightmare"):
        for st in ("normal", "selected", "locked"):
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
    refs.add("splash_intro.mp4")
    refs.add("icon.png")
    refs.add("NotoSansJP-Regular.ttf")
    # BGM fallbacks in audio.py
    refs.update(
        {
            "bgm.ogg",
            "bgm_boss123.ogg",
            "bgm_main.ogg",
            "title.ogg",
            "boss1_bgm.ogg",
            "boss2_bgm.ogg",
            "boss3_bgm.ogg",
            "boss4_bgm.ogg",
            "bgm_boss5.ogg",
            "bgm_boss5_hp100.ogg",
            "bgm_boss5_hp50.ogg",
            "bgm_boss5_hp25.ogg",
            "bgm_boss5_hp10.ogg",
            "bgm_extra_boss.ogg",
            "bgm_extra_boss_tank.ogg",
            "bgm_extra_boss_transform.ogg",
            "bgm_gameover.ogg",
            "bgm_ending.ogg",
        }
    )
    return refs


def main() -> None:
    assets = {p.name for p in ASSETS.iterdir() if p.is_file()}
    refs = build_referenced_names(collect_source_text())
    unused = sorted(assets - refs)
    missing = sorted(refs - assets)
    print(f"assets: {len(assets)} files, referenced: {len(refs & assets)}")
    print(f"unused: {len(unused)}")
    total_unused = 0
    for name in unused:
        sz = (ASSETS / name).stat().st_size
        total_unused += sz
        print(f"  {sz / 1024 / 1024:7.2f} MB  {name}")
    print(f"unused total: {total_unused / 1024 / 1024:.2f} MB")
    if missing:
        print("missing on disk:")
        for name in missing:
            print(f"  {name}")


if __name__ == "__main__":
    main()
