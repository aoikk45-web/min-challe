from fastapi.testclient import TestClient

from app.generate import generate_ten
from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_grade3_warizan_divides_evenly():
    for _ in range(5):
        for prompt, answer in generate_ten("わりざん", 3):
            left, right = prompt.split(" ÷ ")
            a, b = int(left), int(right)
            assert 10 <= a <= 99
            assert 2 <= b <= 9
            assert a % b == 0
            assert answer == str(a // b)


def test_grade3_kakezan_is_2digit_times_1digit():
    for prompt, answer in generate_ten("かけざん", 3):
        left, right = prompt.split(" × ")
        a, b = int(left), int(right)
        assert 10 <= a <= 99
        assert 2 <= b <= 9
        assert answer == str(a * b)


def test_parent_cannot_start():
    client = TestClient(app)
    res = client.post("/api/drills/start", params={"role": "parent"}, json={"kind": "たしざん"})
    assert res.status_code == 403


def test_start_hides_unanswered_correct():
    client = TestClient(app)
    data = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "たしざん"}).json()
    assert data["grade"] == 3
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


def test_start_kokugo_jukugo():
    client = TestClient(app)
    data = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "じゅくごのよみ"}).json()
    assert data["kind"] == "じゅくごのよみ"
    assert data["grade"] == 3
    assert len(data["questions"]) == 10
    assert all(q["correct"] is None for q in data["questions"])


def test_kokugo_kanji_and_jukugo_banks():
    from app.kokugo import JUKUGO_YOMI, KANJI_YOMI

    kanji = generate_ten("かんじのよみ", 3)
    jukugo = generate_ten("じゅくごのよみ", 3)
    assert len(kanji) == 10
    assert len(jukugo) == 10
    assert len({p for p, _ in kanji}) == 10
    kanji_map = dict(KANJI_YOMI)
    jukugo_map = dict(JUKUGO_YOMI)
    for prompt, reading in kanji:
        assert kanji_map[prompt] == reading
    for prompt, reading in jukugo:
        assert jukugo_map[prompt] == reading


def test_kokugo_grades_katakana_as_hiragana():
    client = TestClient(app)
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "かんじのよみ"}).json()
    first = session["questions"][0]
    from app.kokugo import KANJI_YOMI

    reading = dict(KANJI_YOMI)[first["prompt"]]
    katakana = "".join(chr(ord(ch) + 0x60) for ch in reading)
    res = client.post(
        f"/api/drills/{session['id']}/answer",
        params={"role": "child"},
        json={"question_id": first["id"], "answer": katakana},
    )
    assert res.status_code == 200
    answered = next(q for q in res.json()["questions"] if q["id"] == first["id"])
    assert answered["is_correct"] is True
    assert answered["correct"] is not None
