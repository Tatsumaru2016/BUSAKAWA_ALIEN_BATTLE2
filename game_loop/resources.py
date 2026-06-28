# game_loop/resources.py — game_loop フェーズ用の RT.g() 参照グループ

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from game_runtime import RT


@dataclass(frozen=True)
class PlayFrameCore:
    """毎フレーム共通のプレイコンテキスト。"""

    play: Any
    player: Any
    screen: Any
    diff: Any
    state: int
    width: int
    height: int


@dataclass(frozen=True)
class PlayFrameCoreWithApp(PlayFrameCore):
    app: Any


@dataclass(frozen=True)
class UiMessage:
    bubble: Any


@dataclass(frozen=True)
class BossCombatSfx:
    explosion_sound: Any
    laser_warning_sound: Any
    ripple_sound: Any
    boss_special_alert_sound: Any
    boss5_gravity_sound: Any
    boss5_meteo3_sound: Any
    boss5_silence_sound: Any
    boss5_suck_sound: Any


@dataclass(frozen=True)
class BossCombatImages:
    midboss5_images: dict
    boss_shield_img: Any
    boss_shield_img2: Any


@dataclass(frozen=True)
class BattleCollisionSfx:
    explosion_sound: Any
    boss_shield_hit_sound: Any
    boss_shield_break_sound: Any


@dataclass(frozen=True)
class PowerupImages:
    weapon: Any
    laser_charge: Any
    shield: Any
    speed: Any
    super_item: Any
    one_up: Any

    def power_type_map(self) -> dict[str, Any]:
        return {
            "weapon": self.weapon,
            "laser_charge": self.laser_charge,
            "shield": self.shield,
            "speed": self.speed,
            "super": self.super_item,
        }


@dataclass(frozen=True)
class ItemPickupSfx:
    weapon: Any
    shield: Any
    speed: Any
    ems_get: Any
    explosion: Any


@dataclass(frozen=True)
class PlayerInputBundle:
    keys: dict
    shot_interval: int
    font: Any
    bubble: Any
    shot_sound: Any
    support_fighter_images: Any
    bullet_img: Any
    support_arrive_sound: Any
    joy_move_up: Callable[[], bool]
    joy_move_down: Callable[[], bool]
    joy_move_left: Callable[[], bool]
    joy_move_right: Callable[[], bool]
    joy_shoot: Callable[[], bool]


@dataclass(frozen=True)
class ScoreBossBundle:
    score_tick_sound: Any
    warning_img: Any
    warning_sound: Any
    bubble: Any


@dataclass(frozen=True)
class SpawnImages:
    enemy_images: list
    turret_top_img: Any
    turret_bottom_img: Any


@dataclass(frozen=True)
class HudResultAssets:
    keys: dict
    controller: dict
    font: Any
    font_hud_sm: Any
    big_font: Any
    gameover_img: Any
    ending_img: Any
    ending_screen_sound: Any
    title_cheat: Any


def _g(namespace: dict | None) -> dict:
    return RT.g() if namespace is None else namespace


def frame_core(namespace: dict | None = None) -> PlayFrameCore:
    g = _g(namespace)
    return PlayFrameCore(
        play=g["play"],
        player=g["player"],
        screen=g["screen"],
        diff=g["diff"],
        state=g["state"],
        width=g["WIDTH"],
        height=g["HEIGHT"],
    )


def frame_core_with_app(namespace: dict | None = None) -> PlayFrameCoreWithApp:
    core = frame_core(namespace)
    g = _g(namespace)
    return PlayFrameCoreWithApp(
        play=core.play,
        player=core.player,
        screen=core.screen,
        diff=core.diff,
        state=core.state,
        width=core.width,
        height=core.height,
        app=g["app"],
    )


def ui_message(namespace: dict | None = None) -> UiMessage:
    return UiMessage(bubble=_g(namespace)["_bubble"])


def boss_combat_sfx(namespace: dict | None = None) -> BossCombatSfx:
    g = _g(namespace)
    return BossCombatSfx(
        explosion_sound=g["explosion_sound"],
        laser_warning_sound=g["laser_warning_sound"],
        ripple_sound=g["ripple_sound"],
        boss_special_alert_sound=g["boss_special_alert_sound"],
        boss5_gravity_sound=g["boss5_gravity_sound"],
        boss5_meteo3_sound=g["boss5_meteo3_sound"],
        boss5_silence_sound=g.get("boss5_silence_sound", g["laser_warning_sound"]),
        boss5_suck_sound=g.get("boss5_suck_sound", g["boss5_gravity_sound"]),
    )


def boss_combat_images(namespace: dict | None = None) -> BossCombatImages:
    g = _g(namespace)
    return BossCombatImages(
        midboss5_images=g["midboss5_images"],
        boss_shield_img=g["boss_shield_img"],
        boss_shield_img2=g["boss_shield_img2"],
    )


def battle_collision_sfx(namespace: dict | None = None) -> BattleCollisionSfx:
    g = _g(namespace)
    return BattleCollisionSfx(
        explosion_sound=g["explosion_sound"],
        boss_shield_hit_sound=g["boss_shield_hit_sound"],
        boss_shield_break_sound=g["boss_shield_break_sound"],
    )


def powerup_images(namespace: dict | None = None) -> PowerupImages:
    g = _g(namespace)
    return PowerupImages(
        weapon=g["power_weapon_img"],
        laser_charge=g["power_laser_charge_img"],
        shield=g["power_shield_img"],
        speed=g["power_speed_img"],
        super_item=g["power_super_img"],
        one_up=g["power_1up_img"],
    )


def item_pickup_sfx(namespace: dict | None = None) -> ItemPickupSfx:
    g = _g(namespace)
    return ItemPickupSfx(
        weapon=g["item_weapon_sound"],
        shield=g["item_shield_sound"],
        speed=g["item_speed_sound"],
        ems_get=g["ems_get_sound"],
        explosion=g["explosion_sound"],
    )


def player_input_bundle(namespace: dict | None = None) -> PlayerInputBundle:
    g = _g(namespace)
    from game_constants import SHOT_INTERVAL

    return PlayerInputBundle(
        keys=g["KEY_BINDINGS"],
        shot_interval=SHOT_INTERVAL,
        font=g["font"],
        bubble=g["_bubble"],
        shot_sound=g["shot_sound"],
        support_fighter_images=g["support_fighter_images"],
        bullet_img=g["bullet_img"],
        support_arrive_sound=g["support_arrive_sound"],
        joy_move_up=g["joy_move_up"],
        joy_move_down=g["joy_move_down"],
        joy_move_left=g["joy_move_left"],
        joy_move_right=g["joy_move_right"],
        joy_shoot=g["joy_shoot"],
    )


def score_boss_bundle(namespace: dict | None = None) -> ScoreBossBundle:
    g = _g(namespace)
    return ScoreBossBundle(
        score_tick_sound=g["score_tick_sound"],
        warning_img=g["warning_img"],
        warning_sound=g["warning_sound"],
        bubble=g["_bubble"],
    )


def spawn_images(namespace: dict | None = None) -> SpawnImages:
    g = _g(namespace)
    return SpawnImages(
        enemy_images=g["enemy_images"],
        turret_top_img=g["turret_top_img"],
        turret_bottom_img=g["turret_bottom_img"],
    )


@dataclass(frozen=True)
class TitleFlowResources:
    keys: dict
    title_cheat: Any
    title_cheat_sound: Any
    launch_sound: Any
    joy_move_up: Callable[[], bool]
    joy_move_down: Callable[[], bool]
    joy_move_left: Callable[[], bool]
    joy_move_right: Callable[[], bool]


def title_flow_resources(namespace: dict | None = None) -> TitleFlowResources:
    g = _g(namespace)
    return TitleFlowResources(
        keys=g["KEY_BINDINGS"],
        title_cheat=g["title_cheat"],
        title_cheat_sound=g["title_cheat_sound"],
        launch_sound=g["launch_sound"],
        joy_move_up=g["joy_move_up"],
        joy_move_down=g["joy_move_down"],
        joy_move_left=g["joy_move_left"],
        joy_move_right=g["joy_move_right"],
    )


def hud_result_assets(namespace: dict | None = None) -> HudResultAssets:
    g = _g(namespace)
    return HudResultAssets(
        keys=g["KEY_BINDINGS"],
        controller=g["_c"],
        font=g["font"],
        font_hud_sm=g["font_hud_sm"],
        big_font=g["big_font"],
        gameover_img=g["gameover_img"],
        ending_img=g["ending_img"],
        ending_screen_sound=g["ending_screen_sound"],
        title_cheat=g["title_cheat"],
    )
