import re

from fastapi.testclient import TestClient

from app.drill_progress import PERFECT_NEEDED, apply_perfect_streak
from app.generate import WORD_STEP_FROM, generate_ten
from app.main import app
from app.models import DrillProgress
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def _assert_grade3_equation(kind: str, prompt: str, answer: str) -> None:
    if kind == "わりざん":
        left, right = prompt.split(" ÷ ")
        a, b = int(left), int(right)
        assert 10 <= a <= 99
        assert 2 <= b <= 9
        assert a % b == 0
        assert answer == str(a // b)
        return
    left, right = prompt.split(" × ")
    a, b = int(left), int(right)
    assert 10 <= a <= 99
    assert 2 <= b <= 9
    assert answer == str(a * b)


def _assert_word_matches_kind(kind: str, prompt: str, answer: str) -> None:
    assert "？" in prompt
    nums = [int(n) for n in re.findall(r"\d+", prompt)]
    assert len(nums) >= 2
    a, b = nums[0], nums[1]
    if kind == "たしざん":
        assert answer == str(a + b)
    elif kind == "ひきざん":
        assert answer == str(a - b)
    elif kind == "かけざん":
        assert answer == str(a * b)
    else:
        assert b != 0 and a % b == 0
        assert answer == str(a // b)


def test_step1_tashi_is_small():
    for prompt, answer in generate_ten("たしざん", 1):
        assert "？" not in prompt
        left, right = prompt.split(" + ")
        a, b = int(left), int(right)
        assert 1 <= a <= 5
        assert 1 <= b <= 5
        assert answer == str(a + b)


def test_step_below_40_has_no_word_problems():
    items = generate_ten("たしざん", WORD_STEP_FROM - 1)
    assert all("？" not in p for p, _ in items)


def test_grade3_band_warizan_divides_evenly():
    step = 45
    for _ in range(5):
        items = generate_ten("わりざん", step)
        assert len(items) == 10
        for prompt, answer in items[:8]:
            _assert_grade3_equation("わりざん", prompt, answer)
        for prompt, answer in items[8:]:
            _assert_word_matches_kind("わりざん", prompt, answer)


def test_grade3_band_kakezan_is_2digit_times_1digit():
    step = 45
    items = generate_ten("かけざん", step)
    assert len(items) == 10
    for prompt, answer in items[:8]:
        _assert_grade3_equation("かけざん", prompt, answer)
    for prompt, answer in items[8:]:
        _assert_word_matches_kind("かけざん", prompt, answer)


def test_math_last_two_are_word_problems_from_step40():
    step = 50
    for kind in ("たしざん", "ひきざん", "かけざん", "わりざん"):
        items = generate_ten(kind, step)
        assert len(items) == 10
        for prompt, _answer in items[:8]:
            assert "？" not in prompt
        for prompt, answer in items[8:]:
            _assert_word_matches_kind(kind, prompt, answer)


def test_apply_perfect_streak_needs_five():
    row = DrillProgress(member_id=1, kind="たしざん", step=1, perfect_streak=0)
    for _ in range(PERFECT_NEEDED - 1):
        assert apply_perfect_streak(row, 10) is False
        assert row.step == 1
    assert apply_perfect_streak(row, 10) is True
    assert row.step == 2
    assert row.perfect_streak == 0


def test_apply_perfect_streak_resets_on_miss():
    row = DrillProgress(member_id=1, kind="たしざん", step=1, perfect_streak=3)
    assert apply_perfect_streak(row, 9) is False
    assert row.perfect_streak == 0
    assert row.step == 1


def test_progress_api_lists_all_drill_kinds():
    client = TestClient(app)
    rows = client.get("/api/drills/progress", params={"role": "child"}).json()
    kinds = {row["kind"] for row in rows}
    assert kinds == {
        "たしざん",
        "ひきざん",
        "かけざん",
        "わりざん",
        "かんじのよみ",
        "じゅくごのよみ",
        "おはなしのどくかい",
        "とどうふけん",
        "にほんのちり",
        "ちずきごう",
        "けんのかたち",
        "いきもののせいかつ",
        "じしゃくとでんき",
        "たいようとかげ",
        "ひかりとおと",
        "てんきとみず",
    }
    tashi = next(row for row in rows if row["kind"] == "たしざん")
    assert tashi["step"] == 1
    assert tashi["perfect_streak"] == 0
    assert tashi["max_step"] == 100
    kanji = next(row for row in rows if row["kind"] == "かんじのよみ")
    assert kanji["step"] == 1


def test_parent_cannot_start():
    client = TestClient(app)
    res = client.post("/api/drills/start", params={"role": "parent"}, json={"kind": "たしざん"})
    assert res.status_code == 403


def test_start_hides_unanswered_correct():
    client = TestClient(app)
    data = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "たしざん"}).json()
    assert data["grade"] == 3
    assert data["step"] == 1
    assert data["status"] == "in_progress"
    assert len(data["questions"]) == 10
    assert all(q["correct"] is None and q["child_answer"] is None for q in data["questions"])


def test_resume_in_progress_instead_of_new():
    client = TestClient(app)
    first = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "たしざん"}).json()
    second = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "かけざん"}).json()
    assert first["id"] == second["id"]
    assert second["kind"] == "たしざん"


def test_answer_and_finish():
    client = TestClient(app)
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "ひきざん"}).json()
    for question in session["questions"]:
        res = client.post(
            f"/api/drills/{session['id']}/answer",
            params={"role": "child"},
            json={"question_id": question["id"], "answer": 0},
        )
        assert res.status_code == 200
        body = res.json()
        answered = next(q for q in body["questions"] if q["id"] == question["id"])
        assert answered["correct"] is not None
        assert answered["is_correct"] == (str(0) == str(answered["correct"]))
    finished = res.json()
    assert finished["status"] == "finished"
    assert finished["correct_count"] is not None
    assert finished["duration_sec"] is not None
    again = client.post(
        f"/api/drills/{session['id']}/answer",
        params={"role": "child"},
        json={"question_id": session["questions"][0]["id"], "answer": 1},
    )
    assert again.status_code == 409


def test_history_lists_finished():
    client = TestClient(app)
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "わりざん"}).json()
    for question in session["questions"]:
        client.post(
            f"/api/drills/{session['id']}/answer",
            params={"role": "child"},
            json={"question_id": question["id"], "answer": 1},
        )
    history = client.get("/api/drills/history", params={"role": "parent"}).json()
    assert history[0]["id"] == session["id"]
    assert history[0]["status"] == "finished"
    assert history[0]["kind"] == "わりざん"
    assert history[0]["step"] == 1


def test_start_kokugo_jukugo():
    client = TestClient(app)
    data = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "じゅくごのよみ"}).json()
    assert data["kind"] == "じゅくごのよみ"
    assert data["grade"] == 3
    assert data["step"] == 1
    assert len(data["questions"]) == 10
    assert all(q["correct"] is None for q in data["questions"])


def test_kokugo_step1_uses_grade1_pool():
    items = generate_ten("かんじのよみ", 1)
    assert len(items) == 10
    from app.kokugo import _kanji_bank, _max_grade_for_step

    allowed = {row["char"] for row in _kanji_bank() if row["grade"] <= _max_grade_for_step(1)}
    for prompt, _ in items:
        assert "？" in prompt
        assert "\n" in prompt
        assert any(char in prompt for char in allowed)


def test_kokugo_always_uses_context():
    for kind in ("かんじのよみ", "じゅくごのよみ"):
        items = generate_ten(kind, 1)
        assert len(items) == 10
        for prompt, _ in items:
            assert "？" in prompt
            assert "\n" in prompt
            assert "「" in prompt and "」の よみは？" in prompt


def test_kokugo_sentence_from_step40():
    items = generate_ten("じゅくごのよみ", 50)
    assert len(items) == 10
    assert all("？" in p and "\n" in p for p, _ in items)


def test_kokugo_grades_katakana_as_hiragana():
    client = TestClient(app)
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "かんじのよみ"}).json()
    first = session["questions"][0]
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import DrillQuestion

    db = SessionLocal()
    q = db.get(DrillQuestion, first["id"])
    reading = q.correct if q else ""
    db.close()
    katakana = "".join(chr(ord(ch) + 0x60) for ch in reading if "\u3040" <= ch <= "\u309f")
    res = client.post(
        f"/api/drills/{session['id']}/answer",
        params={"role": "child"},
        json={"question_id": first["id"], "answer": katakana},
    )
    assert res.status_code == 200
    answered = next(q for q in res.json()["questions"] if q["id"] == first["id"])
    assert answered["is_correct"] is True
    assert answered["correct"] is not None


def test_start_shakai_has_choices():
    client = TestClient(app)
    data = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "とどうふけん"}).json()
    assert data["kind"] == "とどうふけん"
    assert len(data["questions"]) == 10
    first = data["questions"][0]
    assert first["choices"] is not None
    assert len(first["choices"]) == 4


def test_shakai_pick_ten_has_four_choices():
    items = generate_ten("ちずきごう", 1)
    assert len(items) == 10
    for question in items:
        assert question.choices is not None
        assert len(question.choices) == 4
        assert question.image_url is not None


def test_chizukigo_step1_uses_distinct_symbols():
    from app.shakai import _symbol_choice_pool

    items = generate_ten("ちずきごう", 1)
    assert len(items) == 10
    urls = [q.image_url for q in items]
    assert len(set(urls)) == 10
    pool = set(_symbol_choice_pool(1))
    for question in items:
        assert all(choice in pool for choice in question.choices or [])


def test_chizukigo_high_step_uses_more_symbols():
    from app.shakai import _symbol_pool

    low = len(_symbol_pool(1))
    high = len(_symbol_pool(6))
    assert high > low


def test_shakai_progress_max_step():
    client = TestClient(app)
    rows = client.get("/api/drills/progress", params={"role": "child"}).json()
    shakai = next(row for row in rows if row["kind"] == "ちずきごう")
    assert shakai["max_step"] == 6
    assert shakai["step_label"].startswith("ステージ")


def test_shakai_context_from_stage5():
    items = generate_ten("とどうふけん", 5)
    assert len(items) == 10
    assert all("\n" not in q.prompt for q in items[:8])
    assert all("\n" in q.prompt for q in items[8:])


def test_kokugo_bank_examples_are_natural():
    import json
    from pathlib import Path

    from app.kokugo_natural import is_natural_example, plain_sentence

    data_dir = Path(__file__).resolve().parents[1] / "data" / "kokugo"
    for name in ("kanji.json", "jukugo.json"):
        for row in json.loads((data_dir / name).read_text(encoding="utf-8")):
            target = row.get("char") or row["word"]
            for example in row.get("examples", []):
                assert is_natural_example(target, example["sentence"]), (name, target, example["sentence"])
    kanji = json.loads((data_dir / "kanji.json").read_text(encoding="utf-8"))
    hi = next(row for row in kanji if row["char"] == "日")
    for example in hi["examples"]:
        plain = plain_sentence(example["sentence"])
        assert "日本" not in plain, example


def test_nihon_accepts_both_readings():
    from app.generate import kokugo_reading_matches

    assert kokugo_reading_matches("にほん", "にほん")
    assert kokugo_reading_matches("にっぽん", "にほん")
    assert not kokugo_reading_matches("にち", "にほん")


def test_drill_finish_awards_points():
    client = TestClient(app)
    before = client.get("/api/points/summary", params={"role": "child"}).json()["balance"]
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "たしざん"}).json()
    last = session
    for question in session["questions"]:
        last = client.post(
            f"/api/drills/{session['id']}/answer",
            params={"role": "child"},
            json={"question_id": question["id"], "answer": 0},
        ).json()
    assert last["status"] == "finished"
    assert last["points_earned"] == 10
    after = client.get("/api/points/summary", params={"role": "child"}).json()["balance"]
    assert after - before == 10


def test_dokkai_bank_has_ninety_stories():
    import json
    from pathlib import Path

    rows = json.loads((Path(__file__).resolve().parents[1] / "data" / "kokugo" / "dokkai.json").read_text(encoding="utf-8"))
    assert len(rows) == 90
    counts = {}
    for row in rows:
        counts[row["stage"]] = counts.get(row["stage"], 0) + 1
        assert len(row["questions"]) == 3
        for q in row["questions"]:
            assert q["correct"] in q["choices"]
            assert len(q["choices"]) == 4
    assert counts == {1: 15, 2: 15, 3: 15, 4: 15, 5: 15, 6: 15}


def test_dokkai_session_has_three_questions_and_passage():
    from app.database import SessionLocal
    from app.models import DrillQuestion

    client = TestClient(app)
    session = client.post(
        "/api/drills/start",
        params={"role": "child"},
        json={"kind": "おはなしのどくかい"},
    ).json()
    assert session["kind"] == "おはなしのどくかい"
    assert len(session["questions"]) == 3
    assert session["passage"]
    assert session["passage_title"]
    assert all(q["choices"] for q in session["questions"])
    last = session
    with SessionLocal() as db:
        for question in session["questions"]:
            row = db.get(DrillQuestion, question["id"])
            assert row is not None
            last = client.post(
                f"/api/drills/{session['id']}/answer",
                params={"role": "child"},
                json={"question_id": question["id"], "answer": row.correct},
            ).json()
    assert last["status"] == "finished"
    assert last["correct_count"] == 3
    assert last["points_earned"] == 15


def test_dokkai_session_shuffles_choices():
    import json
    import random

    from app.database import SessionLocal
    from app.models import DrillQuestion

    random.seed(7)
    client = TestClient(app)
    session = client.post(
        "/api/drills/start",
        params={"role": "child"},
        json={"kind": "おはなしのどくかい"},
    ).json()
    first_positions: list[int] = []
    with SessionLocal() as db:
        for question in session["questions"]:
            row = db.get(DrillQuestion, question["id"])
            assert row is not None
            choices = json.loads(row.choices_json or "{}")["choices"]
            assert row.correct in choices
            first_positions.append(choices.index(row.correct))
    assert len(set(first_positions)) > 1


def test_dokkai_progress_uses_six_stages():
    client = TestClient(app)
    rows = client.get("/api/drills/progress", params={"role": "child"}).json()
    dokkai = next(row for row in rows if row["kind"] == "おはなしのどくかい")
    assert dokkai["max_step"] == 6
    assert dokkai["step_label"].startswith("ステージ")
