# API リファレンス

## GET /api/quiz

クイズの問題を1問生成して返す。

### パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|---------|------|
| `mode` | int | `4` | 選択肢数 (4 or 9) |
| `levels` | string | `"1,2,3"` | 出題対象のHSKレベル（カンマ区切り） |
| `exclude` | string | `""` | 除外するword_id（カンマ区切り、直近20問分） |
| `lang` | string | `"en"` | 意味の言語（`"en"` or `"ja"`） |
| `direction` | string | `"random"` | 出題方向（`"random"`, `"hanzi_to_meaning"`, `"meaning_to_hanzi"`） |

### レスポンス

```json
{
  "word_id": 42,
  "direction": "hanzi_to_meaning",
  "prompt": "苹果",
  "prompt_sub": "píng guǒ",
  "has_audio": true,
  "options": [
    {"index": 1, "text": "リンゴ", "word_id": 42},
    {"index": 2, "text": "スイカ", "word_id": 87},
    {"index": 3, "text": "バナナ", "word_id": 55},
    {"index": 4, "text": "ブドウ", "word_id": 63}
  ],
  "correct_index": 1,
  "example": {
    "zh": "我喜欢吃苹果。",
    "pinyin": "Wǒ xǐhuan chī píngguǒ.",
    "en": "I like to eat apples.",
    "ja": "私はリンゴを食べるのが好きです。"
  }
}
```

### direction の値

| direction | prompt | prompt_sub | options |
|-----------|--------|-----------|---------|
| `hanzi_to_meaning` | 漢字 | ピンイン | 意味（lang に応じて英語 or 日本語） |
| `meaning_to_hanzi` | 意味（lang に応じて英語 or 日本語） | null | 漢字 |

- `lang=ja` で日本語訳がない語は英語にフォールバック
- `example` は例文データがある場合のみ含まれる（現在595語すべてに存在）
- `correct_index` をレスポンスに含めるのは個人用アプリのため（サーバー往復なしで即時フィードバック）

## POST /api/answer

回答を記録し、ストリーク情報を返す。

### リクエスト

```json
{
  "word_id": 42,
  "correct": true,
  "response_time_ms": 823,
  "quiz_mode": 4,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### レスポンス

```json
{
  "streak": 7,
  "best_streak": 15
}
```

## GET /api/stats

レベル別・単語別の習熟度統計を返す。

### パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|---------|------|
| `levels` | string | `"1,2,3"` | 対象のHSKレベル（カンマ区切り） |

### レスポンス

```json
{
  "words": [
    {"id": 1, "simplified": "爱", "pinyin": "ài", "hsk_level": 1, "meaning_en": "to love",
     "attempts": 10, "correct": 8, "accuracy": 0.8, "avg_time_ms": 1200}
  ],
  "levels": [
    {"level": 1, "total_words": 150, "practiced_words": 42,
     "total_attempts": 200, "total_correct": 160, "accuracy": 0.8, "avg_time_ms": 1300}
  ]
}
```

## 静的ファイル

| パス | 内容 |
|------|------|
| `/` | SPA (static/index.html) |
| `/style.css?v=N` | CSS（キャッシュバスティング付き） |
| `/app.js?v=N` | JavaScript（キャッシュバスティング付き） |
| `/audio/cmn-{漢字}.mp3` | 音声ファイル（Cache-Control: immutable） |
