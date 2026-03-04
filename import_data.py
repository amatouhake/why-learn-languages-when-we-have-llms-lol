"""Import HSK 1-3 vocabulary from complete-hsk-vocabulary into SQLite."""

import json
from pathlib import Path

from db import DB_PATH, get_connection, SCHEMA

DATA_DIR = Path(__file__).parent / "complete-hsk-vocabulary" / "wordlists" / "exclusive" / "old"
AUDIO_DIR = Path(__file__).parent / "audio-cmn" / "64k" / "hsk"
LLM_DATA = Path(__file__).parent / "data" / "llm_generated.json"


def load_level(level: int) -> list[dict]:
    path = DATA_DIR / f"{level}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def has_audio(simplified: str) -> bool:
    return (AUDIO_DIR / f"cmn-{simplified}.mp3").exists()


def _backup_progress(conn):
    """Back up responses and streaks before DB reset."""
    responses = []
    streaks = []
    try:
        responses = conn.execute("SELECT * FROM responses").fetchall()
        streaks = conn.execute("SELECT * FROM streaks").fetchall()
    except Exception:
        pass
    return responses, streaks


def _restore_progress(conn, responses, streaks):
    """Restore responses and streaks after DB reset."""
    if not responses and not streaks:
        return
    for r in responses:
        conn.execute(
            """INSERT OR IGNORE INTO responses (id, word_id, correct, response_time_ms, quiz_mode, session_id, answered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (r["id"], r["word_id"], r["correct"], r["response_time_ms"], r["quiz_mode"], r["session_id"], r["answered_at"]),
        )
    for s in streaks:
        conn.execute(
            "INSERT OR IGNORE INTO streaks (session_id, quiz_mode, streak, best_streak) VALUES (?, ?, ?, ?)",
            (s["session_id"], s["quiz_mode"], s["streak"], s["best_streak"]),
        )
    conn.commit()
    print(f"Progress restored: {len(responses)} responses, {len(streaks)} streaks")


def import_all():
    # Back up play data before reset
    progress = ([], [])
    if DB_PATH.exists():
        try:
            conn = get_connection()
            progress = _backup_progress(conn)
            conn.close()
        except Exception:
            pass
        DB_PATH.unlink()

    conn = get_connection()
    conn.executescript(SCHEMA)

    rows = []
    for level in (1, 2, 3):
        entries = load_level(level)
        for entry in entries:
            form = entry["forms"][0]
            meanings = form["meanings"]
            meaning_en = meanings[0][:50] if meanings else ""
            rows.append((
                entry["simplified"],
                form.get("traditional", entry["simplified"]),
                form["transcriptions"]["pinyin"],
                form["transcriptions"]["numeric"],
                level,
                ",".join(entry.get("pos", [])),
                meaning_en,
                json.dumps(meanings, ensure_ascii=False),
                has_audio(entry["simplified"]),
            ))

    conn.executemany(
        """INSERT OR IGNORE INTO words
           (simplified, traditional, pinyin, pinyin_num, hsk_level, pos, meaning_en, meanings_en, has_audio)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()

    # Merge LLM-generated data (Japanese translations + example sentences)
    if LLM_DATA.exists():
        with open(LLM_DATA, encoding="utf-8") as f:
            llm_entries = json.load(f)
        updated = 0
        for entry in llm_entries:
            cur = conn.execute(
                """UPDATE words SET meaning_ja=?, example_zh=?, example_pinyin=?, example_en=?, example_ja=?
                   WHERE simplified=?""",
                (
                    entry.get("meaning_ja"),
                    entry.get("example_zh"),
                    entry.get("example_pinyin"),
                    entry.get("example_en"),
                    entry.get("example_ja"),
                    entry["simplified"],
                ),
            )
            updated += cur.rowcount
        conn.commit()
        print(f"LLM data merged: {updated}/{len(llm_entries)} words updated")
    else:
        print(f"LLM data not found at {LLM_DATA}, skipping")

    # Print summary
    cursor = conn.execute("SELECT hsk_level, COUNT(*) FROM words GROUP BY hsk_level ORDER BY hsk_level")
    total = 0
    for row in cursor:
        print(f"HSK {row[0]}: {row[1]} words")
        total += row[1]
    print(f"Total: {total} words")

    audio_count = conn.execute("SELECT COUNT(*) FROM words WHERE has_audio = 1").fetchone()[0]
    print(f"With audio: {audio_count}")

    # Restore play data
    _restore_progress(conn, *progress)

    conn.close()


if __name__ == "__main__":
    import_all()
