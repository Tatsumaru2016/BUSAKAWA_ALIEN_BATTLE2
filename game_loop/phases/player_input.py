# game_loop/phases/player_input.py — 自機入力・描画・連射

import math

import pygame

from bullet import Bullet
from boss5_attack_patterns import get_gravity_player_speed_scale
from boss5_support import (
    draw_boss5_support,
    get_support_fighter,
    is_boss5_support_allowed,
    support_fighter_rect,
    update_boss5_support,
)
from extra_boss_victory import (
    get_extra_victory_speech_anchor,
    is_extra_ending_cinematic,
    is_extra_victory_active,
    is_extra_victory_blocking,
)
from extra_stage_support import get_extra_support_bubble_anchor
from audio import update_boss5_hp_bgm
from game_constants import EMS_MAX
from game_flow import player_can_fire
from game_loop.resources import frame_core, player_input_bundle
from game_runtime import RT
from player_fire_mode import notify_laser_gauge_after_shot
from player_status_ui import (
    draw_player_bracket_back,
    draw_player_bracket_front,
    draw_player_shield_aura,
)
from screen_modes import ENDING, ENDING_EXTRA_DIVE, EXTRA_PLAY, PLAY

_PLAY_LIKE = (PLAY, EXTRA_PLAY)


def run_player_input_phase() -> None:
    core = frame_core()
    play = core.play
    player = core.player
    screen = core.screen
    state = core.state
    WIDTH = core.width
    HEIGHT = core.height
    inp = player_input_bundle()
    boss = play.boss
    boss_active = play.boss_active
    player_dead = play.player_dead
    lives = play.lives
    revive_timer = play.revive_timer
    ending_delay_timer = play.ending_delay_timer
    boss_score_tally = play.boss_score_tally
    bullets = play.bullets
    _shot_timer = play._shot_timer
    _boss_special_alert_timer = play._boss_special_alert_timer

    KEY_BINDINGS = inp.keys
    font = inp.font
    _bubble = inp.bubble
    shot_sound = inp.shot_sound
    support_fighter_images = inp.support_fighter_images
    bullet_img = inp.bullet_img
    support_arrive_sound = inp.support_arrive_sound
    joy_move_up = inp.joy_move_up
    joy_move_down = inp.joy_move_down
    joy_move_left = inp.joy_move_left
    joy_move_right = inp.joy_move_right
    joy_shoot = inp.joy_shoot
    SHOT_INTERVAL = inp.shot_interval

    if player.invincible_timer > 0:
        player.invincible_timer -= 1

    if play.boss_fight_active and lives < play._prev_lives:
        play.set("no_damage_since_boss", False)
    play.set("_prev_lives", lives)

    if player_dead and revive_timer > 0:
        if lives <= 0:
            play.set("revive_timer", 0)
        else:
            new_revive_timer = revive_timer - 1
            play.set("revive_timer", new_revive_timer)
            if new_revive_timer <= 0:
                play.set("player_dead", False)
                player.rect.x = 120
                player.rect.y = HEIGHT // 2
                player.invincible_timer = 180
                _bubble.show("revive")

    if (
        ending_delay_timer == 0
        and state in _PLAY_LIKE
        and not boss_score_tally.active
        and not play.b5_death_active
        and not is_extra_victory_blocking(play)
    ):
        keys = pygame.key.get_pressed()
        joy_funcs = {
            "up": joy_move_up,
            "down": joy_move_down,
            "left": joy_move_left,
            "right": joy_move_right,
        }
        shoot_key = keys[KEY_BINDINGS["shoot"]]
        shoot_joy = joy_shoot()
        allow_fire = player_can_fire(play, boss)
        firing = allow_fire and (shoot_key or shoot_joy)
        player_speed_saved = player.speed
        if boss_active and boss and boss.boss_type == 5:
            player.speed = max(
                1,
                int(player_speed_saved * get_gravity_player_speed_scale(boss)),
            )
        player.update(
            keys,
            WIDTH,
            HEIGHT,
            joy_funcs=joy_funcs,
            key_bindings=KEY_BINDINGS,
            firing=firing,
        )
        if boss_active and boss and boss.boss_type == 5:
            player.speed = player_speed_saved
    elif not is_extra_victory_active(play):

        class FakeKeys:
            def __getitem__(self, key):
                return False

        player.update(FakeKeys(), WIDTH, HEIGHT)

    if state == PLAY and ending_delay_timer == 0 and is_boss5_support_allowed(play):
        update_boss5_support(
            player,
            player_dead,
            boss,
            boss_active,
            bullets,
            bullet_img,
            support_fighter_images,
            _bubble,
            WIDTH,
            HEIGHT,
            Bullet,
            support_arrive_sound,
        )
        update_boss5_hp_bgm(boss)

    if (
        state in _PLAY_LIKE
        and not player_dead
        and ending_delay_timer == 0
        and player_can_fire(play, boss)
    ):
        _shot_timer = max(0, _shot_timer - 1)

        if firing and _shot_timer == 0:
            _shot_timer = SHOT_INTERVAL
            shot_sound.play()
            player.apply_fire_feedback()
            new_bullets = player.shoot()
            used_laser = False
            for b in new_bullets:
                if getattr(b, "is_laser", False):
                    used_laser = True
                    b.life = 180
                    if shoot_key and pygame.key.get_pressed()[pygame.K_RIGHT]:
                        spd_boost = float(player.speed)
                        cur_spd = math.hypot(b.vx, b.vy)
                        if cur_spd > 0.1:
                            new_spd = cur_spd + spd_boost
                            b.vx = b.vx / cur_spd * new_spd
                            b.vy = b.vy / cur_spd * new_spd
            if used_laser:
                player.drain_laser_gauge_for_shot()
                notify_laser_gauge_after_shot(player, _bubble)
            bullets.extend(new_bullets)

        play.set("_shot_timer", _shot_timer)

    extra_gallery = is_extra_ending_cinematic(play)
    if (
        not player_dead
        and state not in (ENDING, ENDING_EXTRA_DIVE)
        and not boss_score_tally.active
        and not extra_gallery
    ):
        draw_player_bracket_back(screen, player)
        meter = float(getattr(player, "shield_meter", 0.0))
        if meter > 0.001:
            draw_player_shield_aura(screen, player, meter)
        if player.invincible_timer == 0 or (player.invincible_timer // 4) % 2 == 0:
            player.draw(screen)
        draw_player_bracket_front(screen, player, play.ems_count, EMS_MAX)

    if state == PLAY:
        draw_boss5_support(screen, play)

    if not player_dead and state not in (ENDING, ENDING_EXTRA_DIVE) and not extra_gallery:
        if state == PLAY:
            sf = get_support_fighter() if is_boss5_support_allowed(play) else None
            support_bubble_anchor = (
                support_fighter_rect(sf) if sf is not None else None
            )
            _bubble.update_and_draw(screen, player.rect, support_bubble_anchor)
        elif state == EXTRA_PLAY:
            if is_extra_victory_active(play):
                support_bubble_anchor = get_extra_victory_speech_anchor(play)
            else:
                support_bubble_anchor = get_extra_support_bubble_anchor(play)
            _bubble.update_and_draw(screen, player.rect, support_bubble_anchor)

        if state in _PLAY_LIKE and _boss_special_alert_timer > 0:
            _boss_special_alert_timer -= 1
            alert_alpha = (
                255
                if _boss_special_alert_timer > 10
                else int(255 * _boss_special_alert_timer / 10)
            )
            alert_visible = True
            if (
                _boss_special_alert_timer > 20
                and (_boss_special_alert_timer // 4) % 2 == 0
            ):
                alert_visible = False
            if alert_visible:
                from settings import PLAY_TOP_MARGIN

                top_m = PLAY_TOP_MARGIN
                ax = max(top_m, min(WIDTH - top_m, player.rect.centerx + 24))
                ay = max(top_m, min(HEIGHT - top_m, player.rect.top - 44))
                alert_bg = pygame.Surface((34, 34), pygame.SRCALPHA)
                pygame.draw.circle(alert_bg, (200, 0, 0, alert_alpha), (17, 17), 17)
                pygame.draw.circle(
                    alert_bg,
                    (255, 80, 80, min(255, alert_alpha + 60)),
                    (17, 17),
                    17,
                    2,
                )
                screen.blit(alert_bg, (ax - 9, ay - 9))
                alert_surf = font.render("!", True, (255, 255, 255))
                alert_surf.set_alpha(alert_alpha)
                alert_rect = alert_surf.get_rect(center=(ax + 8, ay + 8))
                screen.blit(alert_surf, alert_rect)

            play.set("_boss_special_alert_timer", _boss_special_alert_timer)
