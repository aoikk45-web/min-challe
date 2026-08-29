from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed
from tests.conftest import create_plan, create_reward


def setup_function():
    reset_and_seed()


def test_seed_album_starts_empty():
    client = TestClient(app)
    assert client.get("/api/album").json() == []


def test_plan_complete_adds_album_once():
    client = TestClient(app)
    plan = create_plan(client, title="音読")
    before = len(client.get("/api/album").json())
    client.post(f"/api/plans/{plan['id']}/complete", params={"role": "child"})
    after = client.get("/api/album").json()
    assert len(after) == before + 1
    newest = after[0]
    assert newest["kind"] == "plan"
    assert newest["stamp"] == "📒"
    assert plan["title"] in newest["body"]
    again = client.post(f"/api/plans/{plan['id']}/complete", params={"role": "child"})
    assert again.status_code == 409
    assert len(client.get("/api/album").json()) == before + 1


def test_plan_complete_records_even_if_points_off():
    client = TestClient(app)
    plan = create_plan(client)
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    for rule in rules:
        if rule["event_key"] == "plan_complete":
            rule["enabled"] = False
    client.put("/api/points/rules", params={"role": "parent"}, json=rules)
    before = len(client.get("/api/album").json())
    client.post(f"/api/plans/{plan['id']}/complete", params={"role": "child"})
    assert len(client.get("/api/album").json()) == before + 1


def test_child_cannot_add_memo():
    client = TestClient(app)
    res = client.post(
        "/api/album",
        params={"role": "child"},
        json={"title": "ひみつのメモ", "body": "だめ"},
    )
    assert res.status_code == 403


def test_parent_adds_memo_on_top():
    client = TestClient(app)
    created = client.post(
        "/api/album",
        params={"role": "parent"},
        json={"title": "  きょうのひとこと  ", "body": "  えがおが いいね  "},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["kind"] == "memo"
    assert body["stamp"] == "📝"
    assert body["title"] == "きょうのひとこと"
    assert body["body"] == "えがおが いいね"
    listed = client.get("/api/album", params={"role": "parent"}).json()
    assert listed[0]["id"] == body["id"]


def test_drill_finish_and_stamp_and_redeem_record():
    client = TestClient(app)
    create_reward(client)
    before = {row["kind"] for row in client.get("/api/album").json()}
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": "たしざん"}).json()
    for question in session["questions"]:
        client.post(
            f"/api/drills/{session['id']}/answer",
            params={"role": "child"},
            json={"question_id": question["id"], "answer": 0},
        )
    client.post("/api/points/stamp", params={"role": "parent"}, json={"note": "おてつだい"})
    rewards = client.get("/api/points/rewards").json()
    game = next(r for r in rewards if r["cost"] == 30)
    bal = client.get("/api/points/summary").json()["balance"]
    if bal >= 30:
        client.post(f"/api/points/rewards/{game['id']}/redeem", params={"role": "child"})
    kinds = {row["kind"] for row in client.get("/api/album").json()}
    assert "drill" in kinds
    assert "stamp" in kinds
    if bal >= 30:
        assert "redeem" in kinds
    assert kinds >= before
    drill = next(row for row in client.get("/api/album").json() if row["kind"] == "drill" and "たしざん" in row["body"])
    assert drill["stamp"] == "✨"
    assert "/10" in drill["body"]
