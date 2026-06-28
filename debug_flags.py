# debug_flags.py — ボス直撃テスト（リリース前に DEBUG_BOSS_SKIP = False）

from __future__ import annotations

import pygame

from boss5_support import clear_boss5_support
from boss_spawn import begin_boss_warning
from game_runtime import RT

# True: タイトルで F8〜F12 から各ボス戦へ。False: 常に通常プレイ開始
DEBUG_BOSS_SKIP = False

# True: ボス5撃破後エンディングを飛ばし、沈黙ボス口ダイブ演出へ（F12 デバッグ用）
DEBUG_EXTRA_AFTER_BOSS5_DEATH = DEBUG_BOSS_SKIP

# True: タイトルで F6 → エクストラステージへ（吸引演出をスキップ）
DEBUG_EXTRA_SKIP = DEBUG_BOSS_SKIP
EXTRA_SKIP_KEY = pygame.K_F6

BOSS_SKIP_KEYS: dict[int, int] = {
    pygame.K_F8: 1,
    pygame.K_F9: 2,
    pygame.K_F10: 3,
    pygame.K_F11: 4,
    pygame.K_F12: 5,
}


def boss_type_from_key(key: int) -> int | None:
    if not DEBUG_BOSS_SKIP:
        return None
    return BOSS_SKIP_KEYS.get(key)


def queue_boss_skip(boss_type: int) -> None:
    if 1 <= boss_type <= 5:
        RT.g()["_debug_boss_skip"] = boss_type


def queue_extra_skip() -> None:
    RT.g()["_debug_extra_skip"] = True


def extra_skip_from_key(key: int) -> bool:
    if not DEBUG_EXTRA_SKIP:
        return False
    return key == EXTRA_SKIP_KEY


def clear_boss_skip_queue() -> None:
    RT.g().pop("_debug_boss_skip", None)
    RT.g().pop("_debug_extra_skip", None)


def apply_play_debug_setup(play, diff) -> None:
    """reset_game 直後: キューされていれば該当ボスの警告 or エクストラへ。"""
    if RT.g().pop("_debug_extra_skip", None):
        play.set("_debug_pending_extra", True)
        return

    boss_type = RT.g().pop("_debug_boss_skip", None)
    if boss_type is None:
        return
    slot = boss_type - 1
    kills_needed = (
        diff.boss_kills[slot] if slot < len(diff.boss_kills) else 0
    )
    play.enemies.clear()
    play.turrets.clear()
    play.enemy_bullets.clear()
    play.enemy_lasers.clear()
    play.update(
        boss_cycle=slot,
        boss_index=slot,
        kill_count=kills_needed,
        boss5_bg_mode=(boss_type == 5),
    )
    if boss_type != 5:
        clear_boss5_support()
    begin_boss_warning(play, boss_type)
