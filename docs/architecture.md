# アーキテクチャ

## システム構成

```
ブラウザ (SPA)
  │
  ├─ GET /api/quiz      → quiz.py → SQLite (words)
  ├─ POST /api/answer   → app.py  → SQLite (responses, streaks)
  ├─ GET /audio/cmn-*.mp3         → audio-cmn/64k/hsk/
  └─ GET /                        → static/
```

シングルユーザー・シングルワーカー。認証なし。

## データフロー

### インポート (import_data.py)

```
0. responses + streaks をバックアップ（既存DBがあれば）
1. DB削除 → スキーマ再作成

Pass 1: complete-hsk-vocabulary/wordlists/exclusive/old/{1,2,3}.json
  → forms[0] のみ使用
  → meaning_en = meanings[0][:50]
  → has_audio = audio-cmn/64k/hsk/cmn-{simplified}.mp3 の存在チェック
  → INSERT INTO words

Pass 2: data/llm_generated.json (存在する場合のみ)
  → simplified でマッチ
  → UPDATE words SET meaning_ja, example_zh, example_pinyin, example_en, example_ja

3. responses + streaks をリストア
```

### クイズ生成 (quiz.py)

```
1. levels + exclude で対象プールを絞り込み（正答率ベースの重み付き選出）
2. direction_mode に応じて方向決定 (random / hanzi_to_meaning / meaning_to_hanzi)
3. lang に応じて表示言語決定 (en / ja、日本語訳がない場合は英語にフォールバック)
4. ディストラクター選択:
   a. 同レベル＋同品詞グループ (優先)
   b. 同レベル全品詞 (不足時)
   c. 全レベル (フォールバック)
5. 表示テキストの重複を排除
6. シャッフルして index 付与
7. 例文データがあれば example フィールドを追加
```

### フロントエンド状態遷移 (app.js)

```
SETUP → [モードボタン押下] → LOADING → [fetch完了] → READY → [キー/タッチ入力] → ANSWERED → [600ms/2500ms] → LOADING → ...
                                                                                                                  ↑
                                                                    ←←←←←←←← [戻るボタン] ←←←←←← SETUP ←←←←←←←←←
```

- SETUP画面で言語ペア（中↔英 / 中↔日）と出題方向（ランダム / 漢字→意味 / 意味→漢字）を選択
- READY 状態のみキー入力受付（二重回答防止）
- ANSWERED で例文表示（例文ありなら 2.5s、なしなら 0.6s の遅延）
- セッションID: `crypto.randomUUID()` → 非セキュアコンテキストでは `crypto.getRandomValues` フォールバック
- 直近20問: フロントエンドのリングバッファで管理

## DB スキーマ

### words
主キー: `id` (INTEGER), ユニーク: `simplified`

語彙データ。`meaning_ja` は日本語訳（LLM生成、595語すべてに値あり）。
`meanings_en` は全意味のJSON配列、`meaning_en` は表示用の最初の1つ（50文字以内）。
`example_zh`, `example_pinyin`, `example_en`, `example_ja` は例文データ（LLM生成、595語すべてに値あり）。

### responses
回答ログ。`response_time_ms` でミリ秒精度の反応速度を記録。
`session_id` はブラウザセッション単位のUUID。

### streaks
`(session_id, quiz_mode)` でUPSERT。
フロントエンドでもローカルに管理し、サーバーレスポンスの `best_streak` で同期。

## 設計判断

| 判断 | 理由 |
|------|------|
| sync sqlite3 (not aiosqlite) | シングルユーザー・シングルワーカーで非同期の利点なし |
| correct_index をレスポンスに含める | 個人用。サーバー往復を省略して即時フィードバック |
| POST /api/answer は fire-and-forget | UI応答性を優先。ストリークは非同期で同期 |
| POS ベースのディストラクター | 同品詞グループから選ぶことで難易度を適正化 |
| WAL モード | 読み写きの並行性確保（将来の分析クエリ対策） |
| リングバッファ (20問) | フロントエンド管理。サーバー側はステートレス |
| lang=ja フォールバック | meaning_ja が NULL の場合は meaning_en を使用 |
| crypto.getRandomValues フォールバック | HTTP環境（Pi LAN）で crypto.randomUUID() が使えないため |
| 静的ファイルの ?v=N | モバイルブラウザのキャッシュ問題への対策 |
