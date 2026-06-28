# assets_loader.py — 画像・フォントの読み込みとパス解決

import os
import sys

import pygame

from settings import SFX_GAIN
from sfx_mute import is_sfx_muted
from boss5_support import load_support_fighter_images


class GameSound:
    """効果音: ゲームオーバー演出中は play() を無視（BGM は mixer.music）。"""

    __slots__ = ("_sound",)

    def __init__(self, sound: pygame.mixer.Sound) -> None:
        self._sound = sound

    def play(self, *args, **kwargs):
        if is_sfx_muted():
            return None
        return self._sound.play(*args, **kwargs)

    def stop(self):
        return self._sound.stop()

    def set_volume(self, *args, **kwargs):
        return self._sound.set_volume(*args, **kwargs)

# 描画・フォールバック用カラー（main / render_ui 共通）
WHITE = (255, 255, 255)
RED = (255, 80, 80)
GREEN = (40, 255, 100)
CYAN = (80, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 130, 0)
DARK_ORANGE = (180, 70, 0)
BLUE = (30, 80, 255)
LIGHT_BLUE = (100, 220, 255)
GRAY = (50, 50, 50)
DARK_GRAY = (20, 20, 20)
BLACK = (0, 0, 0)


def _resolve_asset_path(relative_path: str) -> str:
    """開発 / onefile / 外付け assets フォルダのいずれでも解決する。"""
    rel = relative_path.replace("\\", "/")
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        external = os.path.join(exe_dir, rel)
        if os.path.exists(external):
            return external
    if hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, rel)
        if os.path.exists(bundled):
            return bundled
    return os.path.join(os.path.abspath("."), rel)


def get_asset_path(relative_path):
    """EXE 化後も開発環境でも正しくアセットのパスを返す。"""
    return _resolve_asset_path(relative_path)


def resource_path(relative_path):
    return _resolve_asset_path(relative_path)


def load_image(name):
    return pygame.image.load(resource_path(f"assets/{name}")).convert_alpha()


def _prepare_play_screen_image(img, width, height):
    """全面UI・自機: 原寸が目標と一致すればスケールしない。"""
    img = img.convert_alpha()
    target = (width, height)
    if img.get_size() != target:
        return pygame.transform.smoothscale(img, target)
    return img


def _prepare_bullet_image(img, size: tuple[int, int]):
    """弾スプライト: 黒透過＋指定サイズへスムーズスケール。"""
    img = img.convert()
    img.set_colorkey((0, 0, 0))
    img = img.convert_alpha()
    if img.get_size() == size:
        return img
    return pygame.transform.smoothscale(img, size)


def _prepare_enemy_bullet_image(img):
    """雑魚弾: ENEMY_BULLET_SIZE。"""
    from settings import ENEMY_BULLET_SIZE

    return _prepare_bullet_image(img, ENEMY_BULLET_SIZE)


def _prepare_enemy_sprite(img):
    """雑魚・エース・特別機: GRUNT_ENEMY_SPRITE_SIZE (130x87) へスムーズスケール（原寸一致時はそのまま）。"""
    from settings import GRUNT_ENEMY_SPRITE_SIZE

    img = img.convert_alpha()
    target = GRUNT_ENEMY_SPRITE_SIZE
    if img.get_size() == target:
        return img
    return pygame.transform.smoothscale(img, target)


def _prepare_extra_parallax_scroll(img, height):
    """エクストラ far/mid: 高さ合わせで横スクロール（パララックス用）。"""
    img = img.convert_alpha()
    if img.get_height() != height:
        scale = height / img.get_height()
        w = max(1, int(img.get_width() * scale))
        return pygame.transform.smoothscale(img, (w, height))
    return img


def _prepare_extra_front_scroll(img, height):
    """エクストラ front: 高さ合わせ＋中央の黒を透過して横スクロール用にする。"""
    if img.get_height() != height:
        scale = height / img.get_height()
        w = max(1, int(img.get_width() * scale))
        img = pygame.transform.smoothscale(img, (w, height))
    img = img.convert()
    img.set_colorkey((0, 0, 0))
    return img


def load_life_icon_image():
    """HUD 残機表示用（白シルエット・黒背景を透過）。"""
    path = resource_path("assets/player_zanki.png")
    surf = pygame.image.load(path)
    surf.set_colorkey((0, 0, 0))
    return surf.convert_alpha()


def _resolve_sound_path(name: str) -> str:
    """デスクトップは WAV、Web は同名 OGG を優先（pygbag 推奨）。"""
    if name.lower().endswith(".wav") and sys.platform == "emscripten":
        ogg_name = name[:-4] + ".ogg"
        ogg_path = resource_path(f"assets/{ogg_name}")
        if os.path.isfile(ogg_path):
            return ogg_path
    return resource_path(f"assets/{name}")


def load_sound(name, gain=None):
    """効果音を読み込み、mixer の音量で調整（numpy / sndarray は使わない）。"""
    if gain is None:
        gain = SFX_GAIN
    sound = pygame.mixer.Sound(_resolve_sound_path(name))
    sound.set_volume(max(0.0, min(1.0, float(gain))))
    return GameSound(sound)


def load_boss_bullet_image(name, size, fallback, color):
    try:
        return _prepare_bullet_image(load_image(name), size)
    except Exception:
        if fallback is not None:
            if fallback.get_size() == size:
                return fallback
            return pygame.transform.smoothscale(fallback, size)
        surf = pygame.Surface(size, pygame.SRCALPHA)
        cx, cy = size[0] // 2, size[1] // 2
        pygame.draw.circle(surf, color, (cx, cy), max(5, min(size) // 2 - 3))
        pygame.draw.circle(surf, WHITE, (cx, cy), max(2, min(size) // 5))
        return surf


def set_window_icon():
    try:
        pygame.display.set_icon(load_image("icon.png"))
    except Exception:
        pass


def load_all_assets(width, height, *, boot_screen=None):
  """ゲームで使う画像・フォントを一括読み込み。dict を返す。"""
  out = {}

  def _boot(msg, pct):
      if boot_screen is None:
          return
      from web_loader import paint_boot_screen

      paint_boot_screen(boot_screen, msg, pct)

  _boot("背景を読み込んでいます…", 18)

  for key, fname in (
      ("bg_far", "bg_far.png"),
      ("bg_mid", "bg_mid.png"),
      ("bg_front", "bg_front.png"),
  ):
      out[key] = _prepare_play_screen_image(load_image(fname), width, height)

  try:
      out["boss5_bg_far"] = _prepare_play_screen_image(
          load_image("boss5_bg_far.png"), width, height,
      )
  except Exception:
      out["boss5_bg_far"] = out["bg_far"]
  try:
      out["boss5_bg_mid"] = _prepare_play_screen_image(
          load_image("boss5_bg_mid.png"), width, height,
      )
  except Exception:
      out["boss5_bg_mid"] = out["bg_mid"]
  try:
      out["boss5_bg_front"] = _prepare_play_screen_image(
          load_image("boss5_bg_front.png"), width, height,
      )
  except Exception:
      out["boss5_bg_front"] = out["bg_front"]

  try:
      out["extra_bg_far"] = _prepare_extra_parallax_scroll(
          load_image("extra_bg_far.png"), height,
      )
  except Exception:
      out["extra_bg_far"] = out["bg_far"]
  try:
      out["extra_bg_mid"] = _prepare_extra_parallax_scroll(
          load_image("extra_bg_mid.png"), height,
      )
  except Exception:
      out["extra_bg_mid"] = out["bg_mid"]
  try:
      out["extra_bg_front"] = _prepare_extra_front_scroll(
          load_image("extra_bg_front.png"), height,
      )
  except Exception:
      out["extra_bg_front"] = _prepare_extra_front_scroll(out["bg_front"], height)

  for key, fname in (
      ("notice_img", "notice.png"),
      ("next_screen_img", "next_screen.png"),
      ("next_screen2_img", "next_screen2.png"),
  ):
      try:
          out[key] = _prepare_play_screen_image(load_image(fname), width, height)
      except Exception:
          out[key] = None

  out["title_img"] = _prepare_play_screen_image(load_image("title.png"), width, height)
  _boot("UI 画像を読み込んでいます…", 32)
  out["warning_img"] = pygame.transform.smoothscale(load_image("warning.png"), (400, 150))
  out["gameover_img"] = load_image("gameover.png")

  try:
      out["ending_img"] = _prepare_play_screen_image(load_image("ending.png"), width, height)
  except Exception:
      out["ending_img"] = pygame.Surface((width, height), pygame.SRCALPHA)
      out["ending_img"].fill((0, 0, 0, 180))

  extra_ending_slides = []
  for i in range(1, 8):
      try:
          extra_ending_slides.append(
              _prepare_play_screen_image(load_image(f"ending{i}.png"), width, height)
          )
      except Exception:
          pass
  out["extra_ending_slides"] = extra_ending_slides

  for key, fname in (
      ("diff_select_bg", "diff_select_bg.png"),
      ("config_keyboard_bg", "config_keyboard_bg.png"),
      ("config_controller_bg", "config_controller_bg.png"),
  ):
      try:
          out[key] = _prepare_play_screen_image(load_image(fname), width, height)
      except Exception:
          out[key] = None

  diff_imgs = {}
  for dname in ("easy", "normal", "hard", "nightmare"):
      key = dname.upper()
      diff_imgs[key] = {}
      for state in ("on", "off"):
          try:
              diff_imgs[key][state] = load_image(f"diff_{dname}_{state}.png")
          except Exception:
              diff_imgs[key][state] = None
  out["diff_imgs"] = diff_imgs

  from settings import PLAYER_SPRITE_FILES, PLAYER_SPRITE_SIZE

  def _prepare_player(img):
      return _prepare_play_screen_image(img, *PLAYER_SPRITE_SIZE)

  player_images = {}
  for key, filename in PLAYER_SPRITE_FILES.items():
      try:
          player_images[key] = _prepare_player(load_image(filename))
      except Exception:
          if key == "shot" and "normal" in player_images:
              player_images["shot"] = player_images["normal"]
          elif key != "shot":
              raise
  if "shot" not in player_images:
      player_images["shot"] = player_images["normal"]
  out["player_images"] = player_images
  _boot("弾・敵グラフィックを読み込んでいます…", 48)
  try:
      out["life_icon_img"] = load_life_icon_image()
  except Exception:
      out["life_icon_img"] = pygame.transform.scale(player_images["normal"], (36, 20))

  from settings import PLAYER_BULLET_SIZE

  out["bullet_img"] = _prepare_bullet_image(load_image("bullet.png"), PLAYER_BULLET_SIZE)
  try:
      out["laser_img"] = pygame.transform.scale(load_image("laser.png"), (420, 22))
  except Exception:
      out["laser_img"] = pygame.Surface((420, 22), pygame.SRCALPHA)
  try:
      out["player_shield_bar_img"] = load_image("player_shield_bar.png").convert_alpha()
  except Exception:
      pw, ph = PLAYER_SPRITE_SIZE
      s = pygame.Surface((pw, 10), pygame.SRCALPHA)
      pygame.draw.rect(s, (40, 55, 75, 200), (0, 0, pw, 10), border_radius=2)
      pygame.draw.rect(s, (0, 200, 255, 220), (1, 1, pw - 2, 8), border_radius=1)
      out["player_shield_bar_img"] = s
  out["shield_img"] = out["player_shield_bar_img"]

  from settings import ENEMY_ACE_COUNT, ENEMY_GRUNT_COUNT

  out["enemy_images"] = []
  for i in range(1, ENEMY_GRUNT_COUNT + 1):
      out["enemy_images"].append(_prepare_enemy_sprite(load_image(f"enemy_{i:02d}.png")))
  for i in range(1, ENEMY_ACE_COUNT + 1):
      out["enemy_images"].append(_prepare_enemy_sprite(load_image(f"enemy_ace{i:02d}.png")))
  out["enemy_images"].append(_prepare_enemy_sprite(load_image("enemy_special.png")))
  out["enemy_bullet_img"] = _prepare_enemy_bullet_image(load_image("enemy_bullet.png"))
  try:
      out["grunt_homing_bullet_img"] = _prepare_enemy_bullet_image(
          load_image("homing_bullet.png")
      )
  except Exception:
      out["grunt_homing_bullet_img"] = out["enemy_bullet_img"]
  try:
      _zako = load_image("explosion_zako.png")
      _zako.set_colorkey((0, 0, 0))
      out["explosion_zako_img"] = _zako.convert_alpha()
  except Exception:
      _zako = pygame.Surface((64, 64), pygame.SRCALPHA)
      pygame.draw.circle(_zako, (255, 200, 80), (32, 32), 28)
      pygame.draw.circle(_zako, (255, 255, 200), (32, 32), 14)
      out["explosion_zako_img"] = _zako
  from settings import BOSS_BULLET_SIZE

  _boss_bullet_sz = BOSS_BULLET_SIZE
  try:
      out["homing_bullet_img"] = _prepare_bullet_image(
          load_image("homing_bullet.png"), _boss_bullet_sz
      )
  except Exception:
      out["homing_bullet_img"] = None

  from settings import TURRET_BULLET_SIZE

  try:
      out["turret_bullet_img"] = _prepare_bullet_image(
          load_image("turret_bullet.png"), TURRET_BULLET_SIZE
      )
  except Exception:
      out["turret_bullet_img"] = None
  try:
      out["turret_top_img"] = load_image("turret_top.png").convert_alpha()
  except Exception:
      t = pygame.Surface((100, 150), pygame.SRCALPHA)
      pygame.draw.rect(t, ORANGE, (8, 14, 84, 94))
      pygame.draw.rect(t, RED, (36, 108, 28, 30))
      out["turret_top_img"] = t

  try:
      out["turret_bottom_img"] = load_image("turret_bottom.png").convert_alpha()
  except Exception:
      t = pygame.Surface((100, 150), pygame.SRCALPHA)
      pygame.draw.rect(t, RED, (36, 12, 28, 30))
      pygame.draw.rect(t, ORANGE, (8, 44, 84, 94))
      out["turret_bottom_img"] = t

  for key, fname, color in (
      ("boss_bullet_img_01", "boss_bullet_01.png", CYAN),
      ("boss_bullet_img_02", "boss_bullet_02.png", YELLOW),
      ("boss_bullet_img_03", "boss_bullet_03.png", RED),
  ):
      try:
          out[key] = _prepare_bullet_image(load_image(fname), _boss_bullet_sz)
      except Exception:
          s = pygame.Surface(_boss_bullet_sz, pygame.SRCALPHA)
          pygame.draw.circle(
              s, color, (_boss_bullet_sz[0] // 2, _boss_bullet_sz[1] // 2),
              _boss_bullet_sz[0] // 2 - 2,
          )
          out[key] = s

  b01, b02, b03 = out["boss_bullet_img_01"], out["boss_bullet_img_02"], out["boss_bullet_img_03"]
  hom = out["homing_bullet_img"]
  out["boss_specific_bullet_imgs"] = {
      "boss1_bullet": load_boss_bullet_image("boss1_bullet.png", _boss_bullet_sz, b01, CYAN),
      "boss1_homing": load_boss_bullet_image(
          "boss1_homing.png", _boss_bullet_sz, hom, (80, 255, 255)
      ),
      "boss2_bullet": load_boss_bullet_image("boss2_bullet.png", _boss_bullet_sz, b02, YELLOW),
      "boss2_bubble": load_boss_bullet_image("boss2_bubble.png", (64, 64), hom, WHITE),
      "boss2_homing": load_boss_bullet_image(
          "boss2_homing.png", _boss_bullet_sz, hom, (255, 220, 80)
      ),
      "boss3_bullet": load_boss_bullet_image("boss3_bullet.png", _boss_bullet_sz, b03, RED),
      "boss3_homing": load_boss_bullet_image(
          "boss3_homing.png", _boss_bullet_sz, hom, (255, 90, 90)
      ),
      "boss4_bullet": load_boss_bullet_image(
          "boss4_bullet.png", _boss_bullet_sz, b03, (120, 255, 120)
      ),
      "boss4_turret_bullet": load_boss_bullet_image(
          "boss4_turret_bullet.png",
          TURRET_BULLET_SIZE,
          out.get("turret_bullet_img") or b03,
          (255, 240, 90),
      ),
  }

  try:
      out["boss3_ufo_img"] = pygame.transform.scale(load_image("boss3_ufo.png"), (72, 48))
  except Exception:
      ufo = pygame.Surface((72, 48), pygame.SRCALPHA)
      pygame.draw.ellipse(ufo, (190, 230, 255), (6, 18, 60, 20))
      pygame.draw.ellipse(ufo, (70, 120, 220), (20, 6, 32, 24))
      pygame.draw.ellipse(ufo, (255, 255, 255), (27, 11, 18, 10))
      for lx in (16, 28, 40, 52):
          pygame.draw.circle(ufo, (255, 80, 80), (lx, 30), 3)
      out["boss3_ufo_img"] = ufo

  try:
      out["boss_bullet_img"] = _prepare_bullet_image(load_image("boss_bullet.png"), _boss_bullet_sz)
  except Exception:
      out["boss_bullet_img"] = hom

  try:
      out["boss_shield_img"] = pygame.transform.scale(load_image("boss_shield.png"), (161, 360))
  except Exception:
      s = pygame.Surface((161, 360), pygame.SRCALPHA)
      pygame.draw.rect(s, (255, 100, 0, 90), (15, 0, 30, 360))
      pygame.draw.rect(s, (255, 200, 50, 180), (35, 0, 8, 360))
      out["boss_shield_img"] = s

  try:
      out["boss_shield_img2"] = pygame.transform.scale(load_image("boss_shield2.png"), (161, 720))
  except Exception:
      s = pygame.Surface((161, 720), pygame.SRCALPHA)
      pygame.draw.rect(s, (255, 100, 0, 90), (15, 0, 30, 720))
      pygame.draw.rect(s, (255, 200, 50, 180), (35, 0, 8, 720))
      out["boss_shield_img2"] = s

  b1_size = (668, 400)
  out["midboss_img1"] = pygame.transform.scale(load_image("midboss1.png"), b1_size)
  _boot("ボス画像を読み込んでいます…", 62)
  try:
      out["midboss_img1b"] = pygame.transform.scale(load_image("midboss1b.png"), b1_size)
  except Exception:
      out["midboss_img1b"] = out["midboss_img1"]
  b2_size = (701, 325)
  out["midboss_img2"] = pygame.transform.scale(load_image("midboss2.png"), b2_size)
  try:
      out["midboss_img2b"] = pygame.transform.scale(load_image("midboss2b.png"), b2_size)
  except Exception:
      out["midboss_img2b"] = out["midboss_img2"]
  b3_size = (729, 400)
  out["midboss_img3"] = pygame.transform.scale(load_image("midboss3.png"), b3_size)
  try:
      out["midboss_img3b"] = pygame.transform.scale(load_image("midboss3b.png"), b3_size)
  except Exception:
      out["midboss_img3b"] = out["midboss_img3"]

  fish_size = (112, 56)
  try:
      out["boss2_fish_img"] = pygame.transform.smoothscale(load_image("boss2_fish.png"), fish_size)
  except Exception:
      f = pygame.Surface(fish_size, pygame.SRCALPHA)
      pygame.draw.ellipse(f, (255, 200, 80), (8, 14, 88, 28))
      pygame.draw.polygon(f, (255, 140, 60), [(4, 28), (22, 18), (22, 38)])
      out["boss2_fish_img"] = f

  try:
      midboss4_d = load_image("midboss4_d.png").convert_alpha()
  except Exception:
      midboss4_d = pygame.Surface((400, 400), pygame.SRCALPHA)
      midboss4_d.fill((60, 160, 60, 220))
      pygame.draw.circle(midboss4_d, (200, 255, 100), (120, 200), 80, 6)
  try:
      midboss4_e = load_image("midboss4_e.png").convert_alpha()
  except Exception:
      midboss4_e = midboss4_d
  try:
      midboss4_f = load_image("midboss4_f.png").convert_alpha()
  except Exception:
      midboss4_f = midboss4_d
  out["midboss4_body_d"] = midboss4_d
  out["midboss4_body_e"] = midboss4_e
  out["midboss4_body_f"] = midboss4_f
  out["midboss4_body_src"] = midboss4_d
  out["midboss4_body_img"] = midboss4_d

  # 上下帯: boss4_up / boss4_down（元サイズのまま）
  def _load_boss4_strip(primary: str, legacy: str):
      for name in (primary, legacy):
          try:
              return load_image(name).convert_alpha()
          except Exception:
              continue
      return None

  out["boss4_overlay_top_img"] = _load_boss4_strip(
      "boss4_up.png", "boss4_overlay_top.png"
  )
  out["boss4_overlay_bottom_img"] = _load_boss4_strip(
      "boss4_down.png", "boss4_overlay_bottom.png"
  )

  boss5_wall_size = (600, 639)
  midboss5_images = {}
  try:
      img5 = pygame.transform.scale(load_image("midboss5.png"), boss5_wall_size)
      try:
          img5b = pygame.transform.scale(load_image("midboss5b.png"), boss5_wall_size)
      except Exception:
          img5b = img5
      try:
          img5d = pygame.transform.scale(load_image("midboss5_dead.png"), boss5_wall_size)
      except Exception:
          img5d = img5
      midboss5_images = {
          "normal": img5,
          "attack": img5,
          "special": img5b,
          "defeat": img5d,
      }
  except Exception:
      try:
          img5 = pygame.transform.scale(load_image("midboss5.png"), boss5_wall_size)
          try:
              img5d = pygame.transform.scale(load_image("midboss5_dead.png"), boss5_wall_size)
          except Exception:
              img5d = img5
          midboss5_images = {
              "normal": img5,
              "attack": img5,
              "special": img5,
              "defeat": img5d,
          }
      except Exception:
          img5 = pygame.transform.scale(out["midboss_img3"], boss5_wall_size)
          midboss5_images = {
              "normal": img5,
              "attack": img5,
              "special": img5,
              "defeat": img5,
          }
  out["midboss5_images"] = midboss5_images

  extra_boss_h = 580
  extra_boss_images = {}

  def _scale_extra_boss_surface(img):
      w = max(1, int(img.get_width() * extra_boss_h / img.get_height()))
      return pygame.transform.smoothscale(img, (w, extra_boss_h))

  def _scale_extra_boss_to_width(img, target_w: int):
      h = max(1, int(img.get_height() * target_w / max(1, img.get_width())))
      return pygame.transform.smoothscale(img, (target_w, h))

  try:
      _ex_normal = _scale_extra_boss_surface(load_image("extra_boss_normal.png"))
      _ex_w = _ex_normal.get_width()
      extra_boss_images = {
          "normal": _ex_normal,
          "charge": _scale_extra_boss_surface(load_image("extra_boss_charge.png")),
          "fire": _scale_extra_boss_surface(load_image("extra_boss_fire.png")),
          "tank1": _scale_extra_boss_surface(load_image("extra_boss_tank1.png")),
          "tank2": _scale_extra_boss_surface(load_image("extra_boss_tank2.png")),
          "tank3": _scale_extra_boss_surface(load_image("extra_boss_tank3.png")),
          "funnel_pose": _scale_extra_boss_to_width(
              load_image("extra_boss_funnel_pose.png"), _ex_w,
          ),
      }
      try:
          extra_boss_images["wave_pose"] = _scale_extra_boss_to_width(
              load_image("extra_boss_wave_pose.png"), _ex_w,
          )
      except Exception:
          extra_boss_images["wave_pose"] = extra_boss_images["funnel_pose"]
      funnel_raw = load_image("extra_funnel.png")
      fw = max(72, int(funnel_raw.get_width() * 1.15))
      fh = max(42, int(funnel_raw.get_height() * 1.15))
      out["extra_funnel_img"] = pygame.transform.smoothscale(funnel_raw, (fw, fh))
  except Exception:
      fallback = midboss5_images.get("normal") or out.get("midboss_img3")
      if fallback is not None:
          extra_boss_images = {
              "normal": fallback,
              "charge": fallback,
              "fire": fallback,
              "tank1": fallback,
              "tank2": fallback,
              "tank3": fallback,
              "funnel_pose": fallback,
              "wave_pose": fallback,
          }
      out["extra_funnel_img"] = pygame.Surface((80, 46), pygame.SRCALPHA)
      pygame.draw.polygon(
          out["extra_funnel_img"],
          (160, 80, 220),
          [(40, 4), (76, 42), (4, 42)],
      )
  out["extra_boss_images"] = extra_boss_images

  try:
      cutter_raw = load_image("extra_boss_cutter.png")
      cw, ch = 182, 165
      scaled = pygame.transform.smoothscale(cutter_raw, (cw, ch))
      # 右→左へ飛ぶので先端が左向きになるよう反転
      out["extra_beam_cutter_img"] = pygame.transform.flip(scaled, True, False)
  except Exception:
      out["extra_beam_cutter_img"] = None

  play_w = out.get("WIDTH", 1280)
  try:
      fighter_raw = load_image("extra_tank_striker_fighter.png")
      fw = max(72, int(play_w * 0.11))
      fh = max(28, int(fighter_raw.get_height() * fw / max(1, fighter_raw.get_width())))
      out["extra_tank_striker_img"] = pygame.transform.smoothscale(
          fighter_raw, (fw, fh),
      )
  except Exception:
      out["extra_tank_striker_img"] = None
  try:
      missile_raw = load_image("extra_tank_striker_missile.png")
      mw = max(22, int(play_w * 0.028))
      mh = max(36, int(missile_raw.get_height() * mw / max(1, missile_raw.get_width())))
      out["extra_tank_striker_missile_img"] = pygame.transform.smoothscale(
          missile_raw, (mw, mh),
      )
  except Exception:
      out["extra_tank_striker_missile_img"] = None

  try:
      out["boss_ripple_base_img"] = load_image("boss_ripple.png")
  except Exception:
      r = pygame.Surface((32, 32), pygame.SRCALPHA)
      pygame.draw.circle(r, CYAN, (16, 16), 16, 3)
      out["boss_ripple_base_img"] = r
  b1_ripple_size = (80, 80)
  try:
      out["boss1_ripple_img"] = pygame.transform.smoothscale(
          load_image("boss1_bubble.png"), b1_ripple_size
      )
  except Exception:
      try:
          out["boss1_ripple_img"] = pygame.transform.smoothscale(
              load_image("boss_ripple.png"), b1_ripple_size
          )
      except Exception:
          out["boss1_ripple_img"] = pygame.transform.smoothscale(
              out["boss_ripple_base_img"], b1_ripple_size
          )

  meteor_size = (80, 48)
  try:
      out["meteor_img"] = pygame.transform.scale(load_image("meteor.png"), meteor_size)
  except Exception:
      try:
          out["meteor_img"] = pygame.transform.scale(load_image("boss5_meteor.png"), meteor_size)
      except Exception:
          m = pygame.Surface(meteor_size, pygame.SRCALPHA)
          pygame.draw.ellipse(m, (120, 75, 45), (6, 14, 68, 26))
          pygame.draw.ellipse(m, (200, 140, 80), (14, 18, 48, 16))
          pygame.draw.circle(m, (255, 220, 160), (22, 24), 6)
          out["meteor_img"] = m

  meteor_small_size = (40, 40)
  try:
      out["meteor_small_img"] = pygame.transform.smoothscale(
          load_image("smallmeteor.png"), meteor_small_size
      )
  except Exception:
      sw, sh = meteor_small_size
      out["meteor_small_img"] = pygame.transform.smoothscale(out["meteor_img"], (sw, sh))

  obstacle_size = (72, 72)
  try:
      out["meteor_obstacle_img"] = pygame.transform.smoothscale(
          load_image("meteor_obstacle.png"), obstacle_size
      )
  except Exception:
      out["meteor_obstacle_img"] = None

  try:
      out["meteor_zako_explosion_img"] = load_image("explosion_zako.png")
  except Exception:
      out["meteor_zako_explosion_img"] = None

  out["support_fighter_images"] = load_support_fighter_images(load_image)
  _boot("アイテム画像を読み込んでいます…", 72)

  out["power_weapon_img"] = pygame.transform.scale(load_image("power_weapon.png"), (56, 56))
  try:
      out["power_laser_charge_img"] = pygame.transform.scale(
          load_image("power_laser_charge.png"), (56, 56)
      )
  except Exception:
      p = pygame.Surface((56, 56), pygame.SRCALPHA)
      pygame.draw.circle(p, (120, 220, 255), (28, 28), 26)
      pygame.draw.circle(p, (220, 250, 255), (28, 28), 13)
      pygame.draw.circle(p, (40, 120, 200), (28, 28), 26, 2)
      out["power_laser_charge_img"] = p
  out["power_shield_img"] = pygame.transform.scale(load_image("power_shield.png"), (56, 56))
  out["power_speed_img"] = pygame.transform.scale(load_image("power_speed.png"), (56, 56))
  try:
      out["power_super_img"] = pygame.transform.scale(load_image("power_super.png"), (56, 56))
  except Exception:
      p = pygame.Surface((56, 56), pygame.SRCALPHA)
      pygame.draw.circle(p, (255, 220, 80), (28, 28), 26)
      pygame.draw.circle(p, (255, 255, 200), (28, 28), 15)
      pygame.draw.circle(p, (255, 160, 30), (28, 28), 26, 2)
      out["power_super_img"] = p
  try:
      out["power_1up_img"] = pygame.transform.scale(load_image("power_1up.png"), (56, 56))
  except Exception:
      p = pygame.Surface((56, 56), pygame.SRCALPHA)
      pygame.draw.circle(p, (50, 220, 50), (28, 28), 26)
      pygame.draw.circle(p, (180, 255, 180), (28, 28), 16)
      _f = pygame.font.Font(get_asset_path("assets/NotoSansJP-Regular.ttf"), 18)
      _t = _f.render("1UP", True, (0, 80, 0))
      p.blit(_t, _t.get_rect(center=(28, 28)))
      out["power_1up_img"] = p

  font_path = get_asset_path("assets/NotoSansJP-Regular.ttf")

  def _load_fin_script_font(size: int = 78) -> pygame.font.Font:
      win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
      for fname in ("segoesc.ttf", "SegoeScript.ttf", "BRUSHSCI.TTF", "LCALLIG.TTF"):
          path = os.path.join(win_fonts, fname)
          if os.path.isfile(path):
              try:
                  return pygame.font.Font(path, size)
              except Exception:
                  pass
      for name in (
          "Segoe Script",
          "Brush Script MT",
          "Lucida Handwriting",
          "Monotype Corsiva",
      ):
          try:
              f = pygame.font.SysFont(name, size)
              if f.render("F", True, (255, 255, 255)).get_width() > 4:
                  return f
          except Exception:
              pass
      return pygame.font.Font(font_path, size)

  out["fin_script_font"] = _load_fin_script_font()
  out["font"] = pygame.font.Font(font_path, 28)
  out["font2"] = pygame.font.Font(font_path, 16)
  out["font_hud_sm"] = pygame.font.Font(font_path, 14)
  out["hud_font"] = pygame.font.Font(font_path, 44)
  out["hp_bar_font"] = pygame.font.Font(font_path, 15)
  out["big_font"] = pygame.font.Font(font_path, 64)
  out["noto_font_path"] = font_path
  _boot("フォントを読み込んでいます…", 85)

  return out


def install_assets(target_globals, assets: dict):
    """読み込み結果を main のグローバルへ展開（既存コード互換）。"""
    for key, value in assets.items():
        target_globals[key] = value
    target_globals.update({
        "WHITE": WHITE,
        "RED": RED,
        "GREEN": GREEN,
        "CYAN": CYAN,
        "YELLOW": YELLOW,
        "ORANGE": ORANGE,
        "DARK_ORANGE": DARK_ORANGE,
        "BLUE": BLUE,
        "LIGHT_BLUE": LIGHT_BLUE,
        "GRAY": GRAY,
        "DARK_GRAY": DARK_GRAY,
        "BLACK": BLACK,
    })
