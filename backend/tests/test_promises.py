from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.ledger import now_utc
from app.main import app
from app.models import Member, PointLedger, PromiseCheck, PromiseItem, PromiseSettlement
from app.seed import reset_and_seed
from app.timeutil import today_jst


def setup_function():
    reset_and_seed()


def _create_item(client: TestClient, *, name: str = "はをみがく", penalty: int = 5) -> dict:
    res = client.post(
        "/api/promises/items",
        params={"role": "parent"},
        json={"name": name, "penalty": penalty},
    )
    assert res.status_code == 201
    return res.json()


def _bootstrap_before_yesterday(db, member_id: int) -> None:
    today = today_jst()
    yesterday = today - timedelta(days=1)
    start = today - timedelta(days=14)
    d = start
    while d < yesterday:
        db.add(PromiseSettlement(member_id=member_id, day=d, created_at=now_utc()))
        d += timedelta(days=1)


def test_parent_creates_and_child_checks():
    client = TestClient(app)
    item = _create_item(client)
    listed = client.get("/api/promises", params={"role": "child"}).json()
    assert any(row["id"] == item["id"] for row in listed["items"])
    checked = client.put(
        f"/api/promises/checks/{item['id']}",
        params={"role": "child"},
        json={"checked": True},
    )
    assert checked.status_code == 200
    assert checked.json()["checked"] is True
    again = client.get("/api/promises", params={"role": "child"}).json()
    row = next(r for r in again["items"] if r["id"] == item["id"])
    assert row["checked"] is True


def test_child_cannot_create_item():
    client = TestClient(app)
    res = client.post(
        "/api/promises/items",
        params={"role": "child"},
        json={"name": "テスト", "penalty": 3},
    )
    assert res.status_code == 403


def test_settle_miss_deducts_points():
    client = TestClient(app)
    item = _create_item(client, penalty=4)
    for _ in range(5):
        client.post("/api/points/stamp", params={"role": "parent"}, json={"note": "てすと"})
    before = client.get("/api/points/summary").json()["balance"]

    with SessionLocal() as db:
        child = db.scalars(select(Member).where(Member.role == "child")).first()
        row = db.get(PromiseItem, item["id"])
        row.created_at = now_utc() - timedelta(days=2)
        _bootstrap_before_yesterday(db, child.id)
        db.commit()

    res = client.get("/api/promises", params={"role": "child"})
    assert res.status_code == 200
    assert res.json()["deducted_total"] == 4
    after = client.get("/api/points/summary").json()["balance"]
    assert after == before - 4


def test_settle_skips_when_checked():
    client = TestClient(app)
    item = _create_item(client, penalty=7)
    for _ in range(4):
        client.post("/api/points/stamp", params={"role": "parent"}, json={"note": "てすと"})
    before = client.get("/api/points/summary").json()["balance"]

    yesterday = today_jst() - timedelta(days=1)
    with SessionLocal() as db:
        child = db.scalars(select(Member).where(Member.role == "child")).first()
        row = db.get(PromiseItem, item["id"])
        row.created_at = now_utc() - timedelta(days=2)
        db.add(PromiseCheck(member_id=child.id, item_id=item["id"], day=yesterday, checked=True))
        _bootstrap_before_yesterday(db, child.id)
        db.commit()

    res = client.get("/api/promises", params={"role": "child"})
    assert res.status_code == 200
    assert res.json()["deducted_total"] == 0
    assert client.get("/api/points/summary").json()["balance"] == before


def test_settle_balance_floor_zero():
    client = TestClient(app)
    item = _create_item(client, penalty=50)
    client.post("/api/points/stamp", params={"role": "parent"}, json={"note": "てすと"})
    before = client.get("/api/points/summary").json()["balance"]
    assert before == 3

    with SessionLocal() as db:
        child = db.scalars(select(Member).where(Member.role == "child")).first()
        row = db.get(PromiseItem, item["id"])
        row.created_at = now_utc() - timedelta(days=2)
        _bootstrap_before_yesterday(db, child.id)
        db.commit()

    res = client.get("/api/promises", params={"role": "child"})
    assert res.json()["deducted_total"] == before
    assert client.get("/api/points/summary").json()["balance"] == 0
    with SessionLocal() as db:
        child = db.scalars(select(Member).where(Member.role == "child")).first()
        miss = db.scalars(
            select(PointLedger).where(
                PointLedger.member_id == child.id, PointLedger.event_key == "promise_miss"
            )
        ).all()
        assert len(miss) == 1
        assert miss[0].delta == -before
