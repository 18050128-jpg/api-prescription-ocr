from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.prescription import PrescriptionResponse
from app.schemas.resource import PrescriptionRecord

client = TestClient(app)


def _register_user(username: str, email: str, password: str = "StrongPass123") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Sample User",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def test_login_rejects_wrong_password():
    username = "sample_wrong_password_user"
    password = "StrongPass123"
    _register_user(username, f"{username}@example.com", password)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "WrongPassword999"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Sai username hoac password."


def test_login_requires_username_and_password():
    response = client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
    assert "Username va password la bat buoc." in response.json()["detail"]


def test_register_duplicate_username_returns_409():
    username = "sample_duplicate_user"
    email = "sampleduplicate@example.com"
    payload = {
        "username": username,
        "email": email,
        "password": "StrongPass123",
        "full_name": "Duplicate User",
    }

    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201, first.text

    second = client.post("/api/v1/auth/register", json=payload)

    assert second.status_code == 409
    assert "da ton tai" in second.json()["detail"].lower()


def test_change_password_rejects_wrong_current_password():
    username = "sample_change_pw_user"
    token = _register_user(username, f"{username}@example.com", "OldPass123")

    response = client.put(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongOldPass123", "new_password": "NewPass456"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Mat khau hien tai khong dung." in response.json()["detail"]


def test_ocr_route_accepts_valid_image_and_persists_result(monkeypatch):
    username = "sample_ocr_user"
    token = _register_user(username, f"{username}@example.com", "StrongPass123")

    fake_result = PrescriptionResponse(
        tep_anh="prescription.png",
        bac_si=["BS. Nguyen Van A"],
        ngay_ke="2026-09-07",
        ho_ten="Nguyen Van B",
        chan_doan="Viem xoang",
        thuoc=[
            {
                "ten": "Paracetamol",
                "so_luong": "2 vien",
                "huong_dan": "Uong sau khi an",
            }
        ],
        van_ban_ocr="sample OCR text",
        ocr={
            "so_doan_van_ban": 3,
            "do_tin_cay_trung_binh": 0.91,
            "engine": "tesseract",
        },
    )

    monkeypatch.setattr(
        "app.api.routes.prescriptions.store_uploaded_image",
        lambda content, filename: (Path("/tmp/prescription_test.png"), "prescription_test.png"),
    )
    monkeypatch.setattr("app.api.routes.prescriptions.process_prescription", lambda content, filename: fake_result)
    monkeypatch.setattr(
        "app.api.routes.prescriptions.save_prescription",
        lambda user_id, payload: PrescriptionRecord(
            id="prescription-123",
            owner_id=user_id,
            tep_anh="prescription_test.png",
            created_at="2026-09-07T10:00:00+00:00",
            data=payload,
        ),
    )

    response = client.post(
        "/api/v1/prescriptions/ocr",
        files={"file": ("prescription.png", b"fake-image-bytes", "image/png")},
        data={"persist": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tep_anh"] == "prescription_test.png"
    assert payload["ho_ten"] == "Nguyen Van B"
    assert payload["thuoc"][0]["ten"] == "Paracetamol"


def test_ocr_route_rejects_non_image_file():
    username = "sample_ocr_invalid_user"
    token = _register_user(username, f"{username}@example.com", "StrongPass123")

    response = client.post(
        "/api/v1/prescriptions/ocr",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File phai la anh toa thuoc."
