# game_loop/world_updates.py — エンディング演出・隕石・レーザー・アイテム・爆発

from __future__ import annotations

import math
import random

from combat import (
    apply_player_hit,
    enemy_laser_hazard_active_in_play,
    zako_explosion_hits_player_sprite,
)
from enemy_bullets import update_enemy_bullets_frame
from explosion import Explosion
from game_constants import EMS_MAX
from game_loop.resources import frame_core_with_app, item_pickup_sfx, ui_message
from game_runtime import RT
from extra_boss import _extra_boss_hazards_disabled
from extra_boss_victory import is_extra_victory_active
from screen_modes import ENDING
from meteors import update_meteors_frame
from score_system import scaled_score
from settings import PLAYER_MAX_WEAPON_LEVEL, SPEED_GAUGE_MAX


def run_world_updates_phase() -> None:
    g = RT.g()
    core = frame_core_with_app()
    play = core.play
    app = core.app
    player = core.player
    screen = core.screen
    diff = core.diff
    state = core.state
    WIDTH = core.width
    HEIGHT = core.height
    pickup_sfx = item_pickup_sfx()
    bubble = ui_message().bubble
    boss = play.boss
    boss_active = play.boss_active
    player_dead = play.player_dead
    lives = play.lives
    ending_delay_timer = play.ending_delay_timer
    score_chain = play.score_chain
    enemy_lasers = play.enemy_lasers
    power_items = play.power_items
    explosions = play.explosions
    ems_count = play.ems_count

    FPS = g["FPS"]
    explosion_sound = pickup_sfx.explosion
    _bubble = bubble
    item_weapon_sound = pickup_sfx.weapon
    item_shield_sound = pickup_sfx.shield
    item_speed_sound = pickup_sfx.speed
    ems_get_sound = pickup_sfx.ems_get

    extra_victory = is_extra_victory_active(play)
    extra_phase = getattr(play, "extra_victory_phase", "")
    extra_hazards_off = _extra_boss_hazards_disabled(play, boss)
    frozen = (
        state == ENDING
        or play.boss_score_tally.active
        or play.b5_death_active
        or ending_delay_timer > 0
        or (extra_victory and extra_phase != "explode")
    )

    if ending_delay_timer > 0:
        if ending_delay_timer % 10 == 0:
            explosion_sound.play()
            if boss:
                play.explosions.append(
                    Explosion(
                        boss.rect.centerx + random.randint(-150, 150),
                        boss.rect.top + random.randint(0, boss.rect.height),
                        big=True,
                    )
                )
            else:
                play.explosions.append(
                    Explosion(
                        WIDTH - 200 + random.randint(-150, 150),
                        HEIGHT // 2 + random.randint(-150, 150),
                        big=True,
                    )
                )
        play.set("ending_delay_timer", ending_delay_timer - 1)

    if frozen:
        for ex in explosions[:]:
            ex.update()
            ex.draw(screen)
            if ex.dead():
                if ex in explosions:
                    explosions.remove(ex)
        return

    update_meteors_frame(state, player_dead, player, boss_active, boss)

    laser_play_top = g.get("PLAY_TOP_MARGIN", 12)
    laser_play_bottom = HEIGHT - 10
    for el in enemy_lasers[:]:
        el.life -= 1
        if el.life <= 0:
            if el in enemy_lasers:
                enemy_lasers.remove(el)
            continue

        if (
            getattr(el, "beam_track_boss", False)
            and boss_active
            and boss
            and boss.boss_type == 3
        ):
            el.rect.midleft = (boss.rect.left - 12, boss.rect.centery)
            if not player_dead:
                ax = float(el.rect.centerx)
                ay = float(el.rect.centery)
                target = math.atan2(
                    player.rect.centery - ay, player.rect.centerx - ax
                )
                target = max(math.radians(158), min(math.radians(202), target))
                cur = getattr(el, "beam_angle", target)
                steer_delta = (target - cur + math.pi) % (2 * math.pi) - math.pi
                cur = cur + steer_delta * 0.045
                cur = max(math.radians(158), min(math.radians(202), cur))
                el.beam_angle = cur
                el.angle = cur
        else:
            el.rect.x += int(el.vx)
            el.rect.y += int(el.vy)

        if not getattr(el, "beam_no_bounce", False):
            if el.rect.top <= laser_play_top:
                el.rect.top = laser_play_top + 1
                el.vy = abs(el.vy) if abs(el.vy) > 1.5 else 6.0
            elif el.rect.bottom >= laser_play_bottom:
                el.rect.bottom = laser_play_bottom - 1
                el.vy = -abs(el.vy) if abs(el.vy) > 1.5 else -6.0

        if state != ENDING:
            el.draw(screen)

        if (
            not extra_hazards_off
            and not player_dead
            and player.invincible_timer == 0
        ):
            from combat import enemy_laser_hits_player_sprite

            if enemy_laser_hazard_active_in_play(el, WIDTH, HEIGHT) and (
                enemy_laser_hits_player_sprite(player, el)
            ):
                apply_player_hit(hit_kind="grunt")
                if el in enemy_lasers:
                    enemy_lasers.remove(el)
                continue

        if getattr(el, "laser_variant", "") == "purple_ground_crescent":
            if el in enemy_lasers:
                enemy_lasers.remove(el)
            continue

        if not getattr(el, "beam_track_boss", False):
            cull_x = -40 if (
                getattr(el, "extra_beam_cutter", False)
                or getattr(el, "extra_funnel_snipe", False)
            ) else -80
            if el.rect.right < cull_x or el.rect.left > WIDTH + 80:
                if el in enemy_lasers:
                    enemy_lasers.remove(el)

    update_enemy_bullets_frame(
        state, player_dead, player, diff, play.boss_fight_timer
    )

    for item in power_items[:]:
        item.update()
        item.draw(screen)
        from combat import pickup_hits_player

        if not player_dead and pickup_hits_player(player, item):
            if item.type == "weapon":
                prev = int(getattr(player, "weapon_level", 1))
                if prev < PLAYER_MAX_WEAPON_LEVEL:
                    player.weapon_level = min(PLAYER_MAX_WEAPON_LEVEL, prev + 1)
                    if int(player.weapon_level) >= PLAYER_MAX_WEAPON_LEVEL:
                        try:
                            player.on_unlock_laser()
                            _bubble.show("laser_equipped")
                        except Exception:
                            pass
                else:
                    # Lv5以降はレーザーゲージ補給
                    try:
                        player.refill_laser_gauge()
                    except Exception:
                        pass
                item_weapon_sound.play()
                _bubble.show("weapon_up")
            elif item.type == "laser_charge":
                try:
                    from settings import LASER_GAUGE_MAX

                    player.refill_laser_gauge(float(LASER_GAUGE_MAX))
                except Exception:
                    pass
                item_weapon_sound.play()
                _bubble.show("weapon_mode_laser")
            elif item.type == "shield":
                from settings import PLAYER_SHIELD_ITEM_FILL

                player.shield_meter = min(
                    1.0, float(getattr(player, "shield_meter", 0.0)) + PLAYER_SHIELD_ITEM_FILL
                )
                item_shield_sound.play()
                _bubble.show("shield_up")
            elif item.type == "speed":
                # 速度はゲージ制（維持は緩め）
                try:
                    player.refill_speed_gauge()
                except Exception:
                    pass
                item_speed_sound.play()
                _bubble.show("speed_up")
            elif item.type == "super":
                # スーパーアイテム: シールドとスピードを即最大化
                player.shield_meter = 1.0
                player.speed_gauge = float(SPEED_GAUGE_MAX)
                item_shield_sound.play()
                item_speed_sound.play()
                _bubble.show_text("SUPER! SHIELD&SPEED MAX", priority=4)
            elif item.type == "1up":
                lives_cap = diff.player_lives + 2
                if lives < lives_cap:
                    play.set("lives", lives + 1)
                    play.set("_prev_lives", lives + 1)
                    item_weapon_sound.play()
                    _bubble.show("1up")
            elif item.type == "ems":
                if ems_count < EMS_MAX:
                    play.set("ems_count", ems_count + 1)
                ems_get_sound.play()
                _bubble.show("ems_get")
            play.add_score(scaled_score(500, diff, score_chain.multiplier()))
            if item in power_items:
                power_items.remove(item)
            continue
        if item.rect.right < 0:
            if item in power_items:
                power_items.remove(item)

    for ex in explosions[:]:
        ex.update()
        ex.draw(screen)
        if (
            not extra_hazards_off
            and not player_dead
            and player.invincible_timer == 0
            and getattr(ex, "damages_player", False)
            and zako_explosion_hits_player_sprite(player, ex)
        ):
            apply_player_hit(hit_kind="grunt")
        if ex.dead():
            if ex in explosions:
                explosions.remove(ex)
