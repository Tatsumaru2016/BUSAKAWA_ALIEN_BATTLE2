# game_loop/phases/gameplay.py

from game_loop.gameplay_score_boss import run_gameplay_score_boss_phase
from game_loop.gameplay_spawns import run_gameplay_spawns_phase
from game_loop.gameplay_entities import run_gameplay_entities_phase
from game_loop.bullet_collisions import run_bullet_collisions_phase
from game_loop.resources import frame_core
from screen_modes import PLAY, EXTRA_PLAY


def _tick_score_chain_after_combat() -> None:
    """撃破登録のあとに猶予タイマーを減らす（同フレームで撃破→猶予リセットが効く）。"""
    core = frame_core()
    if core.state not in (PLAY, EXTRA_PLAY):
        return
    play = core.play
    if play.player_dead or play.boss_score_tally.active:
        return
    play.score_chain.tick(paused=False)


def run_gameplay_phase() -> None:
    run_gameplay_score_boss_phase()
    run_gameplay_spawns_phase()
    run_bullet_collisions_phase()
    _tick_score_chain_after_combat()
    run_gameplay_entities_phase()
