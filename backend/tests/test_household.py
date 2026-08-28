from fastapi.testclient import TestClient

from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_health():
    client = TestClient(app)
    assert client.get("/api/health").json() == {"ok": True}


def test_household_is_sakura_grade_3():
    client = TestClient(app)
    data = client.get("/api/household").json()
    assert data["name"] == "さくら家"
    assert data["child"]["display_name"] == "みんすけ"
    assert data["child"]["grade"] == 3
    assert data["parent"]["display_name"] == "おかあさん"


def test_role_query_rejects_unknown():
    client = TestClient(app)
    assert client.get("/api/household", params={"role": "teacher"}).status_code == 400
