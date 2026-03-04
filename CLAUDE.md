# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Keyboard-driven Chinese (HSK) vocabulary reflex trainer. 4-choice and 9-choice quiz modes with millisecond response time logging. Supports Chinese↔English and Chinese↔Japanese quiz directions. Personal use, deployed on a Raspberry Pi Zero 2 W (512MB RAM).

## Common Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python import_data.py                # HSK 1-3 → hsk.db (595 words + Japanese + examples)

# Run (local dev)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1

# Deploy to Pi (code only)
./deploy.sh

# Deploy to Pi (with data re-import, preserves play data)
./deploy.sh --reimport

# Verify data import
python3 -c "
from db import get_connection; conn = get_connection()
for r in conn.execute('SELECT hsk_level, COUNT(*) FROM words GROUP BY hsk_level ORDER BY hsk_level'):
    print(f'HSK {r[0]}: {r[1]}')
ja = conn.execute('SELECT COUNT(*) FROM words WHERE meaning_ja IS NOT NULL').fetchone()[0]
ex = conn.execute('SELECT COUNT(*) FROM words WHERE example_zh IS NOT NULL').fetchone()[0]
print(f'Japanese: {ja}/595, Examples: {ex}/595')
"
# Expected: HSK 1: 150, HSK 2: 147, HSK 3: 298, Japanese: 595/595, Examples: 595/595
```

## Project Structure

```
app.py              # FastAPI app — /api/quiz, /api/answer, /api/stats, static + audio serving
db.py               # SQLite schema (words, responses, streaks), get_db() dependency
quiz.py             # Quiz generation — lang/direction selection, POS-based distractors, example sentences
import_data.py      # Imports HSK vocabulary JSON + LLM-generated data → hsk.db (idempotent, preserves play data)
deploy.sh           # rsync to Pi + optional --reimport + systemctl restart
requirements.txt    # fastapi, uvicorn[standard]
data/
  llm_generated.json  # 595 words: Japanese translations + example sentences (Claude-generated)
static/
  index.html        # SPA — setup (level/lang/direction/advance selection) + quiz + dashboard screens
  style.css         # Dark theme, radio groups, example area, 4-col list / 9-col 3×3 grid
  app.js            # Keyboard/touch handler, state machine, ring buffer, example display, manual/auto advance
  manifest.json     # PWA manifest
  sw.js             # Service Worker — static asset + audio cache
  icon-192.png      # PWA icon 192x192
  icon-512.png      # PWA icon 512x512
```

## Tech Stack

- **Backend**: FastAPI + Uvicorn (single worker, sync sqlite3)
- **Database**: SQLite (WAL mode, no aiosqlite)
- **Frontend**: Vanilla HTML/CSS/JS SPA served via FastAPI StaticFiles

## Architecture

- Single-user app — no auth, no concurrent write concerns
- Quiz state: `LOADING → READY → ANSWERED → WAITING → (user action) → LOADING → ...` (manual mode, default)
- Quiz state: `LOADING → READY → ANSWERED → (timer) → LOADING → ...` (auto/fast/instant mode)
- `correct_index` sent in quiz response (no server roundtrip for feedback — personal app)
- Frontend manages 20-word ring buffer, sends `exclude` param to avoid repeats
- `POST /api/answer` is fire-and-forget from frontend (streak synced on response)
- Audio served at `/audio/cmn-{simplified}.mp3` with `Cache-Control: immutable`
- Example sentences shown after answering; in manual mode, visible until user advances
- PWA: Service Worker caches static assets (cache-first) and audio (lazy cache-first); API is network-only
- Static assets use `?v=N` cache-busting for mobile browser compatibility

## API Endpoints

- `GET /api/quiz?mode=4&levels=1,2,3&exclude=1,2,3&lang=en&direction=random` — returns question with options, correct_index, and example sentence
- `POST /api/answer` — `{word_id, correct, response_time_ms, quiz_mode, session_id}` → `{streak, best_streak}`
- `GET /api/stats?levels=1,2,3` — per-word and per-level accuracy/speed statistics

## Vocabulary Data

- **Primary**: `complete-hsk-vocabulary/` (MIT / JSON) — HSK 2.0 Levels 1–3 (595 words)
- **Audio**: `audio-cmn/` (CC-BY-SA / MP3) — 569/595 words have audio
- **Japanese translations + examples**: `data/llm_generated.json` (Claude-generated) — 595/595 words with meaning_ja, example_zh, example_pinyin, example_en, example_ja

## Quiz Logic (quiz.py)

- **Language**: `lang` param — `en` (Chinese↔English) or `ja` (Chinese↔Japanese), with fallback to English if Japanese translation is missing
- **Directions**: `direction_mode` param — `random` (default), `hanzi_to_meaning`, or `meaning_to_hanzi`
- **Distractor selection**: same HSK level + same POS group → same level any POS → all levels (fallback)
- **POS groups**: noun (n,nr,ns,nt,nz,ng), verb (v,vn,vi,vt,vd), adj (a,ad,an,ag), adv (d,dg), other
- **Dedup**: display text uniqueness enforced within each question's options
- **Examples**: example sentence (zh/pinyin/en/ja) included in response when available

## Target Environment Constraints

- Raspberry Pi Zero 2 W: quad-core ARM Cortex-A53 1GHz, 512MB RAM
- Keep dependencies minimal — avoid heavy libraries (pandas, numpy) at runtime
- Use `--workers 1` for Uvicorn
- Data analysis, if needed later, should run on a separate machine or use raw SQL aggregation
- HTTP-only (no HTTPS) — use `crypto.getRandomValues` fallback instead of `crypto.randomUUID()`

## DB Schema (db.py)

- **words**: id, simplified (UNIQUE), traditional, pinyin, pinyin_num, hsk_level, pos, meaning_en, meanings_en (JSON), meaning_ja, has_audio, example_zh, example_pinyin, example_en, example_ja
- **responses**: id, word_id (FK), correct, response_time_ms, quiz_mode, session_id, answered_at (ISO)
- **streaks**: session_id + quiz_mode (UNIQUE), streak, best_streak
