from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_returns_access_token():
    username = "web_register_user"
    password = "WebRegister123"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "webregister@example.com",
            "password": password,
            "full_name": "Web Register User",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"
    assert payload["username"] == username


def test_login_accepts_json_payload():
    username = "web_login_user"
    password = "WebLogin123"

    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "weblogin@example.com",
            "password": password,
            "full_name": "Web Login User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "access_token" in payload
    assert payload["token_type"] == "bearer"


def test_login_accepts_form_payload():
    username = "web_login_form_user"
    password = "WebLogin123"

    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "webloginform@example.com",
            "password": password,
            "full_name": "Web Form Login User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "access_token" in payload


def test_change_password_with_token():
    username = "web_change_password_user"
    old_password = "WebOldPassword123"
    new_password = "WebNewPassword456"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": "webchangepassword@example.com",
            "password": old_password,
            "full_name": "Change Password User",
        },
    )

    assert register_response.status_code == 201, register_response.text

    token = register_response.json()["access_token"]

    response = client.put(
        "/api/v1/auth/change-password",
        json={"current_password": old_password, "new_password": new_password},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Mat khau da duoc cap nhat."

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": new_password},
    )

    assert login_response.status_code == 200, login_response.text
