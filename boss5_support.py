# boss5_support.py — ボス5戦専用：味方支援機

import math
import random
import pygame

from settings import PLAYER_SPRITE_SIZE
from support_movement import init_support_autonomy, update_support_free_move

SUPPORT_SIZE = PLAYER_SPRITE_SIZE
SUPPORT_ACTIVE_FRAMES = 60 * 20
SUPPORT_FIRST_DELAY = 60 * 20          # 初回まで（秒≈20）
SUPPORT_REPEAT_INTERVAL = 60 * 25      # 2回目以降の抽選間隔（秒≈25）
SUPPORT_ENTER_CENTER_SPEED = 11.5   # 画面中央へ
SUPPORT_ENTER_JOIN_SPEED = 9.0      # 自機へ合流
SUPPORT_CENTER_HOLD_FRAMES = 40     # 中央での待機（約0.67秒）
SUPPORT_CENTER_Y_RATIO = 0.46       # 画面中央付近のY
SUPPORT_LEAVE_SPEED = 9.5
SUPPORT_SHOT_INTERVAL = 14
# 自機との距離（自律移動のゾーン中心）
SUPPORT_HOME_GAP_X = 42          # 自機左端と支援機右端のすき間
SUPPORT_HOME_OFFSET_Y = -92      # 自機中心より上へ（負=上）
SUPPORT_OFFSET_Y_SPREAD = 22   # 縦の個体差 ±px
SUPPORT_SPAWN_CHANCE = 0.50            # 2回目以降の出現率
SUPPORT_PITY_AFTER_MISSES = 2          # 連続不的中のあと次は確定
# ボスHPが初めてこの割合を下回ったとき追加登場（1回ずつ）
SUPPORT_HP_TRIGGERS = (0.50, 0.25, 0.10)

SUPPORT_FIGHTER_COUNT = 5

_support_fighter = None
_deploy_cd = 0
_first_deploy_pending = False
_spawn_miss_streak = 0
_hp_triggers_used = set()
_last_boss_hp_ratio = 1.0
_queued_hp_spawn = False


def _make_fallback_support(variant):
    """PNG未配置時のプレースホルダ（機体ごとに色分け）。"""
    colors = (
        ((40, 120, 220), (180, 220, 255)),
        ((40, 180, 100), (180, 255, 200)),
        ((220, 140, 40), (255, 220, 160)),
        ((180, 80, 220), (240, 180, 255)),
        ((220, 80, 100), (255, 180, 160)),
    )
    body, wing = colors[variant % len(colors)]
    surf = pygame.Surface(SUPPORT_SIZE, pygame.SRCALPHA)
    w, h = SUPPORT_SIZE
    pygame.draw.polygon(surf, wing, [(8, h // 2), (w - 20, 8), (w - 20, h - 8)])
    pygame.draw.ellipse(surf, body, (18, 14, w - 28, h - 22))
    pygame.draw.circle(surf, (255, 255, 255), (w - 22, h // 2 - 4), 5)
    return surf


def load_support_fighter_images(load_image_fn):
    """support_fighter_1.png 〜 support_fighter_N.png を読み込む。"""
    images = []
    for i in range(1, SUPPORT_FIGHTER_COUNT + 1):
        path = f"support_fighter_{i}.png"
        try:
            img = load_image_fn(path).convert_alpha()
            if img.get_size() != SUPPORT_SIZE:
                img = pygame.transform.smoothscale(img, SUPPORT_SIZE)
        except Exception:
            img = _make_fallback_support(i - 1)
        images.append(img)
    return images


def init_boss5_support_fight():
    global _support_fighter, _deploy_cd, _first_deploy_pending
    global _spawn_miss_streak, _hp_triggers_used, _last_boss_hp_ratio, _queued_hp_spawn
    _support_fighter = None
    _deploy_cd = SUPPORT_FIRST_DELAY
    _first_deploy_pending = True
    _spawn_miss_streak = 0
    _hp_triggers_used = set()
    _last_boss_hp_ratio = 1.0
    _queued_hp_spawn = False


def clear_boss5_support():
    global _support_fighter, _deploy_cd, _first_deploy_pending
    global _spawn_miss_streak, _hp_triggers_used, _last_boss_hp_ratio, _queued_hp_spawn
    _support_fighter = None
    _deploy_cd = 0
    _first_deploy_pending = False
    _spawn_miss_streak = 0
    _hp_triggers_used = set()
    _last_boss_hp_ratio = 1.0
    _queued_hp_spawn = False


def get_support_fighter():
    return _support_fighter


def is_boss5_support_allowed(play) -> bool:
    """ボス5戦中のみ支援機を動かす。"""
    boss = play.boss
    return (
        play.boss_active
        and boss is not None
        and boss.boss_type == 5
        and not play.b5_death_active
    )


def support_fighter_rect(sf):
    """吹き出しのアンカー用矩形。"""
    img = sf["image"]
    return img.get_rect(center=(int(sf["x"]), int(sf["y"])))


def _support_rally_point(width, height):
    return float(width * 0.5), float(height * SUPPORT_CENTER_Y_RATIO)


def _announce_support_arrival(sf, bubble, arrive_sound):
    if sf.get("announced"):
        return
    sf["announced"] = True
    if arrive_sound is not None:
        arrive_sound.play()
    if bubble is not None:
        key = f"support_arrive_{sf['variant']}"
        bubble.show(key, support_fighter_rect(sf), anchor_style="support")


def _step_toward(sf, tx, ty, speed, snap_dist=22.0):
    dx = tx - sf["x"]
    dy = ty - sf["y"]
    dist = math.hypot(dx, dy)
    if dist > 1.0:
        step = min(speed, dist)
        sf["x"] += (dx / dist) * step
        sf["y"] += (dy / dist) * step
        dist = math.hypot(tx - sf["x"], ty - sf["y"])
    if dist <= snap_dist:
        sf["x"], sf["y"] = tx, ty
        return True
    return False


def _spawn_support(player, images, bubble, arrive_sound=None):
    global _support_fighter
    variant = random.randint(0, len(images) - 1)
    _support_fighter = {
        "variant": variant,
        "image": images[variant],
        "state": "enter_center",
        "x": float(-SUPPORT_SIZE[0] - 40),
        "y": float(player.rect.centery + random.randint(-50, 50)),
        "active_timer": SUPPORT_ACTIVE_FRAMES,
        "shot_timer": 0,
        "frame": 0,
        "hold_timer": 0,
        "announced": False,
        "target_offset_y": random.randint(
            -SUPPORT_OFFSET_Y_SPREAD, SUPPORT_OFFSET_Y_SPREAD,
        ),
        "_pending_bubble": bubble,
        "_pending_arrive_sound": arrive_sound,
    }


def _support_home(player):
    """自機の左後方・やや上に待機（自機と重なりにくい位置）。"""
    sw, _ = SUPPORT_SIZE
    off_y = _support_fighter.get("target_offset_y", 0)
    home_x = float(player.rect.left - SUPPORT_HOME_GAP_X - sw * 0.5)
    home_y = float(player.rect.centery + SUPPORT_HOME_OFFSET_Y + off_y)
    return home_x, home_y


def _boss_hp_ratio(boss):
    return boss.hp / max(1, boss.max_hp)


def _hp_spawn_triggered_this_frame(boss):
    """HP閾値を初めて下回ったフレームなら True（50% / 25% / 10% 各1回）。"""
    global _hp_triggers_used, _last_boss_hp_ratio, _queued_hp_spawn
    ratio = _boss_hp_ratio(boss)
    triggered = False
    for threshold in SUPPORT_HP_TRIGGERS:
        if threshold in _hp_triggers_used:
            continue
        if _last_boss_hp_ratio > threshold >= ratio:
            _hp_triggers_used.add(threshold)
            triggered = True
    _last_boss_hp_ratio = ratio
    if triggered and _support_fighter is not None:
        _queued_hp_spawn = True
        return False
    return triggered


def _try_spawn_support(player, images, bubble, arrive_sound, force=False):
    """出現抽選。force または初回・HPトリガー・天井で登場。"""
    global _spawn_miss_streak, _deploy_cd, _first_deploy_pending
    if force:
        _spawn_support(player, images, bubble, arrive_sound)
        _spawn_miss_streak = 0
        _first_deploy_pending = False
        _deploy_cd = SUPPORT_REPEAT_INTERVAL
        return True
    chance = 1.0 if _first_deploy_pending else SUPPORT_SPAWN_CHANCE
    if _spawn_miss_streak >= SUPPORT_PITY_AFTER_MISSES:
        chance = 1.0
    _first_deploy_pending = False
    if random.random() < chance:
        _spawn_support(player, images, bubble, arrive_sound)
        _spawn_miss_streak = 0
        _deploy_cd = SUPPORT_REPEAT_INTERVAL
        return True
    _spawn_miss_streak += 1
    _deploy_cd = SUPPORT_REPEAT_INTERVAL
    return False


def update_boss5_support(
    player,
    player_dead,
    boss,
    boss_active,
    bullets,
    bullet_img,
    images,
    bubble,
    WIDTH,
    HEIGHT,
    Bullet,
    arrive_sound=None,
):
    """毎フレーム更新。ボス5戦中のみ main から呼ぶ。"""
    global _support_fighter, _deploy_cd, _queued_hp_spawn

    if boss is None or boss.boss_type != 5 or not boss_active:
        if _support_fighter is not None:
            clear_boss5_support()
        return

    hp_trigger = _hp_spawn_triggered_this_frame(boss)

    if _support_fighter is None:
        if hp_trigger:
            _deploy_cd = 0
        if _deploy_cd > 0:
            _deploy_cd -= 1
            return
        if player_dead:
            return
        _try_spawn_support(
            player,
            images,
            bubble,
            arrive_sound,
            force=hp_trigger,
        )
        return

    if player_dead:
        return

    sf = _support_fighter
    sf["frame"] = sf.get("frame", 0) + 1

    rally_x, rally_y = _support_rally_point(WIDTH, HEIGHT)
    pending_bubble = sf.get("_pending_bubble")
    pending_sound = sf.get("_pending_arrive_sound")

    if sf["state"] == "enter_center":
        if _step_toward(sf, rally_x, rally_y, SUPPORT_ENTER_CENTER_SPEED):
            sf["state"] = "enter_hold"
            sf["hold_timer"] = SUPPORT_CENTER_HOLD_FRAMES
            _announce_support_arrival(sf, pending_bubble, pending_sound)
            sf["_pending_bubble"] = None
            sf["_pending_arrive_sound"] = None

    elif sf["state"] == "enter_hold":
        sf["hold_timer"] = max(0, sf.get("hold_timer", 0) - 1)
        pulse = 1.0 + 0.06 * math.sin(sf["frame"] * 0.22)
        sf["draw_scale"] = pulse
        if sf["hold_timer"] <= 0:
            sf["state"] = "enter_join"
            sf["draw_scale"] = 1.0

    elif sf["state"] == "enter_join":
        sf["draw_scale"] = 1.0
        if _step_toward(sf, rally_x, rally_y, SUPPORT_ENTER_JOIN_SPEED):
            sf["state"] = "active"
            init_support_autonomy(
                sf,
                sf["x"],
                sf["y"],
                variant=sf.get("variant", 0),
                width=WIDTH,
                height=HEIGHT,
            )

    elif sf["state"] == "active":
        update_support_free_move(
            sf,
            boss,
            WIDTH,
            HEIGHT,
            variant=sf.get("variant", 0),
        )

        sf["active_timer"] -= 1
        sf["shot_timer"] = max(0, sf["shot_timer"] - 1)
        if sf["shot_timer"] == 0 and boss is not None:
            sf["shot_timer"] = SUPPORT_SHOT_INTERVAL
            muzzle_x = int(sf["x"]) + 28
            muzzle_y = int(sf["y"])
            bullets.append(Bullet(muzzle_x, muzzle_y - 10, bullet_img, damage=1))
            bullets.append(Bullet(muzzle_x, muzzle_y, bullet_img, damage=1))
            bullets.append(Bullet(muzzle_x, muzzle_y + 10, bullet_img, damage=1))

        if sf["active_timer"] <= 0:
            sf["state"] = "leave"
            if bubble is not None:
                bubble.show(
                    f"support_leave_{sf['variant']}",
                    support_fighter_rect(sf),
                    anchor_style="support",
                )

    elif sf["state"] == "leave":
        sf["x"] -= SUPPORT_LEAVE_SPEED
        sf["y"] += math.sin(sf["frame"] * 0.06) * 0.8
        if sf["x"] < -SUPPORT_SIZE[0] - 60:
            _support_fighter = None
            if _queued_hp_spawn:
                _queued_hp_spawn = False
                _deploy_cd = 0
            else:
                _deploy_cd = SUPPORT_REPEAT_INTERVAL


def draw_boss5_support(screen, play=None) -> None:
    if play is not None and not is_boss5_support_allowed(play):
        return
    sf = _support_fighter
    if sf is None:
        return
    cx, cy = int(sf["x"]), int(sf["y"])

    if sf.get("state") == "enter_hold":
        hold_t = sf.get("hold_timer", 0)
        for ring_i in range(3):
            radius = 36 + ring_i * 22 + (SUPPORT_CENTER_HOLD_FRAMES - hold_t) // 2
            alpha = max(0, 140 - ring_i * 35 - hold_t * 2)
            ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                ring, (120, 200, 255, alpha),
                (radius + 2, radius + 2), radius, 3,
            )
            screen.blit(ring, (cx - radius - 2, cy - radius - 2))

    img = sf["image"]
    scale = float(sf.get("draw_scale", 1.0))
    if abs(scale - 1.0) > 0.02:
        sw = max(1, int(img.get_width() * scale))
        sh = max(1, int(img.get_height() * scale))
        img = pygame.transform.smoothscale(img, (sw, sh))
    rect = img.get_rect(center=(cx, cy))
    screen.blit(img, rect)
