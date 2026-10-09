import html
from collections import Counter

import pytest

import question_bank
import trivia
from conftest import raw_question


def bank_question(category_id, n, difficulty="", qtype="multiple"):
    q = raw_question(f"Q{category_id}-{n}", "A", qtype=qtype)
    return {**q, "difficulty": difficulty, "category_id": category_id, "source": "test"}


@pytest.fixture
def small_bank(monkeypatch):
    questions = (
        [bank_question(22, n, "easy") for n in range(10)]
        + [bank_question(23, n, "hard") for n in range(10)]
        + [bank_question(13, n) for n in range(2)]
    )
    monkeypatch.setattr(question_bank, "_questions", questions)
    monkeypatch.setattr(question_bank, "available", lambda: True)
    monkeypatch.delenv("QUESTION_SOURCE", raising=False)
    return questions


def test_draws_only_questions_that_match_the_settings(small_bank):
    drawn = question_bank.draw(5, ["22"], "easy")
    assert len(drawn) == 5 and {q["question"].split("-")[0] for q in drawn} == {"Q22"}
    with pytest.raises(question_bank.NotEnoughQuestions):
        question_bank.draw(5, ["22"], "hard")


def test_several_categories_share_a_round_evenly(small_bank):
    drawn = question_bank.draw(6, ["22", "23"])
    assert Counter(q["question"].split("-")[0] for q in drawn) == {"Q22": 3, "Q23": 3}


def test_a_category_that_runs_short_is_made_up_by_the_others(small_bank):
    drawn = question_bank.draw(6, ["13", "22"])  # Musicals has only two
    assert Counter(q["question"].split("-")[0] for q in drawn) == {"Q13": 2, "Q22": 4}


def from_open_trivia_db(asked):
    def fetch(amount, *args):
        asked.append(amount)
        return [{"question": f"OTDB {n}"} for n in range(amount)]
    return fetch


def test_the_bank_is_used_first_and_open_trivia_db_fills_gaps(small_bank, monkeypatch):
    asked = []
    monkeypatch.setattr(trivia, "fetch_from_opentdb", from_open_trivia_db(asked))
    round_ = trivia.fetch_questions(4, "22,23")
    assert len(round_) == 4 and not asked and {q["source"] for q in round_} == {"bank"}
    # no easy History in the bank, so Open Trivia DB supplies all of it
    assert [q["source"] for q in trivia.fetch_questions(4, "23", "easy")] == ["opentdb"] * 4
    assert [q["source"] for q in trivia.fetch_questions(4, "23", source="opentdb")] == ["opentdb"] * 4


def test_a_bank_that_runs_short_is_topped_up_from_open_trivia_db(small_bank, monkeypatch):
    asked = []
    monkeypatch.setattr(trivia, "fetch_from_opentdb", from_open_trivia_db(asked))
    round_ = trivia.fetch_questions(5, "13")  # Musicals has two in the bank
    assert asked == [3]
    assert Counter(q["source"] for q in round_) == {"bank": 2, "opentdb": 3}


def test_the_bank_alone_is_used_when_open_trivia_db_fails(small_bank, monkeypatch):
    def down(*args):
        raise trivia.TriviaError("down")
    monkeypatch.setattr(trivia, "fetch_from_opentdb", down)
    assert len(trivia.fetch_questions(5, "13")) == 2
    with pytest.raises(trivia.TriviaError):
        trivia.fetch_questions(5, "23", "easy")  # nothing in the bank to fall back on


@pytest.mark.skipif(not question_bank.BANK_PATH.exists(), reason="the question bank hasn't been built")
def test_every_question_in_the_real_bank_is_well_formed(monkeypatch):
    monkeypatch.setattr(question_bank, "_questions", None)
    questions = question_bank.questions()
    assert len(questions) > 30000
    for q in questions:
        assert 9 <= q["category_id"] <= 32 and q["type"] in ("multiple", "boolean")
        assert q["difficulty"] in ("", "easy", "medium", "hard")
        answer = html.unescape(q["correct_answer"]).casefold()
        wrong = [html.unescape(w).casefold() for w in q["incorrect_answers"]]
        if q["type"] == "multiple":
            assert len(wrong) == 3 and len(set(wrong)) == 3 and answer not in wrong, q
        else:
            assert {answer, *wrong} == {"true", "false"}, q


@pytest.mark.skipif(not question_bank.BANK_PATH.exists(), reason="the question bank hasn't been built")
def test_the_api_serves_a_mixed_round_from_the_real_bank(monkeypatch):
    from fastapi.testclient import TestClient

    import main

    monkeypatch.setattr(question_bank, "_questions", None)
    monkeypatch.delenv("QUESTION_SOURCE", raising=False)
    monkeypatch.setattr(trivia, "fetch_from_opentdb", lambda *a: pytest.fail("Open Trivia DB shouldn't be needed"))
    with TestClient(main.app) as client:
        questions = client.get("/api/questions", params={"amount": 12, "category": "22,25,16"}).json()
    assert len(questions) == 12
    assert Counter(q["category"] for q in questions) == {"Geography": 4, "Art": 4, "Entertainment: Board Games": 4}
