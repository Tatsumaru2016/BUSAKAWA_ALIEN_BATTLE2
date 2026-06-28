# ボス1戦 — 味方支援機 設計メモ（未採用・ボス5専用のまま）

## 目的（案・未実装）

- ~~**ボス1戦**中に、ボス5と同種の「味方支援機」が登場~~ → **見送り。支援機はボス5戦のみ**（`boss5_support.py`）。
- **難易度が高いほど出現しやすい**（EASY は稀、NIGHTMARE は手厚い）。高難易度ほどプレイヤーが助けを必要とする想定。
- 挙動・演出の基準実装は既存の [`boss5_support.py`](../boss5_support.py) を流用・一般化する。

---

## 既存実装の整理（ボス5）

| 項目 | 現状 |
|------|------|
| モジュール | `boss5_support.py`（グローバル1機のみ） |
| 初期化 | `init_boss5_support_fight()` — `boss_spawn` でボス5出現時 |
| 更新 | `update_boss5_support()` — `player_input` フェーズ、**ボス5戦中のみ** |
| 描画 | `draw_boss5_support()` — 同上 |
| 終了 | `clear_boss5_support()` — 撃破・死亡・リセット時 |
| 画像 | `support_fighter_1.png` 〜 `_5.png`（`SUPPORT_FIGHTER_COUNT = 5`） |
| SE / 吹き出し | `support_arrive.wav`、`messages.py` の `support_arrive_*` / `support_leave_*` |

### 登場フロー（状態機械）

```text
（抽選成功）
  enter_center → 画面中央へ
  enter_hold   → 中央で短い待機＋リング演出＋到着SE/吹き出し
  enter_join   → 自機左後方へ合流
  active       → 追従・3-way射撃（約20秒）
  leave        → 左へ退場 → 消滅 → 再抽選タイマー開始
```

### 登場トリガー（ボス5）

| 種別 | 定数（目安） | 説明 |
|------|----------------|------|
| 初回タイマー | `SUPPORT_FIRST_DELAY` = 20秒 | 戦闘開始後、最初の1回は **100% 出現**（`_first_deploy_pending`） |
| 周期抽選 | `SUPPORT_REPEAT_INTERVAL` = 25秒 | 支援機がいない間、CD ごとに抽選 |
| 通常確率 | `SUPPORT_SPAWN_CHANCE` = **0.50**（固定） | 2回目以降のランダム |
| 天井（pity） | `SUPPORT_PITY_AFTER_MISSES` = 2 | 連続2回外れたら次は **100%** |
| HP 閾値 | 50% / 25% / 10% | 初めて下回った瞬間 **1回ずつ強制抽選**（既に支援中ならキュー） |

### 戦闘中の制約

- 同時に **1機のみ**（グローバル `_support_fighter`）。
- プレイヤー死亡中は新規スポーンしない（既存機は更新打ち切り）。
- 弾は自機と同じ `bullet_img`、ダメージ 1、3発バラ（縦オフセット）。

---

## ボス1への適用方針

### スコープ

- **ボス1戦の開始〜撃破/ゲームオーバーまで**。ボス2以降は現状どおり（ボス5のみ支援）。
- ボス1撃破・タイトル復帰・`play.reset` 時は必ず `clear_*_support()`。

### 難易度別「出現率」（コア要件）

**原則**: `diff.name` に応じたパラメータテーブル。ボス5の固定 50% は使わない。

#### 案A — 推奨（読みやすい4段階）

| 難易度 | 2回目以降の抽選確率 | 初回（戦闘開始後） | pity（連続不的中） |
|--------|----------------------|--------------------|--------------------|
| EASY | **22%** | 22%（初回も抽選） | 4回で確定 |
| NORMAL | **35%** | 35% | 3回で確定 |
| HARD | **50%** | **80%** | 2回で確定 |
| NIGHTMARE | **65%** | **100%**（現B5同等） | 2回で確定 |

- EASY は「たまに来る頼みの援軍」、NIGHTMARE は「長期戦ではほぼ一度は来る」イメージ。
- 初回を NIGHTMARE のみ 100% にすると、高難易度の「開幕20秒で一度は味方が来る」が保証される。

#### 案B — `DifficultyConfig` にキー追加（実装時）

```python
# settings.py に追加予定の例（数値は案Aと同じ）
support_spawn_chance: float      # 周期抽選
support_first_chance: float       # 初回のみ（100% なら 1.0）
support_pity_misses: int
support_first_delay_frames: int   # 任意: 難易度で短縮
support_repeat_interval_frames: int
```

NIGHTMARE だけ `support_first_delay` を短くする案（任意）:

| 難易度 | 初回まで（秒@60fps） | 再抽選間隔（秒） |
|--------|----------------------|------------------|
| EASY | 24秒 (1440f) | 28秒 |
| NORMAL | 22秒 | 26秒 |
| HARD | 20秒 | 25秒 |
| NIGHTMARE | **16秒** | **22秒** |

→ 高難易度は「早く・頻繁にチャンス」＋「当たりやすい」の二重補助。

### HP 閾値トリガー（ボス1）

ボス1は短い戦闘もあるため、ボス5より **やや早め** を推奨:

| 閾値 | 用途 |
|------|------|
| **60%** | 前半切り下げ |
| **35%** | 中盤 |
| **15%** | 瀕死 |

- 各閾値 **1回だけ** 強制抽選（既存 `_hp_triggers_used` と同じ）。
- 難易度による確率とは **独立**（どの難易度でも「危ないときの救済」）。

### 同時出現・他ボスとの関係

- グローバル1機のままなら、理論上ボス1→即ボス5デバッグ等では `clear` 必須（既存と同じ）。
- 将来ボス2/3にも広げるなら **`boss_support` 一般化**＋`active_boss_type` でパラメータ切替がよい。

---

## 実装アーキテクチャ案（未着手）

### 推奨: 一般化モジュール

```text
boss_support.py
  SupportFightConfig(dataclass)  # 確率・delay・HP閾値
  CONFIG_BY_BOSS = {1: ..., 5: ...}
  init_boss_support(boss_type)
  update_boss_support(...)       # boss_type で config 選択
  draw_boss_support(...)
  clear_boss_support()
```

- `boss5_support.py` は薄いラッパーにするか、import 先を差し替えて削除。
- **ボス1用定数**は `CONFIG_BY_BOSS[1]` または `DifficultyConfig` から生成。

### 接続ポイント（実装時チェックリスト）

| 場所 | 変更内容 |
|------|----------|
| `boss_spawn.activate_boss_after_warning` | `boss_type == 1` で `init_boss_support(1)` |
| `game_loop/phases/player_input.py` | `boss.boss_type == 1` でも `update/draw_boss_support` |
| `game_loop/boss_combat.py` / `boss5_death.py` | ボス1撃破時 `clear_boss_support()`（未呼びなら追加） |
| `game_state.PlayState.reset` | 既存 `clear_boss5_support` → 一般化後 `clear` |
| `settings.py` | 難易度別 `support_*` キー（案B） |
| `messages.py` | 流用可（variant 0〜4）。ボス1専用セリフは任意 |

### テスト観点（実装後）

1. EASY: 1戦で 0〜1 回が多いこと。
2. NIGHTMARE: 20秒前後でほぼ1回、HP50%前後でも追加チャンス。
3. 支援中にボス1撃破 → 支援消滅・再抽選停止。
4. 被弾・ゲームオーバーで支援が残らないこと。
5. 吹き出しが自機＋支援アンカーで表示されること（既存 `player_input`）。

---

## パラメータ早見（実装用コピペ）

```python
# 案A + 案B タイミング（frames @ 60fps）
BOSS1_SUPPORT_BY_DIFF = {
    "EASY":      dict(chance=0.22, first_chance=0.22, pity=4, first_delay=1440, repeat=1680),
    "NORMAL":    dict(chance=0.35, first_chance=0.35, pity=3, first_delay=1320, repeat=1560),
    "HARD":      dict(chance=0.50, first_chance=0.80, pity=2, first_delay=1200, repeat=1500),
    "NIGHTMARE": dict(chance=0.65, first_chance=1.00, pity=2, first_delay=960,  repeat=1320),
}
BOSS1_SUPPORT_HP_TRIGGERS = (0.60, 0.35, 0.15)
# 挙動系は B5 と共通: ACTIVE=1200f, SHOT_INTERVAL=14, など
```

---

## 未決定・要確認

1. **初回100%を NIGHTMARE のみ**にするか、HARD も 80% でよいか。
2. ボス1専用の `support_arrive` セリフを分けるか（キャラ世界観）。
3. ボス1戦が短すぎる EASY で「一度も来ない」が多い → `first_delay` を EASY だけ短くするか。
4. 実装時、ボス5の定数を壊さないよう **ボス5は従来どおり固定50%/初回100%** を維持するか、全ボス難易度連動に統一するか。

---

## 実装順序（予定）

1. `boss_support.py` へ一般化（config + boss_type）。
2. `DifficultyConfig` に `support_*` 追加、ボス1のみ参照。
3. `boss_spawn` / `player_input` / `clear` 配線。
4. プレイテストで表の確率を微調整。

**現時点: ドキュメントのみ。コード変更なし。**
