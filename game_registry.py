# game_registry.py — main に散在していた共有 callable の明示登録

from __future__ import annotations

from enemy_bullets import (
    enemy_bullet_hit_rect,
    spawn_boss5_red_laser,
    spawn_boss5_ripple,
    spawn_enemy_bullet,
    spawn_enemy_laser,
    update_enemy_bullets_frame,
)
from meteors import spawn_boss5_meteor, update_meteors_frame
from render_ui import draw_scroll, draw_text_with_shadow, key_label, pad_label


def install_game_registry(namespace: dict) -> None:
    """RT.g() 経由で参照される spawn / UI ヘルパを namespace へ登録。"""
    namespace.update(
        {
          "spawn_enemy_bullet": spawn_enemy_bullet,
          "spawn_enemy_laser": spawn_enemy_laser,
          "spawn_boss5_red_laser": spawn_boss5_red_laser,
          "spawn_boss5_ripple": spawn_boss5_ripple,
          "spawn_boss5_meteor": spawn_boss5_meteor,
          "enemy_bullet_hit_rect": enemy_bullet_hit_rect,
          "update_enemy_bullets_frame": update_enemy_bullets_frame,
          "update_meteors_frame": update_meteors_frame,
          "draw_scroll": draw_scroll,
          "draw_text_with_shadow": draw_text_with_shadow,
          "key_label": key_label,
          "pad_label": pad_label,
        }
    )
