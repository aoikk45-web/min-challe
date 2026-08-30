from app.generate import generate_ten
from app.rika import max_grade_for_step, pick_ten


def test_rika_max_grade_for_step():
    assert max_grade_for_step(1) == 3
    assert max_grade_for_step(2) == 3
    assert max_grade_for_step(3) == 4
    assert max_grade_for_step(4) == 5
    assert max_grade_for_step(5) == 6
    assert max_grade_for_step(6) == 6


def test_rika_pick_ten_has_four_choices():
    kinds = (
        "いきもののせいかつ",
        "じしゃくとでんき",
        "たいようとかげ",
        "ひかりとおと",
        "てんきとみず",
    )
    for kind in kinds:
        items = pick_ten(kind, 1)
        assert len(items) == 10
        for question in items:
            assert question.choices is not None
            assert len(question.choices) == 4
            assert question.correct in question.choices


def test_rika_step3_uses_grade4_or_below():
    items = pick_ten("いきもののせいかつ", 3)
    assert len(items) == 10
    # grade-5/6 prompts from bank should not appear at step 3
    prompts = {q.prompt for q in items}
    assert "生態系（せいたいけい）とは 何（なに）？" not in prompts


def test_start_rika_has_choices():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seed import reset_and_seed

    reset_and_seed()
    client = TestClient(app)
    data = client.post(
        "/api/drills/start",
        params={"role": "child"},
        json={"kind": "じしゃくとでんき"},
    ).json()
    assert data["kind"] == "じしゃくとでんき"
    assert data["step"] == 1
    assert len(data["questions"]) == 10
    assert all(len(q["choices"] or []) == 4 for q in data["questions"])
    assert all(q["correct"] is None for q in data["questions"])


def test_rika_progress_max_step():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seed import reset_and_seed

    reset_and_seed()
    client = TestClient(app)
    rows = client.get("/api/drills/progress", params={"role": "child"}).json()
    rika = next(row for row in rows if row["kind"] == "いきもののせいかつ")
    assert rika["max_step"] == 6
    assert rika["step_label"].startswith("ステージ1")
    assert "ゆうき" in rika["step_label"]


def test_generate_ten_rika():
    items = generate_ten("いきもののせいかつ", 1)
    assert len(items) == 10
