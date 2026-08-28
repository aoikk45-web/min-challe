from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed
from app.timeutil import today_jst, week_bounds


def setup_function():
    reset_and_seed()


def test_lists_this_week_with_past_completed():
    client = TestClient(app)
    data = client.get("/api/plans").json()
    assert len(data) >= 1
    today = today_jst().isoformat()
    for row in data:
        if row["plan_date"] < today:
            assert row["completed_at"] is not None
        else:
            assert row["completed_at"] is None


def test_week_bounds_are_monday_to_sunday():
    start, end = week_bounds(date(2026, 8, 28))
    assert start == date(2026, 8, 24)
    assert end == date(2026, 8, 30)
    assert start.weekday() == 0
    assert (end - start).days == 6


def test_child_cannot_create():
    client = TestClient(app)
    res = client.post(
        "/api/plans",
        params={"role": "child"},
        json={"plan_date": today_jst().isoformat(), "subject": "さんすう", "title": "テスト", "minutes": 10},
    )
    assert res.status_code == 403


def test_parent_creates_updates_deletes():
    client = TestClient(app)
    created = client.post(
        "/api/plans",
        params={"role": "parent"},
        json={"plan_date": today_jst().isoformat(), "subject": "そのた", "title": "  片付け  ", "minutes": 5},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "片付け"
    plan_id = body["id"]

    patched = client.patch(
        f"/api/plans/{plan_id}",
        params={"role": "parent"},
        json={"minutes": 8, "title": "おうちの手伝い"},
    )
    assert patched.status_code == 200
    assert patched.json()["minutes"] == 8
    assert patched.json()["title"] == "おうちの手伝い"

    deleted = client.delete(f"/api/plans/{plan_id}", params={"role": "parent"})
    assert deleted.status_code == 204
    listed = {row["id"] for row in client.get("/api/plans").json()}
    assert plan_id not in listed


def test_complete_once_then_conflict():
    client = TestClient(app)
    open_plan = next(row for row in client.get("/api/plans").json() if row["completed_at"] is None)
    first = client.post(f"/api/plans/{open_plan['id']}/complete", params={"role": "child"})
    assert first.status_code == 200
    assert first.json()["completed_at"] is not None
    second = client.post(f"/api/plans/{open_plan['id']}/complete", params={"role": "parent"})
    assert second.status_code == 409


def test_from_and_to_must_be_together():
    client = TestClient(app)
    assert client.get("/api/plans", params={"from": today_jst().isoformat()}).status_code == 400


def test_empty_range_is_empty_list():
    client = TestClient(app)
    far = today_jst() + timedelta(days=30)
    data = client.get("/api/plans", params={"from": far.isoformat(), "to": far.isoformat()}).json()
    assert data == []
