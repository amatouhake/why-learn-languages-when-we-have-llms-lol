"""Quiz generation logic: question selection, distractor generation."""

import random
import sqlite3

# POS group mapping for distractor selection
POS_GROUPS = {
    "noun": {"n", "nr", "ns", "nt", "nz", "ng"},
    "verb": {"v", "vn", "vi", "vt", "vd"},
    "adj": {"a", "ad", "an", "ag"},
    "adv": {"d", "dg"},
}


def _pos_group(pos_str: str) -> str:
    """Map a comma-separated POS string to a broad group."""
    tags = {t.strip() for t in pos_str.split(",") if t.strip()}
    for group, members in POS_GROUPS.items():
        if tags & members:
            return group
    return "other"


def _select_weighted_word(
    conn: sqlite3.Connection,
    levels: list[int],
    exclude: list[int],
) -> sqlite3.Row:
    """Select a word using accuracy-based weighting.

    Weight rules:
      - Unseen (0 attempts): 5.0
      - Weak (accuracy < 80%): 3.0 + (1 - accuracy) * 7.0  (range 3.5–10.0)
      - Mastered (accuracy >= 80%): 1.0
    """
    placeholders = ",".join("?" for _ in levels)
    if exclude:
        ex_ph = ",".join("?" for _ in exclude)
        where_exclude = f"AND w.id NOT IN ({ex_ph})"
        params = levels + exclude
    else:
        where_exclude = ""
        params = list(levels)

    rows = conn.execute(
        f"""SELECT w.*, COUNT(r.id) AS attempts, COALESCE(SUM(r.correct), 0) AS correct_count
            FROM words w
            LEFT JOIN responses r ON r.word_id = w.id
            WHERE w.hsk_level IN ({placeholders}) {where_exclude}
            GROUP BY w.id""",
        params,
    ).fetchall()

    if not rows:
        # Fallback: ignore exclude list
        rows = conn.execute(
            f"""SELECT w.*, COUNT(r.id) AS attempts, COALESCE(SUM(r.correct), 0) AS correct_count
                FROM words w
                LEFT JOIN responses r ON r.word_id = w.id
                WHERE w.hsk_level IN ({placeholders})
                GROUP BY w.id""",
            levels,
        ).fetchall()

    weights = []
    for row in rows:
        attempts = row["attempts"]
        if attempts == 0:
            weights.append(5.0)
        else:
            accuracy = row["correct_count"] / attempts
            if accuracy < 0.8:
                weights.append(3.0 + (1.0 - accuracy) * 7.0)
            else:
                weights.append(1.0)

    return random.choices(rows, weights=weights, k=1)[0]


def generate_question(
    conn: sqlite3.Connection,
    mode: int,
    levels: list[int],
    exclude: list[int],
    lang: str = "en",
    direction_mode: str = "random",
) -> dict:
    """Generate a quiz question with distractors.

    Args:
        conn: SQLite connection
        mode: 4 or 9 (number of choices)
        levels: HSK levels to draw from (e.g. [1, 2, 3])
        exclude: word IDs to exclude (recent questions)
        lang: "en" or "ja" — meaning language
        direction_mode: "random", "hanzi_to_meaning", or "meaning_to_hanzi"

    Returns:
        dict with word_id, direction, prompt, prompt_sub, has_audio, options, correct_index, example
    """
    target = _select_weighted_word(conn, levels, exclude)

    # Determine direction
    if direction_mode == "random":
        direction = random.choice(["hanzi_to_meaning", "meaning_to_hanzi"])
    else:
        direction = direction_mode

    # Check if we can use Japanese for this question
    use_ja = lang == "ja" and bool(target["meaning_ja"])

    # Gather distractor pool
    target_group = _pos_group(target["pos"])
    needed = mode - 1

    # Strategy: same level + same POS group first
    distractors = _pick_distractors(
        conn, target, levels, target_group, needed, direction, use_ja
    )

    # Build options
    all_words = [target] + distractors
    random.shuffle(all_words)

    correct_index = -1
    options = []
    for i, w in enumerate(all_words):
        idx = i + 1  # 1-based
        if direction == "hanzi_to_meaning":
            text = w["meaning_ja"] if use_ja and w["meaning_ja"] else w["meaning_en"]
        else:
            text = w["simplified"]
        options.append({"index": idx, "text": text, "word_id": w["id"]})
        if w["id"] == target["id"]:
            correct_index = idx

    # Build prompt
    if direction == "hanzi_to_meaning":
        prompt = target["simplified"]
        prompt_sub = target["pinyin"]
    else:
        text = target["meaning_ja"] if use_ja and target["meaning_ja"] else target["meaning_en"]
        prompt = text
        prompt_sub = None

    result = {
        "word_id": target["id"],
        "direction": direction,
        "prompt": prompt,
        "prompt_sub": prompt_sub,
        "has_audio": bool(target["has_audio"]),
        "options": options,
        "correct_index": correct_index,
    }

    if target["example_zh"]:
        result["example"] = {
            "zh": target["example_zh"],
            "pinyin": target["example_pinyin"],
            "en": target["example_en"],
            "ja": target["example_ja"],
        }

    return result


def _pick_distractors(
    conn: sqlite3.Connection,
    target: sqlite3.Row,
    levels: list[int],
    target_group: str,
    needed: int,
    direction: str,
    use_ja: bool,
) -> list[sqlite3.Row]:
    """Pick distractors avoiding duplicate display text."""
    placeholders = ",".join("?" for _ in levels)

    # Collect what text the target shows so we can exclude duplicates
    if direction == "hanzi_to_meaning":
        target_text = target["meaning_ja"] if use_ja and target["meaning_ja"] else target["meaning_en"]
    else:
        target_text = target["simplified"]

    used_texts = {target_text}
    result = []

    # Pool 1: same level + same POS group
    pool1 = conn.execute(
        f"""SELECT * FROM words
            WHERE hsk_level IN ({placeholders}) AND id != ?
            ORDER BY RANDOM()""",
        levels + [target["id"]],
    ).fetchall()

    # Prefer same POS group first
    same_group = [w for w in pool1 if _pos_group(w["pos"]) == target_group]
    diff_group = [w for w in pool1 if _pos_group(w["pos"]) != target_group]

    for w in same_group + diff_group:
        if len(result) >= needed:
            break
        if direction == "hanzi_to_meaning":
            text = w["meaning_ja"] if use_ja and w["meaning_ja"] else w["meaning_en"]
        else:
            text = w["simplified"]
        if text not in used_texts:
            used_texts.add(text)
            result.append(w)

    # Pool 2: all levels (if still short)
    if len(result) < needed:
        all_ids = [target["id"]] + [w["id"] for w in result]
        id_ph = ",".join("?" for _ in all_ids)
        pool2 = conn.execute(
            f"SELECT * FROM words WHERE id NOT IN ({id_ph}) ORDER BY RANDOM()",
            all_ids,
        ).fetchall()
        for w in pool2:
            if len(result) >= needed:
                break
            if direction == "hanzi_to_meaning":
                text = w["meaning_ja"] if use_ja and w["meaning_ja"] else w["meaning_en"]
            else:
                text = w["simplified"]
            if text not in used_texts:
                used_texts.add(text)
                result.append(w)

    return result
