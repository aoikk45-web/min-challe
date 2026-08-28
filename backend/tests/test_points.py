from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_seed_has_balance_and_rules():
    client = TestClient(app)
    summary = client.get("/api/points/summary").json()
    assert summary["balance"] >= 13
    rules = client.get("/api/points/rules").json()
    keys = {r["event_key"] for r in rules}
    assert keys == {"drill_complete", "drill_perfect", "plan_complete", "stamp"}


def test_plan_complete_awards_points():
    client = TestClient(app)
    before = client.get("/api/points/summary").json()["balance"]
    open_plan = next(p for p in client.get("/api/plans").json() if p["completed_at"] is None)
    client.post(f"/api/plans/{open_plan['id']}/complete", params={"role": "child"})
    after = client.get("/api/points/summary").json()["balance"]
    assert after == before + 8
    again = client.post(f"/api/plans/{open_plan['id']}/complete", params={"role": "child"})
    assert again.status_code == 409
    assert client.get("/api/points/summary").json()["balance"] == after


def test_disabled_rule_awards_nothing():
    client = TestClient(app)
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    for rule in rules:
        if rule["event_key"] == "plan_complete":
            rule["enabled"] = False
    client.put("/api/points/rules", params={"role": "parent"}, json=rules)
    before = client.get("/api/points/summary").json()["balance"]
    open_plan = next(p for p in client.get("/api/plans").json() if p["completed_at"] is None)
    client.post(f"/api/plans/{open_plan['id']}/complete", params={"role": "child"})
    assert client.get("/api/points/summary").json()["balance"] == before


def test_child_cannot_edit_rules():
    client = TestClient(app)
    rules = client.get("/api/points/rules").json()
    assert client.put("/api/points/rules", params={"role": "child"}, json=rules).status_code == 403


def test_stamp_and_redeem():
    client = TestClient(app)
    before = client.get("/api/points/summary").json()["balance"]
    stamped = client.post("/api/points/stamp", params={"role": "parent"}, json={"note": "おてつだい"})
    assert stamped.status_code == 200
    assert stamped.json()["balance"] == before + 3
    rewards = client.get("/api/points/rewards").json()
    game = next(r for r in rewards if r["cost"] == 30)
    if stamped.json()["balance"] >= 30:
        redeemed = client.post(f"/api/points/rewards/{game['id']}/redeem", params={"role": "child"})
        assert redeemed.status_code == 200
        assert redeemed.json()["balance"] == stamped.json()["balance"] - 30
    expensive = next(r for r in rewards if r["cost"] == 50)
    # drain by redeeming game if still enough, then try expensive
    bal = client.get("/api/points/summary").json()["balance"]
    if bal < 50:
        res = client.post(f"/api/points/rewards/{expensive['id']}/redeem", params={"role": "child"})
        assert res.status_code == 400
        assert "あと" in res.json()["detail"]


def test_parent_cannot_redeem():
    client = TestClient(app)
    reward = client.get("/api/points/rewards").json()[0]
    assert client.post(f"/api/points/rewards/{reward['id']}/redeem", params={"role": "parent"}).status_code == 403
