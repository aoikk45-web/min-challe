from __future__ import annotations

from fastapi.testclient import TestClient

from app.timeutil import today_jst


def create_plan(
    client: TestClient,
    *,
    title: str = "れんしゅう",
    subject: str = "さんすう",
    minutes: int = 10,
    plan_date: str | None = None,
) -> dict:
    res = client.post(
        "/api/plans",
        params={"role": "parent"},
        json={
            "plan_date": plan_date or today_jst().isoformat(),
            "subject": subject,
            "title": title,
            "minutes": minutes,
        },
    )
    assert res.status_code == 201
    return res.json()


def create_reward(client: TestClient, *, name: str = "ゲーム 15ふん", cost: int = 30) -> dict:
    res = client.post(
        "/api/points/rewards",
        params={"role": "parent"},
        json={"name": name, "cost": cost},
    )
    assert res.status_code == 201
    return res.json()


def add_custom_rule(client: TestClient, *, event_key: str, label: str, points: int) -> list[dict]:
    rules = client.get("/api/points/rules", params={"role": "parent"}).json()
    rules.append(
        {
            "id": -1,
            "event_key": event_key,
            "label": label,
            "points": points,
            "enabled": True,
        }
    )
    res = client.put("/api/points/rules", params={"role": "parent"}, json=rules)
    assert res.status_code == 200
    return res.json()
