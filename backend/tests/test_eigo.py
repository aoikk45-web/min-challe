from app.eigo import max_grade_for_step, pick_ten
from app.generate import generate_ten


def test_eigo_max_grade_for_step():
    assert max_grade_for_step(1) == 3
    assert max_grade_for_step(2) == 3
    assert max_grade_for_step(3) == 4
    assert max_grade_for_step(4) == 5
    assert max_grade_for_step(5) == 6
    assert max_grade_for_step(6) == 6


def test_eigo_pick_ten_has_four_choices():
    for kind in ("たんご", "あいさつ"):
        items = pick_ten(kind, 1)
        assert len(items) == 10
        for question in items:
            assert question.choices is not None
            assert len(question.choices) == 4
            assert question.correct in question.choices


def test_eigo_step3_uses_grade4_or_below():
    items = pick_ten("たんご", 3)
    assert len(items) == 10
    prompts = {q.prompt for q in items}
    assert "「きょう」は 英語で？" not in prompts


def test_start_eigo_has_choices():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seed import reset_and_seed

    reset_and_seed()
    client = TestClient(app)
    data = client.post(
        "/api/drills/start",
        params={"role": "child"},
        json={"kind": "あいさつ"},
    ).json()
    assert data["kind"] == "あいさつ"
    assert data["step"] == 1
    assert len(data["questions"]) == 10
    assert all(len(q["choices"] or []) == 4 for q in data["questions"])
    assert all(q["correct"] is None for q in data["questions"])


def test_eigo_progress_max_step():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seed import reset_and_seed

    reset_and_seed()
    client = TestClient(app)
    rows = client.get("/api/drills/progress", params={"role": "child"}).json()
    tango = next(row for row in rows if row["kind"] == "たんご")
    assert tango["max_step"] == 6
    assert tango["step_label"].startswith("ステージ1")
    assert "はじめて" in tango["step_label"]


def test_generate_ten_eigo():
    items = generate_ten("たんご", 1)
    assert len(items) == 10


def test_eigo_answer_case_insensitive():
    from fastapi.testclient import TestClient

    from app.database import SessionLocal
    from app.main import app
    from app.models import DrillQuestion
    from app.seed import reset_and_seed

    reset_and_seed()
    client = TestClient(app)
    session = client.post(
        "/api/drills/start",
        params={"role": "child"},
        json={"kind": "たんご"},
    ).json()
    qid = session["questions"][0]["id"]
    with SessionLocal() as db:
        correct = db.get(DrillQuestion, qid).correct
    res = client.post(
        f"/api/drills/{session['id']}/answer",
        params={"role": "child"},
        json={"question_id": qid, "answer": correct.swapcase()},
    )
    assert res.status_code == 200
    answered = next(q for q in res.json()["questions"] if q["id"] == qid)
    assert answered["is_correct"] is True
