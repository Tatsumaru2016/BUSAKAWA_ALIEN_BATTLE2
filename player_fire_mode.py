# player_fire_mode.py — レーザー／通常弾の切替とゲージ吹き出し

from __future__ import annotations

from settings import LASER_GAUGE_MAX, PLAYER_MAX_WEAPON_LEVEL


def can_select_fire_mode(player) -> bool:
    return int(getattr(player, "weapon_level", 1)) >= PLAYER_MAX_WEAPON_LEVEL


def toggle_fire_mode(player, bubble) -> None:
    """Lv5: レーザー⇔通常弾を切り替え。"""
    if not can_select_fire_mode(player):
        return
    mode = getattr(player, "fire_mode", "normal")
    if mode == "laser":
        player.fire_mode = "normal"
        bubble.show("weapon_mode_normal")
        return
    if float(getattr(player, "laser_gauge", 0.0)) > 0.001:
        player.fire_mode = "laser"
        bubble.show("weapon_mode_laser")
    else:
        player.fire_mode = "normal"
        bubble.show("laser_need_charge")


def notify_laser_gauge_after_shot(player, bubble) -> None:
    """レーザー発射後のゲージ残量に応じた吹き出し。"""
    lg = float(getattr(player, "laser_gauge", 0.0))
    if lg <= 0.001:
        player.fire_mode = "normal"
        bubble.show("laser_need_charge")
        player._laser_low_warned = False
        return
    if lg < float(LASER_GAUGE_MAX) * 0.25:
        if not getattr(player, "_laser_low_warned", False):
            bubble.show("laser_low")
            player._laser_low_warned = True
    elif lg > float(LASER_GAUGE_MAX) * 0.5:
        player._laser_low_warned = False
