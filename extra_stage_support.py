# extra_stage_support.py — エクストラボス戦: 5機支援（難易度別HP%以下で参加）

from __future__ import annotations

import math
import random

import pygame

from boss5_support import (
    SUPPORT_SIZE,
    _make_fallback_support,
    load_support_fighter_images,
    support_fighter_rect,
)
from game_runtime import RT
from support_movement import init_support_autonomy, update_support_free_move

EXTRA_SUPPORT_HP_RATIO_BY_DIFF = {
    "EASY": 0.50,
    "NORMAL": 0.40,
    "HARD": 0.35,
    "NIGHTMARE": 0.30,
}


def extra_support_hp_ratio(diff=None) -> float:
    """難易度ごとの支援機参加ボスHPしきい値（残HPがこの比率以下で登場）。"""
    if diff is None:
        diff = RT.g()["diff"]
    return EXTRA_SUPPORT_HP_RATIO_BY_DIFF.get(
        getattr(diff, "name", "NORMAL"),
        0.40,
    )
EXTRA_SUPPORT_COUNT = 5
EXTRA_SUPPORT_ENTER_SPEED = 10.0
EXTRA_SUPPORT_SHOT_INTERVAL = 16
EXTRA_SUPPORT_QUIP_MIN = 150
EXTRA_SUPPORT_QUIP_MAX = 280

# 撃破後: 画面中心（自機）の右に縦並び（吹き出し用・重ならない）
VICTORY_SLOT_OFFSET_X = (92, 122, 152, 182, 212)
VICTORY_SLOT_OFFSET_Y = (-108, -54, 0, 54, 108)
VICTORY_LINEUP_SPEED = 3.2
VICTORY_EXIT_SPEED = 5.8
VICTORY_PLAY_MARGIN_Y = 72


def _victory_anchor(play) -> tuple[float, float]:
    px = float(getattr(play, "extra_victory_target_x", 0) or 0)
    py = float(getattr(play, "extra_victory_target_y", 0) or 0)
    if px == 0.0 and py == 0.0:
        px = float(getattr(play, "extra_victory_frozen_x", 0) or 0)
        py = float(getattr(play, "extra_victory_frozen_y", 0) or 0)
    return px, py


def _victory_slot(play, slot_index: int, height: int) -> tuple[float, float]:
    px, py = _victory_anchor(play)
    i = slot_index % 5
    tx = px + VICTORY_SLOT_OFFSET_X[i]
    ty = py + VICTORY_SLOT_OFFSET_Y[i]
    _, sh = SUPPORT_SIZE
    min_y = sh * 0.5 + VICTORY_PLAY_MARGIN_Y
    max_y = float(height) - sh * 0.5 - VICTORY_PLAY_MARGIN_Y
    return tx, max(min_y, min(max_y, ty))


def _right_offscreen_x(variant: int, width: int) -> float:
    sw, _ = SUPPORT_SIZE
    return float(width + sw + 55 + variant * 18)


def _left_offscreen_x(variant: int) -> float:
    sw, _ = SUPPORT_SIZE
    return float(-sw - 48 - variant * 20)


def _step_toward(sf, tx, ty, speed, snap=12.0) -> bool:
    dx = tx - sf["x"]
    dy = ty - sf["y"]
    dist = math.hypot(dx, dy)
    if dist > 1.0:
        step = min(speed, dist)
        sf["x"] += (dx / dist) * step
        sf["y"] += (dy / dist) * step
        dist = math.hypot(tx - sf["x"], ty - sf["y"])
    if dist <= snap:
        sf["x"], sf["y"] = tx, ty
        return True
    return False


def init_extra_support_state(play) -> None:
    play.set("extra_support_deployed", False)
    play.set("extra_support_fighters", [])


def clear_extra_support(play) -> None:
    play.set("extra_support_deployed", False)
    play.set("extra_support_fighters", [])


def is_extra_support_active(play) -> bool:
    return bool(getattr(play, "extra_support_deployed", False))


def _support_image(images, variant: int):
    if images:
        return images[variant % len(images)]
    return _make_fallback_support(variant)


def deploy_extra_support_squad(
    play,
    player,
    images,
    width: int,
    height: int,
    bubble=None,
    arrive_sound=None,
) -> None:
    """ボスHPが難易度しきい値以下: 5機を画面左外から一斉投入。"""
    if play.extra_support_deployed:
        return
    squad = []
    for i in range(EXTRA_SUPPORT_COUNT):
        enter_y = float(player.rect.centery) + VICTORY_SLOT_OFFSET_Y[i] * 0.45
        _, sh = SUPPORT_SIZE
        enter_y = max(
            sh * 0.5 + VICTORY_PLAY_MARGIN_Y,
            min(float(height) - sh * 0.5 - VICTORY_PLAY_MARGIN_Y, enter_y),
        )
        squad.append({
            "variant": i,
            "image": _support_image(images, i),
            "state": "enter",
            "x": _left_offscreen_x(i),
            "y": enter_y + random.randint(-6, 6),
            "enter_tx": float(player.rect.centerx + 40 + i * 8),
            "enter_ty": enter_y,
            "shot_timer": i * 4,
            "frame": 0,
            "quip_timer": random.randint(60, 180),
            "announced": False,
        })
    play.set("extra_support_fighters", squad)
    play.set("extra_support_deployed", True)
    if arrive_sound is not None:
        try:
            arrive_sound.play()
        except Exception:
            pass


def deploy_victory_support_squad(
    play,
    images,
    width: int,
    height: int,
    *,
    variant: int,
    arrive_sound=None,
) -> None:
    """撃破演出（未参加時）: 左外から投入し、整列スロットへ。"""
    squad = list(getattr(play, "extra_support_fighters", []))
    tx, ty = _victory_slot(play, variant, height)
    squad.append({
        "variant": variant,
        "image": _support_image(images, variant),
        "state": "victory_enter",
        "x": _left_offscreen_x(variant),
        "y": float(ty + random.randint(-6, 6)),
        "victory_tx": tx,
        "victory_ty": ty,
        "frame": 0,
        "announced": True,
    })
    play.set("extra_support_fighters", squad)
    play.set("extra_support_deployed", True)
    if variant == 0 and arrive_sound is not None:
        try:
            arrive_sound.play()
        except Exception:
            pass


def begin_victory_lineup(play, width: int, height: int) -> None:
    """全支援機の撃破後スロットを確定し、ゆっくり移動開始。"""
    if not play.extra_support_deployed:
        return
    for sf in play.extra_support_fighters:
        v = sf["variant"]
        tx, ty = _victory_slot(play, v, height)
        sf["victory_tx"] = tx
        sf["victory_ty"] = ty
        if sf.get("state") not in ("victory_hold",):
            sf["state"] = "victory_enter"


def begin_victory_exit(play, width: int) -> None:
    """吹き出し後: 画面右外へ退場。"""
    if not play.extra_support_deployed:
        return
    for sf in play.extra_support_fighters:
        sf["state"] = "victory_exit"
        sf["exit_tx"] = _right_offscreen_x(sf["variant"], width)
        sf["exit_ty"] = float(sf.get("victory_ty", sf["y"]))


def all_support_lineup_done(play) -> bool:
    squad = getattr(play, "extra_support_fighters", [])
    if not squad:
        return True
    return all(sf.get("state") == "victory_hold" for sf in squad)


def all_support_exited(play, width: int) -> bool:
    squad = getattr(play, "extra_support_fighters", [])
    if not squad:
        return True
    limit = float(width) + SUPPORT_SIZE[0] + 40
    return all(float(sf["x"]) >= limit for sf in squad)


def _maybe_support_quip(sf, bubble) -> None:
    if bubble is None:
        return
    sf["quip_timer"] -= 1
    if sf["quip_timer"] > 0:
        return
    sf["quip_timer"] = random.randint(EXTRA_SUPPORT_QUIP_MIN, EXTRA_SUPPORT_QUIP_MAX)
    key = f"extra_support_quip_{sf['variant']}"
    bubble.show(key, support_fighter_rect(sf), anchor_style="support")


def update_extra_support_squad(
    play,
    player,
    player_dead,
    boss,
    bullets,
    bullet_img,
    images,
    bubble,
    width,
    height,
    bullet_cls,
    arrive_sound=None,
    *,
    victory_lineup: bool = False,
    victory_exit: bool = False,
) -> None:
    if not play.extra_support_deployed:
        return

    squad = play.extra_support_fighters
    if not squad:
        return

    if player_dead and not victory_lineup and not victory_exit:
        return

    for sf in squad:
        sf["frame"] = sf.get("frame", 0) + 1

        if victory_exit:
            ex = sf.get("exit_tx", _right_offscreen_x(sf["variant"], width))
            ey = sf.get("exit_ty", sf["y"])
            _step_toward(sf, ex, ey, VICTORY_EXIT_SPEED, snap=24.0)
            continue

        if victory_lineup:
            state = sf.get("state", "victory_enter")
            if state == "victory_enter":
                tx = sf.get("victory_tx", sf["x"])
                ty = sf.get("victory_ty", sf["y"])
                if _step_toward(sf, tx, ty, VICTORY_LINEUP_SPEED):
                    sf["state"] = "victory_hold"
                    sf["x"], sf["y"] = tx, ty
            elif state == "victory_hold":
                sf["x"] = sf.get("victory_tx", sf["x"])
                sf["y"] = sf.get("victory_ty", sf["y"])
            continue

        if sf["state"] == "enter":
            tx = sf.get("enter_tx", sf["x"] + 120)
            ty = sf.get("enter_ty", sf["y"])
            if _step_toward(sf, tx, ty, EXTRA_SUPPORT_ENTER_SPEED):
                sf["state"] = "active"
                init_support_autonomy(
                    sf, sf["x"], sf["y"], variant=sf["variant"],
                    width=width, height=height,
                )
                if not sf["announced"] and bubble is not None:
                    sf["announced"] = True
                    bubble.show(
                        f"support_arrive_{sf['variant']}",
                        support_fighter_rect(sf),
                        anchor_style="support",
                    )
        elif sf["state"] == "active":
            update_support_free_move(
                sf, boss, width, height, variant=sf["variant"],
            )
            if boss is not None and boss.hp > 0 and not player_dead:
                sf["shot_timer"] = max(0, sf.get("shot_timer", 0) - 1)
                if sf["shot_timer"] == 0:
                    sf["shot_timer"] = EXTRA_SUPPORT_SHOT_INTERVAL
                    mx = int(sf["x"]) + 26
                    my = int(sf["y"])
                    bullets.append(bullet_cls(mx, my - 8, bullet_img, damage=1))
                    bullets.append(bullet_cls(mx, my + 8, bullet_img, damage=1))
                _maybe_support_quip(sf, bubble)


def draw_extra_support_squad(screen, play) -> None:
    for sf in getattr(play, "extra_support_fighters", []):
        if sf.get("state") == "victory_exit":
            sw, _ = SUPPORT_SIZE
            if sf["x"] > screen.get_width() + sw:
                continue
        img = sf.get("image")
        if img is None:
            continue
        rect = img.get_rect(center=(int(sf["x"]), int(sf["y"])))
        screen.blit(img, rect)


def check_deploy_extra_support(
    play,
    boss,
    player,
    images,
    bubble,
    width,
    height,
    arrive_sound=None,
) -> None:
    if play.extra_support_deployed or boss is None or boss.boss_type != 6:
        return
    if boss.hp > boss.max_hp * extra_support_hp_ratio():
        return
    deploy_extra_support_squad(
        play, player, images, width, height, bubble, arrive_sound,
    )


def get_extra_support_bubble_anchor(play):
    squad = getattr(play, "extra_support_fighters", [])
    if not squad:
        return None
    visible = [
        sf for sf in squad
        if sf.get("state") in ("victory_hold", "victory_enter")
    ]
    if not visible:
        visible = [sf for sf in squad if sf.get("state") != "victory_exit"]
    if not visible:
        return None
    idx = (pygame.time.get_ticks() // 500) % len(visible)
    return support_fighter_rect(visible[idx])
