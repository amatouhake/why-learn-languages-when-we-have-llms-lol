import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hsk.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY,
    simplified TEXT UNIQUE NOT NULL,
    traditional TEXT,
    pinyin TEXT,
    pinyin_num TEXT,
    hsk_level INTEGER NOT NULL,
    pos TEXT,
    meaning_en TEXT NOT NULL,
    meanings_en TEXT NOT NULL,
    meaning_ja TEXT,
    has_audio INTEGER NOT NULL DEFAULT 0,
    example_zh TEXT,
    example_pinyin TEXT,
    example_en TEXT,
    example_ja TEXT
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY,
    word_id INTEGER NOT NULL REFERENCES words(id),
    correct INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    quiz_mode INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    answered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS streaks (
    session_id TEXT NOT NULL,
    quiz_mode INTEGER NOT NULL,
    streak INTEGER NOT NULL DEFAULT 0,
    best_streak INTEGER NOT NULL DEFAULT 0,
    UNIQUE(session_id, quiz_mode)
);

CREATE INDEX IF NOT EXISTS idx_words_level ON words(hsk_level);
CREATE INDEX IF NOT EXISTS idx_responses_word ON responses(word_id);
CREATE INDEX IF NOT EXISTS idx_responses_session ON responses(session_id);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
