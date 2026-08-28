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
    assert {"drill_complete", "drill_perfect", "plan_complete", "stamp", "custom_test100"} <= keys
    assert next(r for r in rules if r["event_key"] == "custom_test100")["label"] == "テスト100点"


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


def test_delete_custom_rule_keeps_builtins():
    client = TestClient(app)
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    kept = [r for r in rules if r["event_key"] != "custom_test100"]
    res = client.put("/api/points/rules", params={"role": "parent"}, json=kept)
    assert res.status_code == 200
    keys = {r["event_key"] for r in res.json()}
    assert "custom_test100" not in keys
    assert {"drill_complete", "drill_perfect", "plan_complete", "stamp"} <= keys


def test_cannot_delete_builtin_by_omitting():
    client = TestClient(app)
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    without_stamp = [r for r in rules if r["event_key"] != "stamp"]
    res = client.put("/api/points/rules", params={"role": "parent"}, json=without_stamp)
    assert res.status_code == 200
    keys = {r["event_key"] for r in res.json()}
    assert "stamp" in keys


def test_stamp_custom_school_rule():
    client = TestClient(app)
    before = client.get("/api/points/summary").json()["balance"]
    res = client.post(
        "/api/points/stamp",
        params={"role": "parent"},
        json={"note": "さんすう", "event_key": "custom_test100"},
    )
    assert res.status_code == 200
    assert res.json()["balance"] == before + 20
    album = client.get("/api/album").json()
    newest = next(row for row in album if row["title"] == "テスト100点")
    assert newest["body"] == "さんすう"
    ledger = client.get("/api/points/ledger").json()
    assert any(row["event_key"] == "custom_test100" and row["delta"] == 20 for row in ledger)


def test_stamp_rejects_auto_rule():
    client = TestClient(app)
    res = client.post(
        "/api/points/stamp",
        params={"role": "parent"},
        json={"event_key": "plan_complete"},
    )
    assert res.status_code == 400
