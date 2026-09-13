from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_game_clear_awards_points():
    client = TestClient(app)
    before = client.get("/api/points/summary", params={"role": "child"}).json()["balance"]
    res = client.post("/api/games/clear", params={"role": "child"}, json={"game": "cups"})
    assert res.status_code == 200
    body = res.json()
    assert body["points_earned"] == 5
    assert body["balance"] == before + 5


def test_game_clear_respects_disabled_rule():
    client = TestClient(app)
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    for rule in rules:
        if rule["event_key"] == "game_clear":
            rule["enabled"] = False
    client.put("/api/points/rules", params={"role": "parent"}, json=rules)
    res = client.post("/api/games/clear", params={"role": "child"}, json={"game": "memory"})
    assert res.status_code == 200
    assert res.json()["points_earned"] == 0


def test_game_clear_family():
    client = TestClient(app)
    res = client.post("/api/games/clear", params={"role": "child"}, json={"game": "family"})
    assert res.status_code == 200
    assert res.json()["points_earned"] == 5


def test_parent_cannot_claim_game_clear():
    client = TestClient(app)
    res = client.post("/api/games/clear", params={"role": "parent"}, json={"game": "cups"})
    assert res.status_code == 403


def _finish_one_drill(client: TestClient, kind: str = "たしざん") -> None:
    session = client.post("/api/drills/start", params={"role": "child"}, json={"kind": kind}).json()
    for question in session["questions"]:
        client.post(
            f"/api/drills/{session['id']}/answer",
            params={"role": "child"},
            json={"question_id": question["id"], "answer": "0"},
        )


def test_game_play_requires_three_drills():
    client = TestClient(app)
    access = client.get("/api/games/access", params={"role": "child"}).json()
    assert access["plays_remaining"] == 0
    assert access["drills_per_play"] == 3

    denied = client.post("/api/games/play", params={"role": "child"}, json={"game": "cups"})
    assert denied.status_code == 403

    for kind in ("たしざん", "ひきざん", "かけざん"):
        _finish_one_drill(client, kind)

    access = client.get("/api/games/access", params={"role": "child"}).json()
    assert access["drills_finished"] == 3
    assert access["plays_remaining"] == 1

    ok = client.post("/api/games/play", params={"role": "child"}, json={"game": "family"})
    assert ok.status_code == 200
    assert ok.json()["plays_remaining"] == 0

    again = client.post("/api/games/play", params={"role": "child"}, json={"game": "memory"})
    assert again.status_code == 403


def test_parent_cannot_start_game_play():
    client = TestClient(app)
    res = client.post("/api/games/play", params={"role": "parent"}, json={"game": "cups"})
    assert res.status_code == 403
