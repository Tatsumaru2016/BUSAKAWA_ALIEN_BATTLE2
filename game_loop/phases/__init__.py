from game_loop.phases.player_input import run_player_input_phase
from game_loop.phases.gameplay import run_gameplay_phase
from game_loop.phases.boss_combat_phase import run_boss_combat_phase
from game_loop.extra_boss_combat import run_extra_boss_combat_phase
from game_loop.phases.hud_results import run_hud_results_phase
from game_loop.world_updates import run_world_updates_phase
from game_pause import gameplay_freeze_active
from game_runtime import RT

PHASE_RUNNERS = (
    run_player_input_phase,
    run_gameplay_phase,
    run_boss_combat_phase,
    run_extra_boss_combat_phase,
    run_world_updates_phase,
    run_hud_results_phase,
)


def run_all_phases() -> None:
    g = RT.g()
    if gameplay_freeze_active(g["play"], g["state"]):
        run_hud_results_phase()
        return
    for run in PHASE_RUNNERS:
        run()
