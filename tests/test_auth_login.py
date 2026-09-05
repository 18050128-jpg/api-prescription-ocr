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
