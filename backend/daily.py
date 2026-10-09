import json
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

import database
import logs
from ratelimit import RateLimiter, limited
from trivia import TriviaError, fetch_questions, prepare_question, public_question

# Daily challenge: everyone gets the same questions each day (UTC), like Wordle.
#
# 1. GET  /api/daily                  today's date and, if you've started, your questions and answers
# 2. POST /api/daily/start            {token, name} starts your clock and returns the questions
# 3. POST /api/daily/answer           {token, index, answer, date?} checks one answer on the server
# 4. GET  /api/daily/leaderboard      ?date= (default today) finishers: most correct first, then fastest
#
# There are no accounts. The browser makes up a random token and keeps it, and one token
# gets one go per day. On GET requests the token travels in the X-Quizzr-Token header, never
# in the URL, so it can't end up in access logs, browser history or a proxy's records. Correct answers only leave the server once that question is answered.
#
# A run that starts just before midnight (UTC) can still be finished after it: answers and
# the leaderboard take the date the run started, as long as that's today or yesterday.
#
# Results are kept in Postgres when DATABASE_URL is set, or a SQLite file otherwise;
# see database.py.

router = APIRouter(prefix="/api/daily")

DAILY_QUESTIONS = 10
LEADERBOARD_SIZE = 20

_fetch_lock = threading.Lock()  # so two early visitors don't both fetch today's questions

# Generous for a person playing, tight for a script guessing answers
start_limit = RateLimiter(limit=10, window=60)
answer_limit = RateLimiter(limit=60, window=60)

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_sets (
    date        TEXT PRIMARY KEY,
    questions   TEXT NOT NULL,
    created_at  DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_players (
    date        TEXT NOT NULL,
    token       TEXT NOT NULL,
    name        TEXT NOT NULL,
    correct     INTEGER NOT NULL DEFAULT 0,
    started_at  DOUBLE PRECISION NOT NULL,
    finished_at DOUBLE PRECISION,
    PRIMARY KEY (date, token)
);
CREATE TABLE IF NOT EXISTS daily_answers (
    date        TEXT NOT NULL,
    token       TEXT NOT NULL,
    idx         INTEGER NOT NULL,
    answer      TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    answered_at DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (date, token, idx)
);
"""


def today():
    return datetime.now(timezone.utc).date().isoformat()


DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def run_date(requested):
    """The day a request is about: today by default, or yesterday for a run started before midnight."""
    current = today()
    if not requested:
        return current
    yesterday = (datetime.fromisoformat(current) - timedelta(days=1)).date().isoformat()
    if requested in (current, yesterday):
        return requested
    raise HTTPException(status_code=400, detail="That day's challenge has closed.")


def db():
    return database.connect(SCHEMA)


def load_questions(conn, date):
    row = conn.execute("SELECT questions FROM daily_sets WHERE date = ?", (date,)).fetchone()
    return json.loads(row["questions"]) if row else None


def todays_questions(date):
    """Today's prepared questions, fetching and saving them the first time they're asked for."""
    with db() as conn:
        questions = load_questions(conn, date)
    if questions is not None:
        return questions

    with _fetch_lock:
        with db() as conn:
            questions = load_questions(conn, date)
            if questions is not None:
                return questions
        try:
            raw = fetch_questions(DAILY_QUESTIONS, source="opentdb")  # everyone plays these: Open Trivia DB's verified questions
        except TriviaError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        questions = [prepare_question(q) for q in raw]
        with db() as conn:
            conn.execute(
                "INSERT INTO daily_sets (date, questions, created_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                (date, json.dumps(questions), time.time()),
            )
            return load_questions(conn, date)


def finished_ranking(conn, date):
    """Everyone who finished today, best first: most correct, then fastest, then earliest."""
    return conn.execute(
        """
        SELECT token, name, correct, finished_at - started_at AS seconds
        FROM daily_players
        WHERE date = ? AND finished_at IS NOT NULL
        ORDER BY correct DESC, seconds ASC, finished_at ASC
        """,
        (date,),
    ).fetchall()


def player_view(conn, date, token, questions):
    row = conn.execute(
        "SELECT * FROM daily_players WHERE date = ? AND token = ?", (date, token)
    ).fetchone()
    if row is None:
        return None
    answers = conn.execute(
        "SELECT idx, answer, correct FROM daily_answers WHERE date = ? AND token = ? ORDER BY answered_at",
        (date, token),
    ).fetchall()
    view = {
        "name": row["name"],
        "correct": row["correct"],
        "finished": row["finished_at"] is not None,
        "seconds": None,
        "rank": None,
        "finishers": None,
        # in the order they were answered, which is what streaks count
        "answers": [
            {
                "index": a["idx"],
                "answer": a["answer"],
                "correct": bool(a["correct"]),
                "correctAnswer": questions[a["idx"]]["correct"],
            }
            for a in answers
        ],
    }
    if view["finished"]:
        ranking = finished_ranking(conn, date)
        view["seconds"] = round(row["finished_at"] - row["started_at"], 1)
        view["rank"] = next(i + 1 for i, r in enumerate(ranking) if r["token"] == token)
        view["finishers"] = len(ranking)
    return view


class StartBody(BaseModel):
    token: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=20)


class AnswerBody(BaseModel):
    token: str = Field(min_length=8, max_length=64)
    index: int
    answer: str = Field(max_length=500)
    date: str | None = Field(default=None, pattern=DATE_PATTERN)  # the day the run started


@router.get("")
def get_daily(token: str = Header(default="", alias="X-Quizzr-Token", max_length=64)):
    date = today()
    questions = todays_questions(date)
    with db() as conn:
        player = player_view(conn, date, token, questions) if token else None
    return {
        "date": date,
        "total": len(questions),
        # the questions only go out once your clock is running
        "questions": [public_question(q) for q in questions] if player else None,
        "player": player,
    }


@router.post("/start", dependencies=[Depends(limited(start_limit))])
def start_daily(body: StartBody):
    date = today()
    questions = todays_questions(date)
    name = body.name.strip()[:20] or "Player"
    with db() as conn:
        # Starting twice just resumes: the clock keeps its original start time
        conn.execute(
            "INSERT INTO daily_players (date, token, name, started_at) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (date, body.token, name, time.time()),
        )
        player = player_view(conn, date, body.token, questions)
    return {
        "date": date,
        "total": len(questions),
        "questions": [public_question(q) for q in questions],
        "player": player,
    }


@router.post("/answer", dependencies=[Depends(limited(answer_limit))])
def answer_daily(body: AnswerBody):
    date = run_date(body.date)
    if date == today():
        questions = todays_questions(date)
    else:
        with db() as conn:
            questions = load_questions(conn, date)
        if questions is None:
            raise HTTPException(status_code=404, detail="Start today's challenge first.")
    if not 0 <= body.index < len(questions):
        raise HTTPException(status_code=400, detail="There's no question with that number.")

    question = questions[body.index]
    correct = body.answer == question["correct"]
    now = time.time()
    with db() as conn:
        if conn.execute(
            "SELECT 1 FROM daily_players WHERE date = ? AND token = ?", (date, body.token)
        ).fetchone() is None:
            raise HTTPException(status_code=404, detail="Start today's challenge first.")
        try:
            conn.execute(
                "INSERT INTO daily_answers (date, token, idx, answer, correct, answered_at) VALUES (?, ?, ?, ?, ?, ?)",
                (date, body.token, body.index, body.answer, int(correct), now),
            )
        except database.integrity_errors():
            raise HTTPException(status_code=409, detail="You've already answered that question.")

        answered = conn.execute(
            "SELECT COUNT(*) AS n FROM daily_answers WHERE date = ? AND token = ?", (date, body.token)
        ).fetchone()["n"]
        conn.execute(
            """
            UPDATE daily_players
            SET correct = correct + ?,
                finished_at = CASE WHEN ? >= ? THEN ? ELSE finished_at END
            WHERE date = ? AND token = ?
            """,
            (int(correct), answered, len(questions), now, date, body.token),
        )
        player = player_view(conn, date, body.token, questions)
    if player["finished"] and answered == len(questions):
        logs.log_event("daily_finished", date=date, correct=player["correct"], seconds=player["seconds"], rank=player["rank"])

    return {
        "index": body.index,
        "answer": body.answer,
        "correct": correct,
        "correctAnswer": question["correct"],
        "player": player,
    }


@router.get("/leaderboard")
def daily_leaderboard(
    token: str = Header(default="", alias="X-Quizzr-Token", max_length=64),
    date: str | None = Query(default=None, pattern=DATE_PATTERN),
):
    date = run_date(date)
    with db() as conn:
        ranking = finished_ranking(conn, date)
    entries = [
        {
            "rank": i + 1,
            "name": r["name"],
            "correct": r["correct"],
            "seconds": round(r["seconds"], 1),
            "you": bool(token) and r["token"] == token,
        }
        for i, r in enumerate(ranking)
    ]
    shown = entries[:LEADERBOARD_SIZE]
    # If you finished outside the top rows, you still see your own line
    mine = next((e for e in entries if e["you"]), None)
    if mine and mine not in shown:
        shown.append(mine)
    return {"date": date, "finishers": len(entries), "entries": shown}
