# boss_spawn.py — ボス警告〜出現（Phase 4）

from __future__ import annotations

import math

from midboss import MidBoss
from game_runtime import RT
from settings import (
    BOSS1_BASE_HP,
    BOSS1_BASE_SHIELD,
    BOSS2_BASE_HP,
    BOSS2_BASE_SHIELD,
    BOSS3_BASE_HP,
    BOSS3_BASE_SHIELD,
    BOSS4_BASE_HP,
    BOSS4_BASE_SHIELD,
)
from boss5_update import calc_boss5_max_hp, B5_SIN_ANCHOR_X, B5_SIN_ANCHOR_Y
from boss5_support import clear_boss5_support, init_boss5_support_fight
from boss_attacks.boss4_kraken import (
    BOSS4_SPAWN_RIGHT_OVERFLOW,
    sync_boss4_body_layout,
)
from boss5_shield import init_boss5_shield_attrs
from audio import start_boss5_bgm, start_boss_bgm


BOSS_WARNING_DURATION_FRAMES = 180
# 点滅: ON/OFF 各18f（60fpsで約0.3秒）
BOSS_WARNING_BLINK_HALF_FRAMES = 18


def scaled_boss_max_hp(base_hp: int, diff, boss_type: int) -> int:
    """難易度の boss_hp_scale とボス別の追加倍率（例: EASY ボス3/4）を適用。"""
    hp = int(base_hp * diff.boss_hp_scale)
    if boss_type == 3:
        hp = int(hp * getattr(diff, "boss3_hp_mul", 1.0))
    elif boss_type == 4:
        hp = int(hp * getattr(diff, "boss4_hp_mul", 1.0))
    return max(1, hp)


def play_boss_warning_sfx(g, warning_sound, *, with_launch: bool = True) -> None:
    """WARNING効果音（必要なら launch も重ねる）。表示より先に呼ぶ。"""
    if warning_sound is None:
        return
    try:
        warning_sound.play()
    except Exception:
        pass
    if not with_launch:
        return
    try:
        launch = g.get("launch_sound")
        if launch is not None:
            launch.play()
    except Exception:
        pass


def boss_warning_blink_visible(timer: int) -> bool:
    """timer>0 のときのみ点滅ON区間で True（timer==0 は未表示）。"""
    if timer <= 0:
        return False
    return (timer // BOSS_WARNING_BLINK_HALF_FRAMES) % 2 == 0


def draw_boss_warning_overlay(screen, play, warning_img) -> None:
    if warning_img is None or not play.boss_warning:
        return
    if not boss_warning_blink_visible(int(play.boss_warning_timer)):
        return
    screen.blit(
        warning_img,
        warning_img.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)),
    )


def clear_boss_warning(play) -> None:
    play.set("boss_warning", False)
    play.set("boss_warning_timer", 0)
    play.set("boss_warning_pending", False)


def clear_stage_for_boss_entrance(play) -> None:
    """ボス出現時: 画面上の雑魚・雑魚弾・パワーアイテムを除去。"""
    play.enemies.clear()
    play.enemy_bullets.clear()
    play.power_items.clear()
    ghosts = getattr(play, "grunt_hit_ghosts", None)
    if ghosts is not None:
        ghosts.clear()
    try:
        from enemy_waves import reset_grunt_waves

        reset_grunt_waves(play)
    except Exception:
        play._grunt_wave = None
        if not hasattr(play, "grunt_hit_ghosts"):
            play.grunt_hit_ghosts = []


def begin_boss_warning(play, next_boss_type: int) -> None:
    play.set("boss_warning", True)
    play.set("boss_warning_timer", 0)
    play.set("boss_warning_pending", False)
    play.bullets.clear()
    play.enemy_lasers.clear()
    clear_stage_for_boss_entrance(play)
    start_boss_bgm(next_boss_type)
    if next_boss_type == 5:
        play.set("boss5_bg_mode", True)
    g = RT.g()
    play_boss_warning_sfx(g, g.get("warning_sound"))


def on_boss_warning_first_frame(play, next_boss_type: int) -> None:
    if next_boss_type != 5:
        clear_boss5_support()
    start_boss_bgm(next_boss_type)


def activate_boss_after_warning(play, boss_type: int, diff, player, width: int, height: int) -> None:
    """警告180f経過後: ボス出現と戦闘フラグをまとめて設定。"""
    g = RT.g()
    if boss_type != 5:
        clear_boss5_support()
    play.set("boss_warning", False)
    play.set("boss_warning_timer", 0)
    play.set("boss_warning_pending", False)
    play.set("boss_active", True)
    play.update(
        no_damage_since_boss=True,
        boss_fight_timer=0,
        boss_fight_active=True,
    )
    play.score_chain.begin_boss_fight(diff, boss_type)

    if boss_type == 1:
        boss = MidBoss(1, g["midboss_img1"])
        boss.rect = g["midboss_img1"].get_rect(topleft=(820, 150))
        boss.burst_count = 0
        boss.pattern_phase = 0
        boss.max_hp = int(BOSS1_BASE_HP * diff.boss_hp_scale)
        boss.hp = boss.max_hp
        shield = int(BOSS1_BASE_SHIELD * diff.boss_shield_scale)
        boss.move_timer = 0
        boss.low_hp_burst = 5
        boss.cooldown_timer = 0
        shield_max = shield
    elif boss_type == 2:
        boss = MidBoss(2, g["midboss_img2"])
        boss.rect = g["midboss_img2"].get_rect(topleft=(820, 150))
        boss.push_dir = -1
        boss.pattern_phase = 0
        boss.spiral_angle = 0.0
        boss.low_hp_burst = 5
        boss.cooldown_timer = 0
        boss.max_hp = int(BOSS2_BASE_HP * diff.boss_hp_scale)
        boss.hp = boss.max_hp
        shield = int(BOSS2_BASE_SHIELD * diff.boss_shield_scale)
        boss.move_timer = 0
        shield_max = shield
    elif boss_type == 3:
        boss = MidBoss(3, g["midboss_img3"])
        boss.rect = g["midboss_img3"].get_rect(topleft=(820, 150))
        boss.wave_angle = 0
        boss.max_hp = scaled_boss_max_hp(BOSS3_BASE_HP, diff, 3)
        boss.hp = boss.max_hp
        shield = int(BOSS3_BASE_SHIELD * diff.boss_shield_scale)
        boss.move_timer = 0
        shield_max = shield
    elif boss_type == 4:
        boss = MidBoss(4, g["midboss4_body_img"])
        sync_boss4_body_layout(boss)
        boss.max_hp = scaled_boss_max_hp(BOSS4_BASE_HP, diff, 4)
        boss.hp = boss.max_hp
        shield = int(BOSS4_BASE_SHIELD * diff.boss_shield_scale)
        shield_max = shield
        boss.arm_state = "idle"
        boss.arm_timer = 0
        boss.tentacle_len = 0.0
        boss.tentacle_target_y = height // 2
        boss.b4_idle_frame = 0
        boss.b4_idle_swap_timer = 0
        boss.b4_strip_sniper_cd = 60
        boss.b4_top_arm_state = "idle"
        boss.b4_top_arm_timer = 0
        boss.b4_top_tentacle_len = 0.0
        boss.b4_top_target_x = float(width) * 0.5
        boss.b4_top_target_y = float(height) * 0.5
        boss.b4_bot_arm_state = "idle"
        boss.b4_bot_arm_timer = 180
        boss.b4_bot_tentacle_len = 0.0
        boss.b4_bot_target_x = float(width) * 0.5
        boss.b4_bot_target_y = float(height) * 0.5
    elif boss_type == 5:
        play.set("boss5_bg_mode", True)
        boss = MidBoss(5, g["midboss5_images"]["normal"])
        boss.rect = g["midboss5_images"]["normal"].get_rect(center=(1050, 320))
        boss.max_hp = calc_boss5_max_hp(diff, player.weapon_level)
        boss.hp = boss.max_hp
        shield = 0
        shield_max = 0
        boss.move_timer = 0
        boss.b5_spiral = 0.0
        boss.b5_spiral2 = math.pi
        boss.b5_phase_timer = 0
        boss.b5_laser_angle = 0.0
        boss.b5_charge_phase = 0
        boss.b5_special_timer = 0
        boss.b5_rush_state = "idle"
        boss.b5_rush_timer = 0
        boss.b5_rush_vx = 0.0
        boss.b5_rush_vy = 0.0
        boss.b5_sin_anchor_x = B5_SIN_ANCHOR_X
        boss.b5_sin_anchor_y = B5_SIN_ANCHOR_Y
        boss.b5_rush_scaled = False
        boss.b5_rush_spin_angle = 0.0
        boss.b5_rush_flash_timer = 0
        init_boss5_shield_attrs(boss)
    else:
        raise ValueError(f"unknown boss_type: {boss_type}")

    play.set("boss", boss)
    play.set("boss_shield_hp", shield)
    play.set("boss_shield_max", shield_max)
    play.set("boss_shield_grace_timer", 0)

    start_boss_bgm(boss_type)
    if boss_type == 5:
        init_boss5_support_fight()
        start_boss5_bgm(boss)
        g["launch_sound"].play()
        g["_bubble"].show("boss_warning")
