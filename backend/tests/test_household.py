from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_health():
    client = TestClient(app)
    assert client.get("/api/health").json() == {"ok": True}


def test_household_is_oono_family():
    client = TestClient(app)
    data = client.get("/api/household").json()
    assert data["name"] == "おおの家"
    assert data["child"]["display_name"] == "ゆうき"
    assert data["child"]["grade"] == 3
    assert data["parent"]["display_name"] == "おうちの人"


def test_role_query_rejects_unknown():
    client = TestClient(app)
    assert client.get("/api/household", params={"role": "teacher"}).status_code == 400


def test_four_pillars_are_reachable():
    client = TestClient(app)
    assert client.get("/api/plans").status_code == 200
    assert client.get("/api/drills/history").status_code == 200
    assert client.get("/api/points/summary").status_code == 200
    assert client.get("/api/album").status_code == 200
    assert client.get("/api/household", params={"role": "parent"}).status_code == 200
