"""The question bank: 38,000 trivia questions kept with the server, in
backend/data/questions.json.gz (built by backend/scripts/question_bank/build.py).

Drawing from it needs no network and has no rate limit, so quizzes start at once, any number
of categories can share a round, and nothing depends on Open Trivia DB being up. Each
question is in Open Trivia DB's own shape, plus a category_id and a source: "opentriviaqa",
"wikidata" (generated from Wikidata's facts) or "generated" (worked-out number trivia).

How many questions each category holds follows how popular it's likely to be, so drawing
from "any category" naturally favours the popular ones.
"""

import gzip
import json
import os
import random
import threading
from pathlib import Path

# QUESTION_BANK points the server at another bank file, e.g. a trial build
BANK_PATH = Path(os.environ.get("QUESTION_BANK") or Path(__file__).resolve().parent / "data" / "questions.json.gz")
FIELDS = ("type", "difficulty", "category", "question", "correct_answer", "incorrect_answers")

_questions = None
_lock = threading.Lock()


class NotEnoughQuestions(Exception):
    pass


def available():
    return BANK_PATH.exists()


def questions():
    """Every question in the bank, read from disk the first time it's needed."""
    global _questions
    with _lock:
        if _questions is None:
            _questions = json.loads(gzip.decompress(BANK_PATH.read_bytes()).decode("utf-8"))
        return _questions


def draw(amount, categories=(), difficulty=None, question_type=None, partial=False):
    """`amount` random questions matching the settings. With several categories chosen, the
    round is shared evenly between them (a category that runs short is made up by the rest).
    With partial=True, a bank that runs short returns what it has instead of raising.
    Each question is marked "source": "bank"."""
    def matching(category_id=None):
        return [q for q in questions()
                if (category_id is None or q["category_id"] == category_id)
                and (difficulty is None or q["difficulty"] == difficulty)
                and (question_type is None or q["type"] == question_type)]

    if not categories:
        pool = matching()
        if len(pool) < amount and not partial:
            raise NotEnoughQuestions(len(pool))
        picked = random.sample(pool, min(amount, len(pool)))
    else:
        pools = {c: matching(int(c)) for c in categories}
        order = list(categories)
        random.shuffle(order)
        shares = {c: amount // len(order) for c in order}
        for c in order[: amount % len(order)]:
            shares[c] += 1
        picked, owed = [], 0
        for c in sorted(order, key=lambda c: len(pools[c])):  # smallest first, so others can make up for it
            take = min(shares[c] + owed, len(pools[c]))
            owed = shares[c] + owed - take
            picked += random.sample(pools[c], take)
        if owed and not partial:
            raise NotEnoughQuestions(amount - owed)
        random.shuffle(picked)
    return [{**{field: q[field] for field in FIELDS}, "source": "bank"} for q in picked]
