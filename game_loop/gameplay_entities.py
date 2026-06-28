# game_loop/gameplay_entities.py — 敵・タレット更新

from __future__ import annotations

import math

from game_loop.resources import frame_core
from game_runtime import RT
from screen_modes import ENDING, EXTRA_PLAY


def _tick_grunt_ghosts(play) -> None:
    ghosts = getattr(play, "grunt_hit_ghosts", None)
    if not ghosts:
        return
    for g in ghosts:
        g["timer"] -= 1
    play.grunt_hit_ghosts = [g for g in ghosts if g["timer"] > 0]


def run_gameplay_entities_phase() -> None:
    core = frame_core()
    play = core.play
    player = core.player
    screen = core.screen
    state = core.state
    WIDTH = core.width
    HEIGHT = core.height
    player_dead = play.player_dead
    boss_score_tally = play.boss_score_tally

    if state in (ENDING, EXTRA_PLAY) or boss_score_tally.active:
        return

    enemies = play.enemies
    turrets = play.turrets
    enemy_bullets = play.enemy_bullets
    from game_loop.enemy_shoot import try_enemy_shoot

    _tick_grunt_ghosts(play)

    for enemy in enemies[:]:
        enemy.update()
        enemy.draw(screen)
        try_enemy_shoot(enemy)
        if (
            not player_dead
            and player.invincible_timer == 0
            and getattr(enemy, "charge", False)
        ):
            from combat import apply_player_hit, enemy_body_hits_player

            if enemy_body_hits_player(player, enemy):
                apply_player_hit(hit_kind="grunt")

        from grunt_behavior import grunt_should_remove

        if grunt_should_remove(enemy, WIDTH) or enemy.rect.right < 0:
            if enemy in enemies:
                enemies.remove(enemy)

    for turret in turrets[:]:
        turret["rect"].x -= 4
        if turret["rect"].x < WIDTH + 100 and turret["rect"].x > -100:
            screen.blit(turret["image"], (turret["rect"].x, turret["rect"].y))

        turret["shot_timer"] += 1
        if turret["shot_timer"] >= 110:
            turret["shot_timer"] = 0
            from enemy_bullets import spawn_enemy_bullet
            from settings import TURRET_BULLET_SPEED

            dx = player.rect.centerx - turret["rect"].centerx
            fire_y = turret["rect"].bottom if turret["is_top"] else turret["rect"].top
            dy = player.rect.centery - fire_y
            dist = max(1.0, math.hypot(dx, dy))
            spd = float(TURRET_BULLET_SPEED)
            spawn_enemy_bullet(
                x=float(turret["rect"].centerx),
                y=float(fire_y),
                vx=(dx / dist) * spd,
                vy=(dy / dist) * spd,
                homing=True,
                image_type="turret_homing",
            )

        if turret["rect"].right < 0:
            turrets.remove(turret)
