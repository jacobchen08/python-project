"""OpenTriviaQA (https://github.com/uberspot/OpenTriviaQA, CC BY-SA 4.0): about 50,000
multiple-choice questions gathered by hand. Rougher than the rest, so they're filtered hard
(rejection_reason), lightly repaired (fix_text) and ranked (quality) before any is used.
"""

import re
import urllib.request

from common import ENTRIES_DIR, make_question

URL = "https://raw.githubusercontent.com/uberspot/OpenTriviaQA/master/categories/{}"
CACHE = ENTRIES_DIR / "opentriviaqa"

# Each file, and the app category it fits (Open Trivia DB's ids). The files that mix every
# topic go to General Knowledge.
FILES = {
    "animals": 27, "celebrities": 26, "geography": 22, "history": 23, "literature": 10, "movies": 11,
    "music": 12, "science-technology": 17, "sports": 21, "television": 14, "video-games": 15,
    "brain-teasers": 9, "entertainment": 9, "for-kids": 9, "general": 9, "hobbies": 9, "humanities": 9,
    "newest": 9, "people": 9, "rated": 9, "religion-faith": 9, "world": 9,
}

# Apostrophes the source lost, in words where putting them back can't be wrong
CONTRACTIONS = {
    w: w[:-1] + "'" + w[-1]
    for w in ["dont", "doesnt", "didnt", "isnt", "wasnt", "arent", "werent", "cant", "couldnt", "wouldnt",
              "shouldnt", "hasnt", "havent", "hadnt", "aint"]
} | {"thats": "that's", "whats": "what's", "theres": "there's", "youre": "you're", "theyre": "they're"}
CONTRACTION_RE = re.compile(r"\b(" + "|".join(CONTRACTIONS) + r")\b", re.IGNORECASE)
ORDER_BOUND = re.compile(r"\b(all|none|both|neither) of (these|the above|them)\b|\babove\b|\bbelow\b", re.IGNORECASE)
NEEDS_A_PICTURE = re.compile(r"\b(pictured|this picture|this image|shown here|shown above)\b", re.IGNORECASE)
# Signs of text that lost punctuation: a possessive with no apostrophe ("Hestons son"), a gap
# where "&" or a quote went missing ("Willy Wonka  the Chocolate Factory" is fixed to one space)
LOST_PUNCTUATION = re.compile(r"\b[A-Z][a-z]+s (son|daughter|wife|husband|father|mother|brother|sister|first|last|best|famous|real|name|career|debut|album|song|novel|film|movie|show)\b")


def fix_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)  # "Government ," -> "Government,"

    def restore(match):
        word = match.group(0)
        fixed = CONTRACTIONS[word.lower()]
        return fixed[0].upper() + fixed[1:] if word[0].isupper() else fixed

    return CONTRACTION_RE.sub(restore, text)


def read_lines(path):
    """The files mix encodings: most lines are UTF-8, a few are Windows-1252."""
    lines = []
    for raw in path.read_bytes().split(b"\n"):
        try:
            lines.append(raw.decode("utf-8"))
        except UnicodeDecodeError:
            lines.append(raw.decode("cp1252", errors="replace"))
    return lines


def parse(lines):
    """#Q question / ^ correct answer / A..E options, blocks separated by blank lines."""
    entries, current = [], None
    for line in lines:
        line = line.rstrip("\r")
        if line.startswith("#Q"):
            current = {"question": line[2:].strip(), "correct": None, "options": []}
            entries.append(current)
        elif current is None or not line.strip():
            continue
        elif line.startswith("^"):
            current["correct"] = line[1:].strip()
        elif re.match(r"^[A-F] ", line):
            current["options"].append(line[2:].strip())
        elif current["correct"] is None:
            current["question"] += " " + line.strip()  # a question that runs over two lines
    return entries


def rejection_reason(entry):
    """Why a question can't be used, or None if it's fine."""
    question, correct, options = entry["question"], entry["correct"], entry["options"]
    everything = " ".join([question, correct or "", *options])
    if not question or not correct:
        return "no question or no answer"
    if "�" in everything:
        return "broken characters"
    if correct not in options:
        return "the answer isn't one of the options"
    if len(set(options)) != len(options) or not 2 <= len(options) <= 5:
        return "odd set of options"
    lowered = {o.lower() for o in options}
    if lowered == {"yes", "no"}:
        return "yes/no question"
    if len(options) == 2 and lowered != {"true", "false"}:
        return "only two options"
    if any(ORDER_BOUND.search(o) for o in options) or NEEDS_A_PICTURE.search(question):
        return "depends on the option order or a picture"
    if len(question) > 300 or any(len(o) > 100 for o in options):
        return "too long to read on a board"
    return None


def quality(entry):
    """Higher is better: used to keep the best when a category has more than it needs."""
    text = fix_text(entry["question"])
    score = 0
    if LOST_PUNCTUATION.search(text):
        score -= 3
    if 40 <= len(text) <= 160:
        score += 2
    if len(entry["options"]) >= 4:
        score += 1
    if text.endswith("?"):
        score += 1
    if any(c.islower() for c in entry["correct"][:1]):
        score -= 1  # answers starting lowercase are usually sloppy entries
    return score


def load():
    """Every usable question, as (category_id, quality, question) tuples."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out, rejected = [], {}
    for name, category_id in FILES.items():
        path = CACHE / name
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(URL.format(name), timeout=60).read())
        for entry in parse(read_lines(path)):
            reason = rejection_reason(entry)
            if reason:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            correct = fix_text(entry["correct"])
            options = [fix_text(o) for o in entry["options"]]
            if {o.lower() for o in options} == {"true", "false"}:
                question = make_question(category_id, fix_text(entry["question"]), correct.capitalize(), None,
                                         source="opentriviaqa", kind="boolean")
            else:
                wrong = [o for o in options if o != correct][:3]  # four options, like everywhere else
                question = make_question(category_id, fix_text(entry["question"]), correct, wrong, source="opentriviaqa")
            out.append((category_id, quality(entry), question))
    return out, rejected
