# game_progress.py — 難易度解放・エクストラ進行条件

from __future__ import annotations

import json

from game_paths import path_in_save_dir

PROGRESS_FILE = path_in_save_dir("progress.json")


def load_progress() -> dict:
    default = {"hard_cleared": False}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {**default, **data}
    except Exception:
        pass
    return dict(default)


def save_progress(data: dict) -> None:
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def is_nightmare_unlocked(progress: dict | None = None) -> bool:
    if progress is None:
        progress = load_progress()
    return bool(progress.get("hard_cleared"))


def mark_hard_cleared() -> bool:
    """HARD で通常エンディング or エクストラクリア時に呼ぶ。初回のみ保存。"""
    progress = load_progress()
    if progress.get("hard_cleared"):
        return False
    progress["hard_cleared"] = True
    save_progress(progress)
    return True


def is_difficulty_selectable(name: str, progress: dict | None = None) -> bool:
    if name != "NIGHTMARE":
        return True
    return is_nightmare_unlocked(progress)


def extra_stage_allowed(diff_name: str) -> bool:
    return diff_name in ("NORMAL", "HARD", "NIGHTMARE")
