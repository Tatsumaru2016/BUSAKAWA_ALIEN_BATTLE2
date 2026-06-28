# audio.py — 効果音の一括読み込みと BGM 管理

import os

import pygame

from boss5_update import get_boss5_bgm_hp_tier, resolve_boss5_bgm_track
from assets_loader import resource_path
from settings import BGM_VOLUME
from sfx_mute import is_sfx_muted, set_sfx_muted

BGM_TITLE = "assets/title.ogg"
BGM_NORMAL = "assets/bgm_main.ogg"
BGM_BOSS1 = "assets/boss1_bgm.ogg"
BGM_BOSS2 = "assets/boss2_bgm.ogg"
BGM_BOSS3 = "assets/boss3_bgm.ogg"
BGM_BOSS4 = "assets/boss4_bgm.ogg"
BGM_BOSS_BY_TYPE = {
    1: BGM_BOSS1,
    2: BGM_BOSS2,
    3: BGM_BOSS3,
    4: BGM_BOSS4,
}
# 個別曲が無いときの旧ファイル名
BGM_FALLBACKS: dict[str, list[str]] = {
    BGM_NORMAL: ["assets/bgm.ogg"],
    BGM_BOSS1: ["assets/bgm_boss123.ogg"],
    BGM_BOSS2: ["assets/bgm_boss123.ogg"],
    BGM_BOSS3: ["assets/bgm_boss123.ogg"],
    BGM_BOSS4: ["assets/bgm_boss4.ogg"],
}
BGM_BOSS5 = "assets/bgm_boss5.ogg"
BGM_EXTRA_BOSS = "assets/bgm_extra_boss.ogg"
BGM_EXTRA_BOSS_TANK = "assets/bgm_extra_boss_tank.ogg"
BGM_EXTRA_BOSS_TRANSFORM = "assets/bgm_extra_boss_transform.ogg"
BGM_EXTRA_BOSS_FALLBACK = BGM_BOSS5
BGM_GAMEOVER = "assets/bgm_gameover.ogg"
BGM_ENDING = "assets/bgm_ending.ogg"

_current_bgm = None
_boss5_bgm_tier = None


def _boss5_bgm_path_exists(track: str) -> bool:
    return _resolve_bgm_path(track) is not None


def _music_busy() -> bool:
    try:
        return bool(pygame.mixer.music.get_busy())
    except Exception:
        return False


def _resolve_bgm_path(track: str) -> str | None:
    """論理トラック名 → 実ファイルの絶対パス（フォールバック込み）。"""
    for candidate in (track, *BGM_FALLBACKS.get(track, ())):
        path = resource_path(candidate)
        if os.path.isfile(path):
            return path
    return None


def invalidate_bgm_state() -> None:
    """fadeout 等で再生が止まったあと、次の play_bgm が確実に走るようにする。"""
    global _current_bgm
    _current_bgm = None


def ensure_music_playing(volume: float | None = None) -> None:
    """ポーズ解除・ウィンドウ復帰後: 記録上の曲が止まっていれば再開。"""
    if _current_bgm and not _music_busy():
        play_bgm(_current_bgm, volume=volume, force=True)


def bgm_for_boss_type(boss_type: int) -> str | None:
    """ボス1〜4のBGMパス。未対応・未配置は None。"""
    track = BGM_BOSS_BY_TYPE.get(boss_type)
    if track is None:
        return None
    if _resolve_bgm_path(track):
        return track
    return None


def start_boss_bgm(boss_type: int, volume: float | None = None, *, force: bool = True) -> None:
    """ボス警告〜出現: ボス種別に応じてBGMを切り替える。"""
    if boss_type == 5:
        start_boss5_bgm(volume=volume, force=force)
        return
    track = bgm_for_boss_type(boss_type)
    if track:
        play_bgm(track, volume=volume, force=force)


def play_bgm(track, volume=None, loops=-1, force=False):
    """BGM を切り替える。同曲でも再生が止まっていれば再ロードする。"""
    global _current_bgm
    vol = BGM_VOLUME if volume is None else volume
    if _current_bgm == track and not force:
        if _music_busy():
            try:
                pygame.mixer.music.set_volume(vol)
            except Exception:
                pass
            return
    path = _resolve_bgm_path(track)
    if path is None:
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loops)
        pygame.mixer.music.set_volume(vol)
        _current_bgm = track
    except Exception:
        pass


def stop_bgm():
    global _current_bgm
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    _current_bgm = None


def update_boss5_hp_bgm(boss, volume: float | None = None, *, force: bool = False):
    """ボス5: HP帯が変わったときだけ BGM を切り替える。"""
    global _boss5_bgm_tier
    tier = get_boss5_bgm_hp_tier(boss)
    if tier == _boss5_bgm_tier and not force:
        if _music_busy():
            return
    _boss5_bgm_tier = tier
    play_bgm(
        resolve_boss5_bgm_track(tier, _boss5_bgm_path_exists),
        volume=volume,
        force=force,
    )


def start_boss5_bgm(boss=None, volume: float | None = None, *, force: bool = True):
    global _boss5_bgm_tier
    _boss5_bgm_tier = None
    if boss is not None:
        update_boss5_hp_bgm(boss, volume=volume, force=force)
    else:
        _boss5_bgm_tier = 1.0
        play_bgm(
            resolve_boss5_bgm_track(1.0, _boss5_bgm_path_exists),
            volume=volume,
            force=force,
        )


def reset_boss5_hp_bgm():
    global _boss5_bgm_tier
    _boss5_bgm_tier = None


def start_extra_boss_bgm(volume: float | None = None) -> None:
    """エクストラステージ専用BGM（未配置時はボス5曲へフォールバック）。"""
    if _boss5_bgm_path_exists(BGM_EXTRA_BOSS):
        play_bgm(BGM_EXTRA_BOSS, volume=volume)
    else:
        play_bgm(BGM_EXTRA_BOSS_FALLBACK, volume=volume)


def start_extra_boss_tank_bgm(volume: float | None = None) -> None:
    """エクストラボス: 第一形態（タンク）BGM。"""
    if _boss5_bgm_path_exists(BGM_EXTRA_BOSS_TANK):
        play_bgm(BGM_EXTRA_BOSS_TANK, volume=volume)
    else:
        # ない場合は第二形態用（既存の extra boss 曲）へ
        start_extra_boss_bgm(volume=volume)


def start_extra_boss_transform_bgm(volume: float | None = None) -> None:
    """エクストラボス: 変形中 BGM。"""
    if _boss5_bgm_path_exists(BGM_EXTRA_BOSS_TRANSFORM):
        play_bgm(BGM_EXTRA_BOSS_TRANSFORM, volume=volume)
    else:
        start_extra_boss_bgm(volume=volume)


def load_all_sfx(load_sound_fn):
    """load_sound(name) を受け取り、効果音オブジェクトの dict を返す。"""
    def _load_first(*names):
        last_err = None
        for nm in names:
            try:
                return load_sound_fn(nm)
            except Exception as e:
                last_err = e
                continue
        if last_err is not None:
            raise last_err
        raise RuntimeError("no candidate names")

    shot_sound = load_sound_fn("shot.wav")
    explosion_sound = load_sound_fn("explosion.wav")
    warning_sound = load_sound_fn("warning.wav")

    try:
        boss_shield_hit_sound = _load_first("shield_hit_sound.wav", "player_shield_hit.wav")
        boss_shield_break_sound = _load_first("shield_break_sound.wav", "player_shield_break.wav")
    except Exception:
        boss_shield_hit_sound = shot_sound
        boss_shield_break_sound = explosion_sound

    try:
        # 自機シールドは専用音を最優先。無ければ盾系SEへフォールバック。
        player_shield_hit_sound = _load_first("player_shield_hit.wav", "shield_hit_sound.wav")
        player_shield_break_sound = _load_first("player_shield_break.wav", "shield_break_sound.wav")
    except Exception:
        player_shield_hit_sound = shot_sound
        player_shield_break_sound = explosion_sound

    try:
        item_weapon_sound = load_sound_fn("item_weapon.wav")
        item_shield_sound = load_sound_fn("item_shield.wav")
        item_speed_sound = load_sound_fn("item_speed.wav")
    except Exception:
        item_weapon_sound = shot_sound
        item_shield_sound = shot_sound
        item_speed_sound = shot_sound

    try:
        launch_sound = load_sound_fn("launch.wav")
    except Exception:
        launch_sound = warning_sound

    try:
        beam_sound = load_sound_fn("laser.wav")
    except Exception:
        beam_sound = warning_sound

    try:
        ems_get_sound = load_sound_fn("item_speed.wav")
    except Exception:
        ems_get_sound = shot_sound
    try:
        ems_use_sound = load_sound_fn("ems.wav")
    except Exception:
        ems_use_sound = warning_sound

    try:
        laser_warning_sound = load_sound_fn("laser_warning.wav")
    except Exception:
        laser_warning_sound = beam_sound

    try:
        difficulty_select_sound = load_sound_fn("difficulty_select.wav")
    except Exception:
        difficulty_select_sound = shot_sound

    try:
        difficulty_confirm_sound = load_sound_fn("difficulty_confirm.wav")
    except Exception:
        difficulty_confirm_sound = launch_sound

    try:
        title_cheat_sound = load_sound_fn("title_cheat.wav")
    except Exception:
        title_cheat_sound = item_weapon_sound

    try:
        score_tick_sound = load_sound_fn("score_tick.wav")
    except Exception:
        score_tick_sound = difficulty_confirm_sound

    try:
        chain_milestone_sound = load_sound_fn("chain_combo.wav")
    except Exception:
        try:
            chain_milestone_sound = load_sound_fn("item_weapon.wav")
        except Exception:
            chain_milestone_sound = difficulty_confirm_sound

    try:
        ripple_sound = load_sound_fn("ripple.wav")
    except Exception:
        ripple_sound = beam_sound

    try:
        boss_special_alert_sound = load_sound_fn("boss_special_alert.wav")
    except Exception:
        boss_special_alert_sound = laser_warning_sound

    try:
        boss5_gravity_sound = load_sound_fn("boss5_gravity.wav")
    except Exception:
        boss5_gravity_sound = boss_special_alert_sound

    try:
        boss5_meteo3_sound = load_sound_fn("boss5_meteo3.wav")
    except Exception:
        boss5_meteo3_sound = warning_sound

    try:
        boss5_meteo1_sound = load_sound_fn("boss5_meteo1.wav")
    except Exception:
        boss5_meteo1_sound = explosion_sound

    try:
        ending_screen_sound = load_sound_fn("ending.wav")
    except Exception:
        ending_screen_sound = launch_sound

    try:
        boss5_silence_sound = load_sound_fn("boss5_silence.wav")
    except Exception:
        boss5_silence_sound = laser_warning_sound

    try:
        boss5_suck_sound = load_sound_fn("boss5_suck.wav")
    except Exception:
        boss5_suck_sound = boss5_gravity_sound

    try:
        support_arrive_sound = load_sound_fn("support_arrive.wav")
    except Exception:
        support_arrive_sound = launch_sound

    # エクストラボス SE（assets/ 配置名 ← 元ファイル例）
    # extra_boss_enter.wav      ← launch.wav
    # extra_boss_beam_charge.wav ← laser_warning.wav
    # extra_boss_beam_fire.wav   ← extra_laser.wav
    # extra_funnel_shot.wav      ← laser_fannel.wav
    try:
        extra_boss_enter_sound = load_sound_fn("extra_boss_enter.wav")
    except Exception:
        extra_boss_enter_sound = launch_sound
    try:
        extra_boss_beam_charge_sound = load_sound_fn("extra_boss_beam_charge.wav")
    except Exception:
        extra_boss_beam_charge_sound = laser_warning_sound
    try:
        extra_boss_beam_fire_sound = load_sound_fn("extra_boss_beam_fire.wav")
    except Exception:
        extra_boss_beam_fire_sound = beam_sound
    try:
        extra_funnel_shot_sound = load_sound_fn("extra_funnel_shot.wav")
    except Exception:
        extra_funnel_shot_sound = beam_sound
    try:
        extra_boss_transform_sound = load_sound_fn("extra_boss_transform.wav")
    except Exception:
        extra_boss_transform_sound = boss_shield_break_sound

    return {
        "shot_sound": shot_sound,
        "explosion_sound": explosion_sound,
        "warning_sound": warning_sound,
        "boss_shield_hit_sound": boss_shield_hit_sound,
        "boss_shield_break_sound": boss_shield_break_sound,
        "player_shield_hit_sound": player_shield_hit_sound,
        "player_shield_break_sound": player_shield_break_sound,
        "item_weapon_sound": item_weapon_sound,
        "item_shield_sound": item_shield_sound,
        "item_speed_sound": item_speed_sound,
        "launch_sound": launch_sound,
        "beam_sound": beam_sound,
        "ems_get_sound": ems_get_sound,
        "ems_use_sound": ems_use_sound,
        "laser_warning_sound": laser_warning_sound,
        "difficulty_select_sound": difficulty_select_sound,
        "difficulty_confirm_sound": difficulty_confirm_sound,
        "title_cheat_sound": title_cheat_sound,
        "score_tick_sound": score_tick_sound,
        "chain_milestone_sound": chain_milestone_sound,
        "ripple_sound": ripple_sound,
        "boss_special_alert_sound": boss_special_alert_sound,
        "boss5_gravity_sound": boss5_gravity_sound,
        "boss5_meteo3_sound": boss5_meteo3_sound,
        "boss5_meteo1_sound": boss5_meteo1_sound,
        "boss5_silence_sound": boss5_silence_sound,
        "boss5_suck_sound": boss5_suck_sound,
        "ending_screen_sound": ending_screen_sound,
        "support_arrive_sound": support_arrive_sound,
        "extra_boss_enter_sound": extra_boss_enter_sound,
        "extra_boss_beam_charge_sound": extra_boss_beam_charge_sound,
        "extra_boss_beam_fire_sound": extra_boss_beam_fire_sound,
        "extra_funnel_shot_sound": extra_funnel_shot_sound,
        "extra_boss_transform_sound": extra_boss_transform_sound,
    }


def install_sfx(target_globals, sfx: dict):
    """main 互換のため効果音をグローバルへ展開。"""
    target_globals.update(sfx)
