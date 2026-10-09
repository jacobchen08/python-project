import html
import os
import random
import threading
import time

import requests

import question_bank

# Settings are passed in with each request (instead of stored in global variables)
# so that different players on the same server don't overwrite each other's choices.

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_TYPES = {"multiple", "boolean"}


class TriviaError(Exception):
    pass


class NotEnoughQuestions(TriviaError):
    """Open Trivia DB has too few questions for these settings (or none left unseen)."""


# Open Trivia DB allows one request per IP every 5 seconds. When two quizzes start close
# together, waiting it out once is friendlier than failing.
RATE_LIMIT_WAIT = 5.5
RATE_LIMIT_RETRIES = 1

TOKEN_URL = "https://opentdb.com/api_token.php"
TOKEN_RETRY_AFTER = 60  # seconds to wait before asking again if getting a token failed


class SessionToken:
    """Open Trivia DB's session token: while it's in use, no question comes back twice.

    One token is shared by the whole server, so players see fresh questions across rounds
    rather than the same popular ones again. When a token has handed out every question for
    some settings (response code 4) it's reset; when it has expired after 6 idle hours
    (code 3) a new one is requested. If the token service is down, quizzes still work,
    just without the no-repeats guarantee.
    """

    def __init__(self):
        self.value = None
        self.failed_at = None
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            if self.value is None and (self.failed_at is None or time.time() - self.failed_at > TOKEN_RETRY_AFTER):
                self.value = self._request()
                self.failed_at = None if self.value else time.time()
            return self.value

    def forget(self):
        with self.lock:
            self.value = None
            self.failed_at = None

    def reset(self):
        with self.lock:
            token = self.value
        if not token:
            return
        try:
            requests.get(TOKEN_URL, params={"command": "reset", "token": token}, timeout=10)
        except requests.RequestException:
            self.forget()  # can't reset it, so start over with a new one

    @staticmethod
    def _request():
        try:
            data = requests.get(TOKEN_URL, params={"command": "request"}, timeout=10).json()
        except (requests.RequestException, ValueError):
            return None
        return data.get("token") if data.get("response_code") == 0 else None


session_token = SessionToken()

# A round over several categories needs one Open Trivia DB request per category, 5 seconds
# apart, so each round draws from at most this many of the chosen categories (about 15 extra
# seconds at worst). Different rounds pick different ones, so every choice comes up.
MAX_CATEGORIES_PER_ROUND = 4


def parse_categories(category):
    """'all', '22', '22,23' or a list, as a list of valid category ids (strings, no repeats)."""
    parts = category if isinstance(category, (list, tuple)) else str(category or "").split(",")
    chosen = []
    for part in parts:
        part = str(part).strip()
        # Open Trivia DB's category ids run from 9 to 32
        if part.isdigit() and 9 <= int(part) <= 32 and part not in chosen:
            chosen.append(part)
    return chosen


def fetch_mixed(amount, chosen, difficulty, question_type):
    """A round from Open Trivia DB spread evenly over several categories, in a random order."""
    picked = random.sample(chosen, min(len(chosen), amount, MAX_CATEGORIES_PER_ROUND))
    shares = {c: amount // len(picked) for c in picked}
    for c in random.sample(picked, amount % len(picked)):
        shares[c] += 1

    questions, owed = [], 0
    for i, category in enumerate(picked):
        if i:
            time.sleep(RATE_LIMIT_WAIT)  # Open Trivia DB allows one request every 5 seconds
        wanted = shares[category] + owed
        try:
            questions += fetch_from_opentdb(wanted, category, difficulty, question_type)
            owed = 0
        except NotEnoughQuestions:
            owed = wanted  # this category ran short: the next one makes up the difference
    if owed:
        raise NotEnoughQuestions("Not enough questions for those settings. Try fewer questions or more categories.")
    random.shuffle(questions)
    return questions


def fetch_questions(amount=10, category="all", difficulty="all", question_type="all", source=None):
    """Questions in Open Trivia DB's shape, each marked with its "source": "bank" or "opentdb".

    The bank (question_bank.py) is the default: instant, no rate limit, any number of
    categories. When it has too few questions for the settings (say, easy questions in a
    category whose bank is mostly hard), Open Trivia DB's live API makes up the rest and the
    two are shuffled together. Nothing from Open Trivia DB is stored. It supplies the whole
    round when asked for (source="opentdb", or QUESTION_SOURCE=opentdb) or when the bank
    file is missing.
    """
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = 10
    # Open Trivia DB hands out at most 50 questions at a time, and the app asks for no more
    amount = max(1, min(amount, 50))
    chosen = parse_categories(category)

    # End-to-end tests run without the internet and need answers they can predict
    if os.environ.get("QUIZZR_OFFLINE_TRIVIA") == "1":
        return offline_questions(amount, chosen)

    source = source or os.environ.get("QUESTION_SOURCE", "bank")
    from_bank = []
    if source == "bank" and question_bank.available():
        from_bank = question_bank.draw(
            amount,
            chosen,
            difficulty if difficulty in VALID_DIFFICULTIES else None,
            question_type if question_type in VALID_TYPES else None,
            partial=True,
        )
        if len(from_bank) == amount:
            return from_bank

    # The bank only runs short once every chosen category is used up, so Open Trivia DB
    # is asked for the rest across all of them
    wanted = amount - len(from_bank)
    try:
        if len(chosen) > 1:
            extra = fetch_mixed(wanted, chosen, difficulty, question_type)
        else:
            extra = fetch_from_opentdb(wanted, chosen[0] if chosen else "all", difficulty, question_type)
    except TriviaError:
        if not from_bank:
            raise
        return from_bank  # Open Trivia DB couldn't help: a shorter round beats none
    questions = from_bank + [{**q, "source": "opentdb"} for q in extra]
    random.shuffle(questions)
    return questions


def fetch_from_opentdb(amount, category="all", difficulty="all", question_type="all", retries=RATE_LIMIT_RETRIES, token_retries=1):
    """Questions from Open Trivia DB's live API, for one category (or any)."""
    chosen = parse_categories(category)

    url = f"https://opentdb.com/api.php?amount={amount}"
    if chosen:
        url += f"&category={chosen[0]}"
    if difficulty in VALID_DIFFICULTIES:
        url += f"&difficulty={difficulty}"
    if question_type in VALID_TYPES:
        url += f"&type={question_type}"
    token = session_token.get()
    if token:
        url += f"&token={token}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 429:
            # Rate limited: the body says so too ({"response_code": 5}), handled below
            data = {"response_code": 5}
        else:
            response.raise_for_status()
            data = response.json()
    except (requests.RequestException, ValueError) as e:
        raise TriviaError("Could not reach the trivia service. Try again.") from e

    # Open Trivia DB response codes: 1 = not enough questions, 3 = token expired,
    # 4 = token has used up every question for these settings, 5 = rate limited
    code = data.get("response_code", 0)
    if code in (3, 4) and token and token_retries > 0:
        if code == 3:
            session_token.forget()
        else:
            session_token.reset()
        return fetch_from_opentdb(amount, category, difficulty, question_type, retries, token_retries - 1)
    if code == 4:
        raise NotEnoughQuestions("You've seen every question for those settings. Try another category or difficulty.")
    if code == 1:
        raise NotEnoughQuestions("Not enough questions for those settings. Try fewer questions or another category.")
    if code == 5:
        if retries > 0:
            time.sleep(RATE_LIMIT_WAIT)
            return fetch_from_opentdb(amount, category, difficulty, question_type, retries - 1, token_retries)
        raise TriviaError("The trivia service is busy. Wait a few seconds and try again.")
    if code != 0:
        raise TriviaError("Failed to fetch questions")

    return data.get("results", [])


def prepare_question(raw):
    """Decode an Open Trivia DB question and fix its answer order.

    Shuffling once on the server means every player sees the options in the same order.
    The result keeps the correct answer under "correct"; never send that key to a browser
    before the player has answered.
    """
    correct = html.unescape(raw["correct_answer"])
    if raw["type"] == "multiple":
        options = [correct] + [html.unescape(a) for a in raw["incorrect_answers"]]
        random.shuffle(options)
    else:
        options = ["True", "False"]
    return {
        "question": html.unescape(raw["question"]),
        "category": html.unescape(raw["category"]),
        "difficulty": raw.get("difficulty", ""),
        "type": raw["type"],
        "source": raw.get("source", ""),
        "options": options,
        "correct": correct,
    }


def public_question(question):
    """A prepared question without its correct answer, safe to send before answering."""
    return {k: question.get(k, "") for k in ("question", "category", "difficulty", "type", "source", "options")}


# Open Trivia DB's names for the categories the end-to-end tests ask for
TEST_CATEGORY_NAMES = {"9": "General Knowledge", "22": "Geography", "23": "History"}


def offline_questions(amount, categories=()):
    """Predictable questions for end-to-end tests (QUIZZR_OFFLINE_TRIVIA=1): the answer to
    "Test question N" is always "Right N", and it's always one of four options. With
    categories chosen, the questions take turns between them."""
    names = [TEST_CATEGORY_NAMES.get(c, "General Knowledge") for c in categories] or ["General Knowledge"]
    return [
        {
            "type": "multiple",
            "difficulty": ("easy", "medium", "hard")[i % 3],
            "category": names[i % len(names)],
            "question": f"Test question {i + 1}",
            "correct_answer": f"Right {i + 1}",
            "incorrect_answers": [f"Wrong {i + 1}a", f"Wrong {i + 1}b", f"Wrong {i + 1}c"],
        }
        for i in range(amount)
    ]
