"""Build the question bank: backend/data/questions.json.gz.

    python backend/scripts/question_bank/build.py

Each category gets the number of questions in common.TARGETS. OpenTriviaQA's questions go
in first (best first); questions generated from Wikidata, and Mathematics' number trivia, fill
the rest, one question per item before any item gets a second. Every question passes the
same checks (valid), and difficulty comes from how well known the item is.

Downloads are cached in backend/data/sources/ (not committed), so rebuilding is quick and
gives the same bank. Delete that folder to fetch everything fresh.
"""

import gzip
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generators  # noqa: E402
import generators2  # noqa: E402
import mathematics  # noqa: E402
import otqa  # noqa: E402
from common import CATEGORY_NAMES, DATA, TARGETS, new_rng  # noqa: E402

OUT = DATA / "questions.json.gz"

# Where each category's generated questions come from
GENERATED = {
    10: [generators.books], 15: [generators.video_games], 23: [generators.history], 22: [generators.geography],
    31: [generators.anime_manga], 20: [generators.mythology], 25: [generators.art],
    32: [generators2.cartoons], 29: [generators2.comics], 28: [generators2.vehicles], 16: [generators2.board_games],
    13: [generators2.musicals], 30: [generators2.gadgets], 19: [generators2.mathematicians, mathematics.generate],
}
try:  # animals, politics and computers (generators3), once their data is in
    import generators3  # noqa: E402

    GENERATED.update(generators3.GENERATORS3)
except ImportError:
    pass

# Words too common to count as giving an answer away ("Studio", "Comics"…)
COMMON_WORDS = {"the", "and", "company", "games", "game", "comics", "studio", "studios", "entertainment", "productions",
                "publishing", "press", "group", "river", "city", "national", "museum", "gallery", "party", "republic",
                "kingdom", "united", "states", "island", "islands", "saint", "new", "great", "south", "north", "east",
                "west", "royal", "art", "film", "films", "television", "animation", "motor", "motors", "software",
                "systems", "music", "records", "international", "world", "century", "mythology"}


def plain(text):
    return html.unescape(text).casefold()


def valid(q):
    """Why a question can't go in the bank, or None if it's fine."""
    question, answer = plain(q["question"]), plain(q["correct_answer"])
    wrong = [plain(w) for w in q["incorrect_answers"]]
    if q["type"] == "multiple" and (len(wrong) != 3 or len(set(wrong)) != 3 or answer in wrong or not all(wrong)):
        return "options"
    if not answer or len(question) > 300 or len(answer) > 100:
        return "length"
    if q["type"] == "multiple" and not answer.isdigit():
        if len(answer) >= 3 and answer in question:
            return "answer in the question"
        words = [w for w in re.split(r"\W+", answer) if len(w) >= 4 and w not in COMMON_WORDS]
        if any(re.search(rf"\b{re.escape(w)}\b", question) for w in words):
            return "part of the answer in the question"
    return None


def set_difficulty(questions):
    """Generated questions about better-known things are easier: thirds by fame."""
    ranked = sorted((q for q in questions if not q["difficulty"] and q["source"] != "opentriviaqa"),
                    key=lambda q: q["_fame"], reverse=True)
    third = max(1, len(ranked) // 3)
    for i, q in enumerate(ranked):
        q["difficulty"] = "easy" if i < third else "medium" if i < 2 * third else "hard"


def spread(candidates, needed, rng):
    """`needed` questions, at most one per item until every item has had one, then two…"""
    by_item = defaultdict(list)
    for q in candidates:
        by_item[q["_item"]].append(q)
    items = list(by_item)
    rng.shuffle(items)
    for questions in by_item.values():
        rng.shuffle(questions)
    chosen, round_ = [], 0
    while len(chosen) < needed and any(len(qs) > round_ for qs in by_item.values()):
        for item in items:
            if round_ < len(by_item[item]):
                chosen.append(by_item[item][round_])
                if len(chosen) == needed:
                    break
        round_ += 1
    return chosen


def main():
    seen, rejected = set(), Counter()

    def fresh(q):
        key = re.sub(r"[^a-z0-9]", "", plain(q["question"])) + "|" + plain(q["correct_answer"])
        reason = valid(q) or ("duplicate" if key in seen else None)
        if reason:
            rejected[reason] += 1
            return False
        seen.add(key)
        return True

    from_otqa, otqa_rejected = otqa.load()
    by_category = defaultdict(list)
    for category_id, score, q in sorted(from_otqa, key=lambda t: -t[1]):
        by_category[category_id].append(q)

    bank, report = [], []
    for category_id, target in TARGETS.items():
        rng = new_rng(f"build-{category_id}")
        mine = [q for q in by_category.get(category_id, []) if fresh(q)][:target]
        for q in mine:
            q["_item"], q["_fame"] = q["question"], 0
        if len(mine) < target:
            generated = [q for make in GENERATED.get(category_id, []) for q in make() if q]
            set_difficulty(generated)
            usable = [q for q in generated if fresh(q)]
            mine += spread(usable, target - len(mine), rng)
        report.append((CATEGORY_NAMES[category_id], len(mine), target, Counter(q["source"] for q in mine)))
        bank += mine

    for q in bank:
        q.pop("_item", None)
        q.pop("_fame", None)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(gzip.compress(json.dumps(bank, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))

    print(f"{len(bank)} questions in {OUT.relative_to(DATA.parent.parent)} ({OUT.stat().st_size // 1024} KB)\n")
    for name, count, target, sources in report:
        mark = "" if count >= target else f"   SHORT by {target - count}"
        print(f"  {name:42} {count:5} / {target}  {dict(sources)}{mark}")
    print("\nleft out:", dict(rejected), "| OpenTriviaQA filter:", otqa_rejected)


if __name__ == "__main__":
    # Python shuffles the order of sets differently on every run; fixing it makes rebuilding
    # give exactly the same bank
    if os.environ.get("PYTHONHASHSEED") != "0":
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONHASHSEED": "0"}))
    main()
