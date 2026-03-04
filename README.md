# Why Learn Languages When We Have LLMs LOL

A small, keyboard-driven Chinese (HSK) vocabulary reflex trainer.

Yes, the name is a joke.
No, the logging is not.

## What It Does

- HSK 2.0 Level 1–3 vocabulary (595 words)
- 4-choice and 9-choice quiz modes
- Chinese↔English and Chinese↔Japanese language pairs
- Configurable quiz direction (random / hanzi→meaning / meaning→hanzi)
- Keyboard (1–4 / 1–9) and touch input
- Instant feedback with example sentences
- Millisecond response time logging
- Accuracy-weighted word selection (weak words appear more often)
- Mastery dashboard with per-word and per-level stats
- SQLite storage

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite
- **Frontend**: Vanilla HTML/CSS/JS SPA
- **Target**: Raspberry Pi Zero 2 W

## Vocabulary Data

- [complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) (MIT) — primary word list
- [audio-cmn](https://github.com/hugolpz/audio-cmn) (CC-BY-SA) — native speaker audio (569/595 words)
- Japanese translations + example sentences — LLM-generated (`data/llm_generated.json`)

## Response Logging

- Correct / incorrect
- Response time (ms)
- Timestamps
- Streaks

## Scope

Just reps.

## License

MIT
