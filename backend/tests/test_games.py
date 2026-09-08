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


def test_parent_cannot_claim_game_clear():
    client = TestClient(app)
    res = client.post("/api/games/clear", params={"role": "parent"}, json={"game": "cups"})
    assert res.status_code == 403
