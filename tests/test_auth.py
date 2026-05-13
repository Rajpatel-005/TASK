from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import src.auth as auth_module
import src.main as main_module
from src.main import fastapi_app


def make_auth_client(monkeypatch):
    state = {
        "otps": {},
        "users": {},
        "next_user_id": 1,
    }

    def fake_initialize_postgres_tables():
        return None

    def fake_get_postgres_db():
        yield state

    def fake_upsert_otp_code(db, mobile_number, otp_code, expires_at):
        db["otps"][mobile_number] = SimpleNamespace(
            mobile_number=mobile_number,
            otp_code=otp_code,
            expires_at=expires_at,
        )

    def fake_get_otp_code(db, mobile_number):
        return db["otps"].get(mobile_number)

    def fake_delete_otp_code(db, otp_record):
        db["otps"].pop(otp_record.mobile_number, None)

    def fake_is_otp_expired(otp_record):
        return datetime.now(timezone.utc) > otp_record.expires_at

    def fake_get_or_create_user(db, mobile_number):
        if mobile_number in db["users"]:
            return db["users"][mobile_number], False

        user = {
            "id": db["next_user_id"],
            "mobile_number": mobile_number,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db["users"][mobile_number] = user
        db["next_user_id"] += 1
        return user, True

    monkeypatch.setattr(main_module, "initialize_postgres_tables", fake_initialize_postgres_tables)
    monkeypatch.setattr(auth_module, "upsert_otp_code", fake_upsert_otp_code)
    monkeypatch.setattr(auth_module, "get_otp_code", fake_get_otp_code)
    monkeypatch.setattr(auth_module, "delete_otp_code", fake_delete_otp_code)
    monkeypatch.setattr(auth_module, "is_otp_expired", fake_is_otp_expired)
    monkeypatch.setattr(auth_module, "get_or_create_user", fake_get_or_create_user)
    fastapi_app.dependency_overrides[auth_module.get_postgres_db] = fake_get_postgres_db

    client = TestClient(fastapi_app)
    return client, state


def test_request_and_verify_otp(monkeypatch):
    client, state = make_auth_client(monkeypatch)

    request_response = client.post(
        "/auth/request-otp",
        json={"mobile_number": "9876543210"},
    )
    assert request_response.status_code == 200
    request_data = request_response.json()
    assert request_data["mobile_number"] == "9876543210"
    assert "otp" in request_data
    assert "9876543210" in state["otps"]

    verify_response = client.post(
        "/auth/verify-otp",
        json={"mobile_number": "9876543210", "otp": request_data["otp"]},
    )
    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert verify_data["user"]["mobile_number"] == "9876543210"
    assert verify_data["token_type"] == "bearer"
    assert "access_token" in verify_data

    client.close()
    fastapi_app.dependency_overrides.clear()


def test_wrong_otp_is_rejected(monkeypatch):
    client, _ = make_auth_client(monkeypatch)

    client.post(
        "/auth/request-otp",
        json={"mobile_number": "9999999999"},
    )

    verify_response = client.post(
        "/auth/verify-otp",
        json={"mobile_number": "9999999999", "otp": "0000"},
    )
    assert verify_response.status_code == 400
    assert verify_response.json()["detail"] == "Invalid OTP"

    client.close()
    fastapi_app.dependency_overrides.clear()
