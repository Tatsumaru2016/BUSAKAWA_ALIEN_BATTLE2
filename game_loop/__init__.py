import pygame

from game_loop.phases import run_all_phases
from game_runtime import RT


def run_play_frame() -> None:
    g = RT.g()
    g["diff"] = g["app"].diff
    g["hi_score"] = g["app"].hi_score
    g["_ticks"] = pygame.time.get_ticks()
    run_all_phases()
    g["app"].hi_score = g["hi_score"]
