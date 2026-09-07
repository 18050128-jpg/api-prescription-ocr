from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import user_service

client = TestClient(app)


def _register_user(client: TestClient, username: str, email: str, password: str = "StrongPass123") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Auth Flow User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def test_register_login_and_change_password_flow(monkeypatch):
    temp_db = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    temp_db.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_db)
    user_service._tokens.clear()

    username = "auth_flow_user"
    email = "auth_flow_user@example.com"
    old_password = "StrongPass123"
    new_password = "NewStrongPass456"

    token = _register_user(client, username, email, old_password)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": old_password},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["username"] == username

    change_response = client.put(
        "/api/v1/auth/change-password",
        json={"current_password": old_password, "new_password": new_password},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_response.status_code == 200, change_response.text
    assert change_response.json()["message"] == "Mat khau da duoc cap nhat."

    next_login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": new_password},
    )
    assert next_login.status_code == 200, next_login.text
    assert next_login.json()["access_token"]


def test_login_requires_valid_credentials(monkeypatch):
    temp_db = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    temp_db.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_db)
    user_service._tokens.clear()

    username = "wrong_password_user"
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "wrongpassword@example.com",
            "password": "StrongPass123",
            "full_name": "Wrong Password User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "IncorrectPass999"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Sai username hoac password."


def test_reset_password_with_username_and_email(monkeypatch):
    temp_db = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    temp_db.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_db)
    user_service._tokens.clear()

    username = "reset_password_user"
    email = "reset@example.com"
    old_password = "StrongPass123"
    new_password = "NewPassword456"

    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": old_password,
            "full_name": "Reset User",
        },
    )

    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={"username": username, "email": email, "new_password": new_password},
    )
    assert reset_response.status_code == 200, reset_response.text
    assert reset_response.json()["message"] == "Mat khau da duoc dat lai."

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": new_password},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["username"] == username


def test_bootstrap_admin_and_admin_route_require_access(monkeypatch):
    temp_db = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_db.parent.mkdir(parents=True, exist_ok=True)
    temp_db.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_db)
    user_service._tokens.clear()

    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "username": "admin_bootstrap",
            "email": "admin_bootstrap@example.com",
            "password": "StrongPass123",
            "full_name": "Bootstrap Admin",
            "role": "admin",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    protected = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200
    assert len(protected.json()) >= 1

    unauthorized = client.get("/api/v1/users")
    assert unauthorized.status_code == 401
