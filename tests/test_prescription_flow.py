from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.services import resource_service, user_service

client = TestClient(app)


def _register_and_login(username: str, email: str, password: str = "StrongPass123", role: str = "user") -> tuple[str, dict[str, Any]]:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Prescription User",
            "role": role,
        },
    )
    assert register.status_code == 201, register.text
    token = register.json()["access_token"]
    return token, register.json()


def test_prescription_ocr_route_returns_valid_payload(monkeypatch):
    temp_users = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_users.parent.mkdir(parents=True, exist_ok=True)
    temp_users.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_users)
    user_service._tokens.clear()

    temp_prescriptions = temp_users.parent / "Prescriptions.json"
    temp_prescriptions.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(resource_service, "PRESCRIPTIONS_PATH", temp_prescriptions)
    monkeypatch.setattr(resource_service, "MEDICINES_PATH", temp_users.parent / "Medicines.json")

    token, _ = _register_and_login("ocr_user", "ocr_user@example.com")

    fake_result = {
        "tep_anh": "prescription.png",
        "ten_benh_vien": "BV Binh Dan",
        "bac_si": ["BS. Lan"],
        "ngay_ke": "2026-09-07",
        "ho_ten": "Nguyen Thi Hoa",
        "chan_doan": "Viem xoang",
        "thuoc": [{"ten": "Paracetamol", "so_luong": "2 vien", "huong_dan": "Sau ăn"}],
        "van_ban_ocr": "OCR test text",
        "ocr": {"so_doan_van_ban": 2, "do_tin_cay_trung_binh": 0.85, "engine": "tesseract"},
    }
    monkeypatch.setattr("app.api.routes.prescriptions.store_uploaded_image", lambda content, filename: (temp_users.parent / "stored.png", "stored.png"))
    monkeypatch.setattr("app.api.routes.prescriptions.process_prescription", lambda content, filename: __import__("app.schemas.prescription", fromlist=["PrescriptionResponse"]).PrescriptionResponse.model_validate(fake_result))
    monkeypatch.setattr("app.api.routes.prescriptions.save_prescription", lambda user_id, payload: resource_service.PrescriptionRecord.model_validate({
        "id": "prescription-123",
        "owner_id": user_id,
        "tep_anh": "stored.png",
        "created_at": "2026-09-07T00:00:00+00:00",
        "data": payload,
    }))

    response = client.post(
        "/api/v1/prescriptions/ocr",
        files={"file": ("prescription.png", b"fake-image-bytes", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ho_ten"] == "Nguyen Thi Hoa"
    assert data["thuoc"][0]["ten"] == "Paracetamol"
    assert data["ocr"]["engine"] == "tesseract"


def test_doctor_can_only_access_own_prescriptions(monkeypatch):
    temp_users = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_users.parent.mkdir(parents=True, exist_ok=True)
    temp_users.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_users)
    user_service._tokens.clear()

    temp_prescriptions = temp_users.parent / "Prescriptions.json"
    temp_prescriptions.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(resource_service, "PRESCRIPTIONS_PATH", temp_prescriptions)
    monkeypatch.setattr(resource_service, "MEDICINES_PATH", temp_users.parent / "Medicines.json")

    doc1_token, _ = _register_and_login("doctor_1", "doctor1@example.com", role="doctor")
    _register_and_login("doctor_2", "doctor2@example.com", role="doctor")

    doc1_user = next(user for user in user_service._read_users() if user["username"] == "doctor_1")
    doc2_user = next(user for user in user_service._read_users() if user["username"] == "doctor_2")

    resource_service.save_prescription(doc1_user["id"], {
        "tep_anh": "d1.png",
        "ho_ten": "Patient One",
        "thuoc": [{"ten": "Amoxicillin", "so_luong": "2 vien", "huong_dan": "Sáng"}],
        "van_ban_ocr": "test",
        "ocr": {"so_doan_van_ban": 1, "do_tin_cay_trung_binh": 0.8, "engine": "tesseract"},
    })
    resource_service.save_prescription(doc2_user["id"], {
        "tep_anh": "d2.png",
        "ho_ten": "Patient Two",
        "thuoc": [{"ten": "Vitamin C", "so_luong": "1 vien", "huong_dan": "Tối"}],
        "van_ban_ocr": "test",
        "ocr": {"so_doan_van_ban": 1, "do_tin_cay_trung_binh": 0.8, "engine": "tesseract"},
    })

    response = client.get("/api/v1/prescriptions", headers={"Authorization": f"Bearer {doc1_token}"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["data"]["ho_ten"] == "Patient One"


def test_consume_medicine_validates_quantity_and_access(monkeypatch):
    temp_users = __import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "User.json"
    temp_users.parent.mkdir(parents=True, exist_ok=True)
    temp_users.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(user_service, "USER_DB_PATH", temp_users)
    user_service._tokens.clear()

    temp_prescriptions = temp_users.parent / "Prescriptions.json"
    temp_prescriptions.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(resource_service, "PRESCRIPTIONS_PATH", temp_prescriptions)
    monkeypatch.setattr(resource_service, "MEDICINES_PATH", temp_users.parent / "Medicines.json")

    token, _ = _register_and_login("medicine_user", "medicine_user@example.com")
    user_id = next(item["id"] for item in user_service._read_users() if item["username"] == "medicine_user")

    saved = resource_service.save_prescription(user_id, {
        "tep_anh": "med.png",
        "ho_ten": "Medication User",
        "thuoc": [{"ten": "Amoxicillin", "so_luong": "5 vien", "huong_dan": "Sáng"}],
        "van_ban_ocr": "test",
        "ocr": {"so_doan_van_ban": 1, "do_tin_cay_trung_binh": 0.8, "engine": "tesseract"},
    })

    used_response = client.post(
        f"/api/v1/prescriptions/{saved.id}/medicines/0/use",
        json={"used_quantity": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert used_response.status_code == 200, used_response.text
    assert used_response.json()["thuoc"][0]["so_luong"] == "3 vien"

    inventory_rows = resource_service._read(resource_service.MEDICINES_PATH)
    assert inventory_rows[-1]["so_luong"] == "3 vien"

    too_much = client.post(
        f"/api/v1/prescriptions/{saved.id}/medicines/0/use",
        json={"used_quantity": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert too_much.status_code == 400
    assert "vuot qua" in too_much.json()["detail"].lower()
