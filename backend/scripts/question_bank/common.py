"""What every question source shares: the app's categories, one question shape, and the
helpers that make generated questions read well (similar wrong answers, years, difficulty)."""

import html
import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
ENTRIES_DIR = DATA / "sources"

# Open Trivia DB's category names and ids, which the app's categories use
CATEGORY_NAMES = {
    9: "General Knowledge", 10: "Entertainment: Books", 11: "Entertainment: Film", 12: "Entertainment: Music",
    13: "Entertainment: Musicals & Theatres", 14: "Entertainment: Television", 15: "Entertainment: Video Games",
    16: "Entertainment: Board Games", 17: "Science & Nature", 18: "Science: Computers", 19: "Science: Mathematics",
    20: "Mythology", 21: "Sports", 22: "Geography", 23: "History", 24: "Politics", 25: "Art", 26: "Celebrities",
    27: "Animals", 28: "Vehicles", 29: "Entertainment: Comics", 30: "Science: Gadgets",
    31: "Entertainment: Japanese Anime & Manga", 32: "Entertainment: Cartoon & Animations",
}

# How many questions each category gets, from how popular it's likely to be
# (tiers 1 and 2: 2,000; tier 3: 1,200; tier 4: 800)
TARGETS = {
    9: 2000, 11: 2000, 14: 2000, 12: 2000, 23: 2000, 22: 2000, 17: 2000,  # tier 1
    15: 2000, 21: 2000, 10: 2000, 27: 2000, 18: 2000, 31: 2000,  # tier 2
    20: 1200, 25: 1200, 24: 1200, 19: 1200, 32: 1200, 29: 1200, 26: 1200, 28: 1200,  # tier 3
    16: 800, 13: 800, 30: 800,  # tier 4
}


def make_question(category_id, question, correct, wrong, difficulty="", source="wikidata", kind="multiple"):
    """One question in the bank's shape: Open Trivia DB's fields (text HTML-escaped like theirs)
    plus the category id and where it came from. kind="boolean" makes a true/false question
    whose answer is `correct` ("True" or "False")."""
    if kind == "boolean":
        wrong = ["False" if correct == "True" else "True"]
    return {
        "type": kind,
        "difficulty": difficulty,
        "category": CATEGORY_NAMES[category_id],
        "category_id": category_id,
        "question": html.escape(question),
        "correct_answer": html.escape(str(correct)),
        "incorrect_answers": [html.escape(str(w)) for w in wrong],
        "source": source,
    }


def similar(correct, pool, rng, k=3, closeness=None):
    """k wrong answers from `pool`: different from the right one (ignoring case), never repeated,
    and, when `closeness` is given, drawn from the closest few so they're plausible."""
    seen = {str(correct).casefold()}
    candidates = []
    for value in pool:
        key = str(value).casefold()
        if key not in seen:
            seen.add(key)
            candidates.append(value)
    if len(candidates) < k:
        return None
    rng.shuffle(candidates)
    if closeness:
        candidates.sort(key=closeness)
        near = candidates[: max(k * 4, 12)]  # the closest dozen or so, picked at random among them
        return rng.sample(near, k)
    return candidates[:k]


def year_options(year, rng, spread=(1, 2, 3, 4, 5, 6, 8, 10)):
    """Three wrong years near the right one (none in the future)."""
    picks = set()
    while len(picks) < 3:
        guess = year + rng.choice([-1, 1]) * rng.choice(spread)
        if guess != year and guess <= 2026:
            picks.add(guess)
    return sorted(picks)


def decade_options(year, rng):
    decade = year - year % 10
    others = [decade + step for step in (-30, -20, -10, 10, 20) if decade + step <= 2020]
    return f"{decade}s", [f"{d}s" for d in rng.sample(others, 3)]


def difficulty_by_fame(items, links_of):
    """Easy for the best-known third, medium for the next, hard for the rest."""
    ranked = sorted(items, key=links_of, reverse=True)
    third = max(1, len(ranked) // 3)
    return {id(item): ("easy" if i < third else "medium" if i < 2 * third else "hard") for i, item in enumerate(ranked)}


def pick(rng, *phrasings):
    """One of several ways of saying the same thing, so a run of questions doesn't read alike."""
    return rng.choice(phrasings)


def new_rng(name):
    """A random source fixed per category, so rebuilding gives the same bank."""
    return random.Random(f"quizzr-bank-{name}")
