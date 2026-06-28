# homing_bullet.py — ホーミング弾の追尾更新

import math

# ボス2ホーミングの弾速（5分の3）
B2_HOMING_SPEED_MULT = 3 / 5


def update_homing_bullet(eb, player, diff_config, frame):
    """強化版ホーミング弾更新（全ボス共通）。"""
    if not eb.get("homing") or not player or getattr(player, "dead", False):
        return False

    dx = player.rect.centerx - eb.get("x", 0)
    dy = player.rect.centery - eb.get("y", 0)
    dist = math.hypot(dx, dy)

    if dist < 5:
        return False

    image_type = eb.get("image_type", "")
    turret_homing = image_type == "turret_homing"
    b2_homing = image_type == "boss2_homing"

    if turret_homing:
        strength = {
            "EASY": 0.024,
            "NORMAL": 0.029,
            "HARD": 0.034,
            "NIGHTMARE": 0.042,
        }.get(diff_config.name, 0.029)
    else:
        strength = 0.085
        if diff_config.name == "NIGHTMARE":
            strength = 0.135
        elif diff_config.name == "HARD":
            strength = 0.060
        elif diff_config.name == "NORMAL":
            strength = 0.055
        elif diff_config.name == "EASY":
            strength = 0.040
        if b2_homing:
            strength *= 0.82
        elif image_type == "boss1_homing":
            strength *= 0.75

    speed = math.hypot(eb.get("vx", 0), eb.get("vy", 0))
    if turret_homing:
        if speed < 3.0:
            speed = 6.4
    elif speed < 3.0:
        speed = 5.8
    if b2_homing:
        speed *= B2_HOMING_SPEED_MULT

    target_vx = (dx / dist) * speed
    target_vy = (dy / dist) * speed

    eb["vx"] = eb.get("vx", 0) * (1 - strength) + target_vx * strength
    eb["vy"] = eb.get("vy", 0) * (1 - strength) + target_vy * strength

    cur_speed = math.hypot(eb["vx"], eb["vy"])
    min_speed = 5.0 if turret_homing else 4.2
    if b2_homing:
        min_speed *= B2_HOMING_SPEED_MULT
    if cur_speed < min_speed:
        scale = min_speed / cur_speed
        eb["vx"] *= scale
        eb["vy"] *= scale

    return True
