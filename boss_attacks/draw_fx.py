"""Boss battle FX (Phase 3)."""

import math

import pygame

from game_runtime import RT


def g():
    return RT.g()


def draw_boss_special_fx(boss, is_low_hp):
    ticks = pygame.time.get_ticks()
    screen = g()["screen"]
    width = g()["WIDTH"]
    height = g()["HEIGHT"]

    if boss.boss_type == 1 and getattr(boss, "b1_sp_state", "idle") == "burst":
        _bt = getattr(boss, "b1_burst_timer", 0)
        _flash_alpha = max(0, int(120 - _bt * 1.0))
        if _flash_alpha > 0:
            _b1_flash = pygame.Surface((boss.rect.width, boss.rect.height), pygame.SRCALPHA)
            _b1_flash.fill((100, 200, 255, _flash_alpha))
            screen.blit(_b1_flash, boss.rect.topleft)
        _b1_pulse = int(14 + math.sin(ticks * 0.025) * 8 + min(_bt, 30) * 0.4)
        _b1_fx = boss.rect.left + 20
        _b1_fy = boss.rect.centery
        pygame.draw.circle(screen, (20, 60, 120), (_b1_fx, _b1_fy), _b1_pulse + 10, 3)
        pygame.draw.circle(screen, (80, 180, 255), (_b1_fx, _b1_fy), _b1_pulse + 4, 2)
        pygame.draw.circle(screen, (200, 240, 255), (_b1_fx, _b1_fy), max(3, _b1_pulse // 2))
        if _bt < 10:
            _warn_alpha = int(160 * (1 - _bt / 10))
            _bx = boss.rect.left - 36
            _cy = boss.rect.centery
            _top = boss.rect.top + int(boss.rect.height * 0.14)
            _bot = boss.rect.bottom - int(boss.rect.height * 0.14)
            for _y0, _y1 in ((_top, _cy), (_cy, _bot)):
                _seg_h = max(4, _y1 - _y0)
                _b1_warn = pygame.Surface((6, _seg_h), pygame.SRCALPHA)
                _b1_warn.fill((100, 200, 255, _warn_alpha))
                screen.blit(_b1_warn, (_bx, _y0))

    elif boss.boss_type == 2:
        _b2_cs = getattr(boss, "b2_charge_state", "idle")
        if _b2_cs == "charge":
            _b2_flash_a = int(100 + math.sin(ticks * 0.05) * 60)
            _b2_flash = pygame.Surface((boss.rect.width, boss.rect.height), pygame.SRCALPHA)
            _b2_flash.fill((255, 40, 40, _b2_flash_a))
            screen.blit(_b2_flash, boss.rect.topleft)
            _b2_ring_x = boss.rect.left - 20
            _b2_ring_y = boss.rect.centery
            _b2_ring_r = int(30 + math.sin(ticks * 0.04) * 15)
            pygame.draw.circle(screen, (180, 0, 0), (_b2_ring_x, _b2_ring_y), _b2_ring_r + 12, 4)
            pygame.draw.circle(screen, (255, 80, 80), (_b2_ring_x, _b2_ring_y), _b2_ring_r + 4, 2)
            pygame.draw.circle(screen, (255, 200, 200), (_b2_ring_x, _b2_ring_y), max(4, _b2_ring_r // 2))

    elif boss.boss_type == 3 and getattr(boss, "b3_sp_state", "idle") == "burst":
        _b3t = getattr(boss, "b3_sp_sub", 0)
        _b3_flash_a = max(0, int(100 - _b3t * 0.8))
        if _b3_flash_a > 0:
            _b3_flash = pygame.Surface((boss.rect.width, boss.rect.height), pygame.SRCALPHA)
            _b3_flash.fill((160, 60, 255, _b3_flash_a))
            screen.blit(_b3_flash, boss.rect.topleft)
        if _b3t < 40:
            for _ri in range(3):
                _b3_r = int((_b3t * 18) - _ri * 30)
                if _b3_r > 0:
                    _alpha_ring = max(0, 180 - _b3t * 4 - _ri * 40)
                    _b3_ring_surf = pygame.Surface(((_b3_r + 6) * 2, (_b3_r + 6) * 2), pygame.SRCALPHA)
                    pygame.draw.circle(
                        _b3_ring_surf, (140, 80, 255, _alpha_ring),
                        (_b3_r + 6, _b3_r + 6), _b3_r + 3, 3,
                    )
                    pygame.draw.circle(
                        _b3_ring_surf, (200, 160, 255, _alpha_ring // 2),
                        (_b3_r + 6, _b3_r + 6), _b3_r, 2,
                    )
                    screen.blit(
                        _b3_ring_surf,
                        (width - (_b3_r + 6) * 2 // 2, boss.rect.centery - (_b3_r + 6)),
                    )
