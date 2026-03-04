"""FastAPI app: quiz API + static file serving."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import get_db, init_db
from quiz import generate_question

app = FastAPI()

AUDIO_DIR = Path(__file__).parent / "audio-cmn" / "64k" / "hsk"


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/quiz")
def get_quiz(
    mode: int = Query(4, ge=4, le=9),
    levels: str = Query("1,2,3"),
    exclude: str = Query(""),
    lang: str = Query("en"),
    direction: str = Query("random"),
    conn: sqlite3.Connection = Depends(get_db),
):
    level_list = [int(x) for x in levels.split(",") if x.strip()]
    exclude_list = [int(x) for x in exclude.split(",") if x.strip()]
    if lang not in ("en", "ja"):
        lang = "en"
    if direction not in ("random", "hanzi_to_meaning", "meaning_to_hanzi"):
        direction = "random"
    question = generate_question(conn, mode, level_list, exclude_list, lang=lang, direction_mode=direction)
    return question


class AnswerRequest(BaseModel):
    word_id: int
    correct: bool
    response_time_ms: int
    quiz_mode: int
    session_id: str


@app.post("/api/answer")
def post_answer(
    req: AnswerRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    # Record response
    conn.execute(
        """INSERT INTO responses (word_id, correct, response_time_ms, quiz_mode, session_id, answered_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (req.word_id, int(req.correct), req.response_time_ms, req.quiz_mode, req.session_id, datetime.now(timezone.utc).isoformat()),
    )

    # Update streak
    row = conn.execute(
        "SELECT streak, best_streak FROM streaks WHERE session_id = ? AND quiz_mode = ?",
        (req.session_id, req.quiz_mode),
    ).fetchone()

    if row is None:
        streak = 1 if req.correct else 0
        best = streak
        conn.execute(
            "INSERT INTO streaks (session_id, quiz_mode, streak, best_streak) VALUES (?, ?, ?, ?)",
            (req.session_id, req.quiz_mode, streak, best),
        )
    else:
        if req.correct:
            streak = row["streak"] + 1
            best = max(row["best_streak"], streak)
        else:
            streak = 0
            best = row["best_streak"]
        conn.execute(
            "UPDATE streaks SET streak = ?, best_streak = ? WHERE session_id = ? AND quiz_mode = ?",
            (streak, best, req.session_id, req.quiz_mode),
        )

    conn.commit()
    return {"streak": streak, "best_streak": best}


@app.get("/api/stats")
def get_stats(
    levels: str = Query("1,2,3"),
    conn: sqlite3.Connection = Depends(get_db),
):
    level_list = [int(x) for x in levels.split(",") if x.strip()]
    placeholders = ",".join("?" for _ in level_list)

    # Per-word stats
    word_rows = conn.execute(
        f"""SELECT w.id, w.simplified, w.pinyin, w.hsk_level, w.meaning_en,
                   COUNT(r.id) AS attempts, COALESCE(SUM(r.correct), 0) AS correct,
                   CASE WHEN COUNT(r.id) > 0
                        THEN ROUND(CAST(SUM(r.correct) AS REAL) / COUNT(r.id), 3)
                        ELSE NULL END AS accuracy,
                   CASE WHEN COUNT(r.id) > 0
                        THEN CAST(AVG(r.response_time_ms) AS INTEGER)
                        ELSE NULL END AS avg_time_ms
            FROM words w
            LEFT JOIN responses r ON r.word_id = w.id
            WHERE w.hsk_level IN ({placeholders})
            GROUP BY w.id
            ORDER BY w.hsk_level, w.simplified""",
        level_list,
    ).fetchall()

    words = [
        {
            "id": r["id"], "simplified": r["simplified"], "pinyin": r["pinyin"],
            "hsk_level": r["hsk_level"], "meaning_en": r["meaning_en"],
            "attempts": r["attempts"], "correct": r["correct"],
            "accuracy": r["accuracy"], "avg_time_ms": r["avg_time_ms"],
        }
        for r in word_rows
    ]

    # Per-level summary
    level_rows = conn.execute(
        f"""SELECT w.hsk_level AS level,
                   COUNT(DISTINCT w.id) AS total_words,
                   COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN w.id END) AS practiced_words,
                   COUNT(r.id) AS total_attempts,
                   COALESCE(SUM(r.correct), 0) AS total_correct,
                   CASE WHEN COUNT(r.id) > 0
                        THEN ROUND(CAST(SUM(r.correct) AS REAL) / COUNT(r.id), 3)
                        ELSE NULL END AS accuracy,
                   CASE WHEN COUNT(r.id) > 0
                        THEN CAST(AVG(r.response_time_ms) AS INTEGER)
                        ELSE NULL END AS avg_time_ms
            FROM words w
            LEFT JOIN responses r ON r.word_id = w.id
            WHERE w.hsk_level IN ({placeholders})
            GROUP BY w.hsk_level
            ORDER BY w.hsk_level""",
        level_list,
    ).fetchall()

    level_stats = [
        {
            "level": r["level"], "total_words": r["total_words"],
            "practiced_words": r["practiced_words"],
            "total_attempts": r["total_attempts"],
            "total_correct": r["total_correct"],
            "accuracy": r["accuracy"], "avg_time_ms": r["avg_time_ms"],
        }
        for r in level_rows
    ]

    return {"words": words, "levels": level_stats}


# Audio files with cache headers
if AUDIO_DIR.exists():
    from starlette.responses import FileResponse

    @app.get("/audio/{filename:path}")
    def serve_audio(filename: str):
        file_path = AUDIO_DIR / filename
        if not file_path.exists():
            return JSONResponse({"error": "not found"}, status_code=404)
        return FileResponse(
            file_path,
            media_type="audio/mpeg",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )


# Static files (must be last — catches all unmatched routes)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
