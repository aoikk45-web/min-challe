from fastapi.testclient import TestClient

from app.pinutil import DEFAULT_PARENT_PIN, DEFAULT_UNLOCK_PIN, verify_pin
from app.main import app
from app.seed import reset_and_seed


def setup_function():
    reset_and_seed()


def test_auth_status_configured_after_seed():
    client = TestClient(app)
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    assert res.json()["configured"] is True


def test_unlock_ok_and_bad():
    client = TestClient(app)
    assert client.post("/api/auth/unlock", json={"pin": DEFAULT_UNLOCK_PIN}).status_code == 204
    bad = client.post("/api/auth/unlock", json={"pin": "9999"})
    assert bad.status_code == 401


def test_verify_parent_ok_and_bad():
    client = TestClient(app)
    assert client.post("/api/auth/verify-parent", json={"pin": DEFAULT_PARENT_PIN}).status_code == 204
    bad = client.post("/api/auth/verify-parent", json={"pin": "0000"})
    assert bad.status_code == 401


def test_change_pins():
    client = TestClient(app)
    res = client.post(
        "/api/auth/change-pins",
        json={
            "current_parent_pin": DEFAULT_PARENT_PIN,
            "unlock_pin": "4321",
            "parent_pin": "8765",
        },
    )
    assert res.status_code == 204
    assert client.post("/api/auth/unlock", json={"pin": "4321"}).status_code == 204
    assert client.post("/api/auth/verify-parent", json={"pin": "8765"}).status_code == 204
    assert client.post("/api/auth/unlock", json={"pin": DEFAULT_UNLOCK_PIN}).status_code == 401


def test_setup_rejected_when_already_configured():
    client = TestClient(app)
    res = client.post(
        "/api/auth/setup",
        json={"unlock_pin": "1111", "parent_pin": "2222"},
    )
    assert res.status_code == 400


def test_hash_not_plaintext():
    from app.database import SessionLocal
    from app.models import Household

    with SessionLocal() as db:
        hh = db.get(Household, 1)
        assert hh is not None
        assert hh.unlock_pin_hash != DEFAULT_UNLOCK_PIN
        assert "$" in (hh.unlock_pin_hash or "")
        assert verify_pin(DEFAULT_UNLOCK_PIN, hh.unlock_pin_hash)
