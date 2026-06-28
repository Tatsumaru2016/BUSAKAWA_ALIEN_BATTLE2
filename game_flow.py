# game_flow.py — ゲーム進行フラグ（画面モードと PlayState の組み合わせ）

from __future__ import annotations

from typing import TYPE_CHECKING

from screen_modes import EXTRA_PLAY, PLAY

if TYPE_CHECKING:
    from game_state import PlayState


def is_final_gameover_play(play: "PlayState", state: int) -> bool:
    """最終ライフ喪失後、GO 画面へ遷移するまでの PLAY 中演出。"""
    return (
        state in (PLAY, EXTRA_PLAY)
        and play.player_dead
        and play.lives <= 0
        and play.revive_timer <= 0
    )


def player_can_fire(play: "PlayState", boss) -> bool:
    """ボス撃破演出中は自機の射撃を止める。"""
    if getattr(play, "game_paused", False):
        return False
    if getattr(play, "extra_victory_active", False):
        return False
    if boss is not None and getattr(boss, "ex_tank_transform_active", False):
        return False
    intro = getattr(play, "extra_intro_phase", "")
    if intro and intro != "fight":
        return False
    if play.b5_death_active or play.boss_score_tally.active:
        return False
    if play.b5_victory_timer > 0:
        return False
    if boss is not None and play.boss_active and boss.hp <= 0:
        return False
    return True


def should_mute_sfx(play: "PlayState", state: int) -> bool:
    """GO 演出中および GO 画面では効果音を鳴らさない（BGM は別）。"""
    from screen_modes import GAMEOVER

    return is_final_gameover_play(play, state) or state == GAMEOVER
