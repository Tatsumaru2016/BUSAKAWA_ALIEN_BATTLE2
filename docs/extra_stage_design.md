# エクストラステージ構想メモ（実装前）

## 推奨フロー（エンディング＋スコアを必ず見せる）

```
Boss5撃破
  → PLAY + ending_delay_timer（花火・BGM_ENDING）約3秒
  → ENDING（スコア + 2択: エクストラ / 難易度選択）
  → ENDING_EXTRA_DIVE（白黒ボス口へ自機が縮小して吸い込まれる）
        完了後 ENTER → DIFFICULTY_SELECT（EXTRA_PLAY は未実装）
  → EXTRA_PLAY（将来: 専用ボス1体）
  → EXTRA_CLEAR 演出 → タイトル or 真エンディング
```

`ENDING` のまま2択を足すより、**スコア表示専用の ENDING の次に PROMPT を挟む**と、
「クリア結果を見逃さない」「エクストラは任意」が両立しやすい。

## 状態・データ

| 項目 | 案 |
|------|-----|
| 画面 | `ENDING_EXTRA_PROMPT = 6`, `EXTRA_PLAY = 7`（main.py に予約済み） |
| セッション | `PlayState.extra_run: bool`, `extra_boss_defeated: bool` |
| ボス | `boss_type == 6` または `extra_boss` 専用クラス（本編 MidBoss と分離） |
| 難易度 | 本編と同じ `diff` を引き継ぎ、HP/弾速だけ `extra_*` 倍率 |

## エクストラへ進む条件（例）

- **デフォルト**: クリア後は必ず PROMPT 表示（誰でも挑戦可）
- **任意の厳しめ**: ノーコンティニュー / 残機1以上 / ハイスコア更新 など
- **隠し**: エンディング中にコナミ風入力で解禁（タイトルチートと別）

## エクストラボス設計の方向性

- 本編5体の「要素寄せ」より、**1体にギミックを集中**（実装・テストが楽）
- 本編資産流用: BGM差し替え、背景1枚、ボス画像1セット
- 撃破後: 短いスタッフロール or 「真クリア」メダル → タイトル

## 実装順（リファクタ後）

1. `AppState` / イベント / `screen_handlers` に PROMPT・EXTRA_PLAY
2. `boss_spawn.activate_extra_boss()` + 専用 `boss_extra/` パッケージ
3. `ending_delay` 終了時 `ENDING` へ（現状維持）→ PROMPT 遷移だけ追加
4. DEBUG: `debug_flags.DEBUG_EXTRA_AFTER_ENDING = True` で PROMPT スキップテスト
