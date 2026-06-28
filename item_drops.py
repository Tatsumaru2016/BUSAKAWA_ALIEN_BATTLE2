# item_drops.py — パワーアイテム種別の重み付け（1up は呼び出し側で別枠）

from __future__ import annotations

import random

from settings import PLAYER_MAX_WEAPON_LEVEL

PLAYER_MAX_SPEED = 11
ITEM_WEIGHT_NEED = 52
ITEM_WEIGHT_BASE = 12
ITEM_WEIGHT_LOW = 4
# 武器は他より低め（レーザー／スピードの維持はゲージで調整）
WEAPON_WEIGHT_SCALE = 0.65
BOSS_SUPPLY_1UP_WEIGHT = 10


def _power_item_weights(player) -> tuple[int, int, int, int]:
    """(weapon, laser_charge, shield, speed) の抽選重み。"""
    w_weapon = ITEM_WEIGHT_BASE
    w_shield = ITEM_WEIGHT_BASE
    w_speed = ITEM_WEIGHT_BASE

    wl = int(getattr(player, "weapon_level", 1))
    if wl < PLAYER_MAX_WEAPON_LEVEL:
        w_weapon = ITEM_WEIGHT_NEED
    else:
        # Lv5到達後は基本的に武器を絞る（ただしゲージが少ないときは少しだけ上げる）
        w_weapon = ITEM_WEIGHT_LOW
        lg = float(getattr(player, "laser_gauge", 0.0))
        try:
            from settings import LASER_GAUGE_MAX

            if lg < float(LASER_GAUGE_MAX) * 0.35:
                w_weapon = max(w_weapon, ITEM_WEIGHT_BASE)
        except Exception:
            pass
    w_weapon = max(1, int(w_weapon * WEAPON_WEIGHT_SCALE))

    meter = float(getattr(player, "shield_meter", 0.0))
    if meter <= 0.001:
        w_shield = ITEM_WEIGHT_NEED
    elif meter < 0.35:
        w_shield = max(ITEM_WEIGHT_BASE, ITEM_WEIGHT_NEED // 2)
    else:
        w_shield = ITEM_WEIGHT_LOW

    # スピードはゲージ制: 残量が少ないときほど寄せる
    sg = float(getattr(player, "speed_gauge", 0.0))
    try:
        from settings import SPEED_GAUGE_MAX

        if sg < float(SPEED_GAUGE_MAX) * 0.35:
            w_speed = ITEM_WEIGHT_NEED
        elif sg < float(SPEED_GAUGE_MAX) * 0.70:
            w_speed = max(ITEM_WEIGHT_BASE, ITEM_WEIGHT_NEED // 2)
        else:
            w_speed = ITEM_WEIGHT_LOW
    except Exception:
        if int(getattr(player, "speed", 7)) < PLAYER_MAX_SPEED:
            w_speed = ITEM_WEIGHT_NEED
        else:
            w_speed = ITEM_WEIGHT_LOW

    # レーザー充填は武器Lvアップと同率
    w_laser_charge = w_weapon
    return w_weapon, w_laser_charge, w_shield, w_speed


def roll_power_item_type(player) -> str:
    """雑魚ドロップ用: weapon / laser_charge / shield / speed（1up 以外）。"""
    w_weapon, w_laser_charge, w_shield, w_speed = _power_item_weights(player)
    return random.choices(
        ["weapon", "laser_charge", "shield", "speed"],
        weights=[w_weapon, w_laser_charge, w_shield, w_speed],
        k=1,
    )[0]


def roll_boss_supply_item_type(player) -> str:
    """ボス戦サプライ: 1up 重みは固定、他3種はプレイ状況で偏る。"""
    w_weapon, w_laser_charge, w_shield, w_speed = _power_item_weights(player)
    return random.choices(
        ["weapon", "laser_charge", "shield", "speed", "1up"],
        weights=[w_weapon, w_laser_charge, w_shield, w_speed, BOSS_SUPPLY_1UP_WEIGHT],
        k=1,
    )[0]
