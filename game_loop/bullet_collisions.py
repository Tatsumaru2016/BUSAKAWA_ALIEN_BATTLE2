# game_loop/bullet_collisions.py — 自機弾の移動・衝突

from __future__ import annotations

import math
import random

import pygame

from boss5_shield import shield_meteor_blocks_bullet
from boss_attacks.boss4_kraken import (
    bullet_hits_boss4_overlays,
    bullet_hits_boss4_shield_block,
)
from combat import (
    bullet_damage_to_boss,
    bullet_hits_boss_visible_pixels,
    bullet_hits_enemy_bullet_visual,
    bullet_hits_enemy_sprite,
    bullet_hits_turret_sprite,
)
from enemy_bullets import enemy_bullet_destructible_by_player, spawn_enemy_bullet
from explosion import Explosion, GruntExplosion
from settings import is_enemy_ace_type, is_enemy_special_type
from game_loop.resources import (
    battle_collision_sfx,
    frame_core,
    powerup_images,
)
from game_runtime import RT
from screen_modes import ENDING, ENDING_EXTRA_DIVE
from item_drops import roll_power_item_type
from powerup import PowerItem


def _reflect_laser(bullet) -> bool:
    """レーザーをランダム方向に反射。3回目で消滅なら True。"""
    bullet.bounce_count += 1
    if bullet.bounce_count >= 3:
        return True
    angles = [0, 45, 90, 135, 180, 225, 270, 315]
    rad = math.radians(random.choice(angles))
    spd = max(math.hypot(bullet.vx, bullet.vy), 12.0)
    bullet.vx = math.cos(rad) * spd
    bullet.vy = math.sin(rad) * spd
    return False


def _laser_motion(bullet, height: int) -> bool:
    """レーザー移動。画面外・寿命切れなら True（弾を削除済み）。"""
    core = frame_core()
    bullets = core.play.bullets
    width = core.width

    if bullet.life <= 0:
        if bullet in bullets:
            bullets.remove(bullet)
        return True

    bullet.rect.x += int(bullet.vx)
    bullet.rect.y += int(bullet.vy)

    laser_play_top = RT.g().get("PLAY_TOP_MARGIN", 12)
    laser_play_bottom = height - 10
    if bullet.rect.top <= laser_play_top:
        bullet.rect.top = laser_play_top + 1
        bullet.vy = abs(bullet.vy) if abs(bullet.vy) > 0.5 else 6.0
        bullet.bounce_count += 1
        if bullet.bounce_count >= 2:
            if bullet in bullets:
                bullets.remove(bullet)
            return True
    elif bullet.rect.bottom >= laser_play_bottom:
        bullet.rect.bottom = laser_play_bottom - 1
        bullet.vy = -abs(bullet.vy) if abs(bullet.vy) > 0.5 else -6.0
        bullet.bounce_count += 1
        if bullet.bounce_count >= 2:
            if bullet in bullets:
                bullets.remove(bullet)
            return True

    if bullet.rect.right < 0 or bullet.rect.left > width:
        if bullet in bullets:
            bullets.remove(bullet)
        return True
    return False


def _other_bullet_motion(bullet, height: int) -> None:
    width = RT.g()["WIDTH"]
    if getattr(bullet, "lane_crawl", None):
        lane_top = RT.g().get("PLAY_TOP_MARGIN", 12)
        lane_bottom = height - 10
        if not bullet.lane_active:
            bullet.rect.y += int(bullet.custom_vy)
            if bullet.lane_crawl == "top" and bullet.rect.top <= lane_top:
                bullet.rect.top = lane_top
                bullet.lane_active = True
            elif bullet.lane_crawl == "bottom" and bullet.rect.bottom >= lane_bottom:
                bullet.rect.bottom = lane_bottom
                bullet.lane_active = True
        else:
            bullet.rect.x += int(bullet.speed)
    elif hasattr(bullet, "custom_vy"):
        bullet.rect.y += int(bullet.custom_vy)
        bullet.rect.x += 12

    if bullet.rect.left > width + 150 or bullet.rect.right < -150:
        bullets = RT.g()["play"].bullets
        if bullet in bullets:
            bullets.remove(bullet)


def _show_player_bubble(key: str) -> None:
    try:
        RT.g()["_bubble"].show(key)
    except Exception:
        pass


def _on_enemy_kill(play, diff, enemy, explosions, explosion_sound, power_items, pimgs):
    from grunt_behavior import make_death_ghost, spawn_death_scatter

    if not getattr(enemy, "grunt_behavior", None):
        spawn_death_scatter(enemy, float(diff.enemy_bullet_spd))
    ghosts = getattr(play, "grunt_hit_ghosts", None)
    if ghosts is None:
        play.grunt_hit_ghosts = []
        ghosts = play.grunt_hit_ghosts
    ghosts.append(make_death_ghost(enemy))

    if getattr(enemy, "grunt_behavior", None):
        zako_img = RT.g().get("explosion_zako_img")
        if zako_img is not None:
            explosions.append(
                GruntExplosion(enemy.rect.centerx, enemy.rect.centery, zako_img)
            )
        else:
            explosions.append(
                Explosion(enemy.rect.centerx, enemy.rect.centery, big=True)
            )
        explosion_sound.play()
    elif enemy.type == 1:
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, big=True))
        explosion_sound.play()
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            spawn_enemy_bullet(
                x=enemy.rect.centerx,
                y=enemy.rect.centery,
                vx=math.cos(rad) * 3.5,
                vy=math.sin(rad) * 3.5,
                image_type="normal",
            )
    elif is_enemy_special_type(enemy.type) or getattr(enemy, "special_leader", False):
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, big=True))
        explosion_sound.play()
    elif is_enemy_ace_type(enemy.type) or getattr(enemy, "ace_leader", False):
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, big=True))
        explosion_sound.play()
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            spawn_enemy_bullet(
                x=enemy.rect.centerx,
                y=enemy.rect.centery,
                vx=math.cos(rad) * 3.2,
                vy=math.sin(rad) * 3.2,
                image_type="normal",
            )
    elif enemy.type == 3 and getattr(enemy, "variant", 0) in (0, 2):
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, big=True))
        explosion_sound.play()
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            spawn_enemy_bullet(
                x=enemy.rect.centerx,
                y=enemy.rect.centery,
                vx=math.cos(rad) * 4.0,
                vy=math.sin(rad) * 4.0,
                image_type="normal",
            )
    else:
        explosions.append(Explosion(enemy.rect.centerx, enemy.rect.centery, big=False))

    ace_kill = bool(
        getattr(enemy, "ace_leader", False)
        or is_enemy_ace_type(getattr(enemy, "type", -1))
        or getattr(enemy, "grunt_behavior", None) == "ace"
    )
    if ace_kill:
        play.add_score(play.score_chain.score_ace_kill(diff))
    else:
        play.add_score(play.score_chain.score_enemy_kill(diff))
    play.add_kill()
    if enemy in play.enemies:
        play.enemies.remove(enemy)

    if is_enemy_special_type(getattr(enemy, "type", -1)) or getattr(
        enemy, "special_leader", False
    ):
        try:
            frame_core().player.apply_special_kill_bonus()
        except Exception:
            pass
        _show_player_bubble("special_kill")
        return

    if ace_kill:
        _show_player_bubble("ace_kill")
        ace_item_type = random.choice(("laser_charge", "super"))
        power_items.append(
            PowerItem(
                enemy.rect.centerx,
                enemy.rect.centery,
                ace_item_type,
                pimgs.power_type_map()[ace_item_type],
            )
        )
        return

    drop_roll = random.randint(0, 99)
    one_up_pct = getattr(diff, "drop_1up_pct", 2)
    item_pct = getattr(diff, "drop_item_pct", 45)
    if drop_roll < one_up_pct:
        power_items.append(
            PowerItem(
                enemy.rect.centerx, enemy.rect.centery, "1up", pimgs.one_up
            )
        )
    elif drop_roll < one_up_pct + item_pct:
        player = RT.g()["player"]
        item_type = roll_power_item_type(player)
        img = pimgs.power_type_map()[item_type]
        power_items.append(
            PowerItem(enemy.rect.centerx, enemy.rect.centery, item_type, img)
        )


def _resolve_bullet_hit(bullet, is_laser, bullets) -> tuple[bool, bool]:
    """(bullet_removed, laser_reflected)"""
    if is_laser:
        if _reflect_laser(bullet):
            if bullet in bullets:
                bullets.remove(bullet)
            return True, False
        return False, True
    if bullet in bullets:
        bullets.remove(bullet)
    return True, False


def run_bullet_collisions_phase() -> None:
    core = frame_core()
    play = core.play
    state = core.state
    diff = core.diff
    player_dead = play.player_dead
    boss_score_tally = play.boss_score_tally

    if (
        player_dead
        or state in (ENDING, ENDING_EXTRA_DIVE)
        or boss_score_tally.active
        or play.b5_death_active
        or getattr(play, "extra_victory_active", False)
    ):
        return

    screen = core.screen
    height = core.height
    width = core.width
    hit_sfx = battle_collision_sfx()
    bullets = play.bullets
    enemy_bullets = play.enemy_bullets
    enemies = play.enemies
    turrets = play.turrets
    meteors = play.meteors
    explosions = play.explosions
    power_items = play.power_items
    boss = play.boss
    boss_active = play.boss_active
    boss_shield_hp = play.boss_shield_hp
    score_chain = play.score_chain
    explosion_sound = hit_sfx.explosion_sound
    boss_shield_hit_sound = hit_sfx.boss_shield_hit_sound
    boss_shield_break_sound = hit_sfx.boss_shield_break_sound
    pimgs = powerup_images()

    for bullet in bullets[:]:
        is_laser = getattr(bullet, "is_laser", False)
        bullet.update()

        if is_laser:
            if _laser_motion(bullet, height):
                continue
        else:
            _other_bullet_motion(bullet, height)
            if bullet not in bullets:
                continue
            if not is_laser and hasattr(bullet, "life") and bullet.life <= 0:
                bullets.remove(bullet)
                continue

        bullet.draw(screen)

        if bullet not in bullets:
            continue

        bullet_removed = False
        laser_reflected = False

        for eb in enemy_bullets[:]:
            if eb.get("indestructible"):
                continue
            is_curtain = eb.get("attack_type") == "b1_tentacle_curtain"
            is_b1_ripple = eb.get("attack_type") == "b1_diagonal_ripple"
            if (
                eb.get("is_boss_bullet", False)
                and not is_curtain
                and not is_b1_ripple
                and not enemy_bullet_destructible_by_player(eb)
            ):
                continue
            if not bullet_hits_enemy_bullet_visual(bullet, eb):
                continue

            explosions.append(Explosion(eb["x"], eb["y"], big=False))
            eb_hp = int(eb.get("hp", 1))
            dmg = max(1, getattr(bullet, "damage", 1))
            if is_curtain:
                eb["state"] = "retract"
                if eb_hp > dmg:
                    eb["hp"] = eb_hp - dmg
                    bullet_removed, laser_reflected = _resolve_bullet_hit(
                        bullet, is_laser, bullets
                    )
                    break
                eb["hp"] = 0
                eb["state"] = "retract"
                bullet_removed, laser_reflected = _resolve_bullet_hit(
                    bullet, is_laser, bullets
                )
                break
            if eb_hp > 1:
                eb["hp"] = eb_hp - dmg
                if eb["hp"] > 0:
                    bullet_removed, laser_reflected = _resolve_bullet_hit(
                        bullet, is_laser, bullets
                    )
                    break
            if eb in enemy_bullets:
                enemy_bullets.remove(eb)
            bullet_removed, laser_reflected = _resolve_bullet_hit(
                bullet, is_laser, bullets
            )
            break

        if bullet_removed or laser_reflected or bullet not in bullets:
            continue

        ghosts = getattr(play, "grunt_hit_ghosts", None) or []
        for ghost in ghosts:
            gr = ghost["rect"]
            if bullet.rect.colliderect(gr):
                bullet_removed, laser_reflected = _resolve_bullet_hit(
                    bullet, is_laser, bullets
                )
                break
        if bullet_removed or laser_reflected or bullet not in bullets:
            continue

        for enemy in enemies[:]:
            if not bullet_hits_enemy_sprite(bullet, enemy):
                continue
            from grunt_behavior import (
                apply_grunt_bullet_damage,
                grunt_damage_allowed,
                grunt_invulnerable,
            )

            if grunt_invulnerable(enemy):
                continue
            if getattr(enemy, "grunt_behavior", None) and not grunt_damage_allowed(
                enemy, width
            ):
                continue
            dmg = bullet.damage
            if getattr(enemy, "grunt_behavior", None):
                dmg = apply_grunt_bullet_damage(enemy, dmg)
                if dmg <= 0:
                    bullet_removed, laser_reflected = _resolve_bullet_hit(
                        bullet, is_laser, bullets
                    )
                    break
            enemy.hp -= dmg
            is_grunt = bool(getattr(enemy, "grunt_behavior", None))
            if not is_grunt:
                explosions.append(
                    Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
                )
            bullet_removed, laser_reflected = _resolve_bullet_hit(
                bullet, is_laser, bullets
            )
            if enemy.hp <= 0:
                _on_enemy_kill(
                    play, diff, enemy, explosions, explosion_sound, power_items, pimgs
                )
            break

        if bullet_removed or laser_reflected or bullet not in bullets:
            continue

        for turret in turrets[:]:
            if not bullet_hits_turret_sprite(bullet, turret):
                continue
            turret["hp"] -= bullet.damage
            explosions.append(
                Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
            )
            bullet_removed, laser_reflected = _resolve_bullet_hit(
                bullet, is_laser, bullets
            )
            if turret["hp"] <= 0:
                explosion_sound.play()
                explosions.append(
                    Explosion(
                        turret["rect"].centerx, turret["rect"].centery, big=True
                    )
                )
                play.add_score(play.score_chain.score_turret_kill(diff))
                turrets.remove(turret)
            break

        if bullet_removed or laser_reflected or bullet not in bullets:
            continue

        if boss_active and boss and boss.boss_type == 5:
            from meteors import meteor_blocks_player_bullet

            for m in meteors[:]:
                if m.get("b5_shield"):
                    continue
                if not meteor_blocks_player_bullet(bullet, m):
                    continue
                m_hp = int(m.get("hp", 1))
                dmg = max(1, bullet_damage_to_boss(bullet, boss))
                explosions.append(
                    Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
                )
                bullet_removed, laser_reflected = _resolve_bullet_hit(
                    bullet, is_laser, bullets
                )
                if m_hp > dmg:
                    m["hp"] = m_hp - dmg
                    break
                explosions.append(Explosion(int(m["x"]), int(m["y"]), big=True))
                if m in meteors:
                    meteors.remove(m)
                break
            if bullet_removed or laser_reflected or bullet not in bullets:
                continue

            for m in meteors[:]:
                if not m.get("b5_shield"):
                    continue
                if not shield_meteor_blocks_bullet(bullet, m):
                    continue
                m["hp"] = m.get("hp", 1) - bullet_damage_to_boss(bullet, boss)
                boss_shield_hit_sound.play()
                explosions.append(
                    Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
                )
                bullet_removed, laser_reflected = _resolve_bullet_hit(
                    bullet, is_laser, bullets
                )
                if m["hp"] <= 0:
                    explosions.append(Explosion(int(m["x"]), int(m["y"]), big=True))
                    if m in meteors:
                        meteors.remove(m)
                    shield_left = sum(1 for _m in meteors if _m.get("b5_shield"))
                    if not shield_left and not getattr(boss, "b5_shield_stashed", False):
                        boss_shield_break_sound.play()
                break
            if bullet_removed or laser_reflected or bullet not in bullets:
                continue

        if boss_active and boss:
            if boss.boss_type == 6 and boss.hp <= 0:
                if bullet in bullets:
                    bullets.remove(bullet)
                continue
            if boss.boss_type == 4 and boss_shield_hp > 0:
                if not bullet_hits_boss4_shield_block(bullet, boss):
                    continue
            elif not bullet_hits_boss_visible_pixels(bullet, boss):
                if boss.boss_type != 4 or not bullet_hits_boss4_overlays(
                    bullet, boss
                ):
                    continue
            if boss_shield_hp > 0:
                b5_dmg = bullet_damage_to_boss(bullet, boss)
                play.set("boss_shield_hp", boss_shield_hp - b5_dmg)
                play.explosions.append(
                    Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
                )
                boss_shield_hit_sound.play()
                if is_laser:
                    if _reflect_laser(bullet):
                        if bullet in bullets:
                            bullets.remove(bullet)
                elif bullet in bullets:
                    bullets.remove(bullet)

                if play.boss_shield_hp <= 0:
                    play.set("boss_shield_hp", 0)
                    boss_shield_break_sound.play()
                    play.set("boss_shield_grace_timer", diff.shield_grace_f)
                    if boss.boss_type == 4:
                        from boss_attacks.boss4_kraken import reset_boss4_tentacles

                        reset_boss4_tentacles(boss)
                    boss.shot_timer = 5 if boss.boss_type == 5 else 0
                    for _ in range(8):
                        explosions.append(
                            Explosion(
                                boss.rect.left + random.randint(-10, 40),
                                boss.rect.top + random.randint(0, boss.rect.height),
                                big=True,
                            )
                        )
                continue

            b5_dmg = bullet_damage_to_boss(bullet, boss)
            boss.hp -= b5_dmg
            score_chain.add_boss_hit(diff, b5_dmg, diff.boss_hit_score)
            if boss.boss_type == 6 and boss.hp <= 0:
                from extra_boss_victory import try_extra_boss_defeat

                try_extra_boss_defeat(play, boss)
            if is_laser:
                if _reflect_laser(bullet) and bullet in bullets:
                    bullets.remove(bullet)
            elif bullet in bullets:
                bullets.remove(bullet)
            explosions.append(
                Explosion(bullet.rect.centerx, bullet.rect.centery, big=False)
            )
