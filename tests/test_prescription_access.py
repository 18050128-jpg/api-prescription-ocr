import pytest

from app.services import resource_service


def _prescription(owner_id: str, prescription_id: str) -> dict:
    return {
        "id": prescription_id,
        "owner_id": owner_id,
        "tep_anh": "prescription.png",
        "created_at": "2026-09-06T00:00:00+00:00",
        "data": {"thuoc": [{"ten": "Paracetamol", "so_luong": "2 Vien"}]},
    }


def test_doctor_sees_only_owned_prescriptions(monkeypatch):
    records = [
        _prescription("doctor-1", "prescription-1"),
        _prescription("doctor-2", "prescription-2"),
    ]
    monkeypatch.setattr(resource_service, "_read", lambda _path: records)

    result = resource_service.list_prescriptions({"id": "doctor-1", "role": "doctor"})

    assert [item.id for item in result] == ["prescription-1"]


def test_doctor_cannot_consume_foreign_prescription(monkeypatch):
    records = [_prescription("doctor-2", "prescription-2")]
    writes = []
    monkeypatch.setattr(resource_service, "_read", lambda _path: records)
    monkeypatch.setattr(resource_service, "_write", lambda path, data: writes.append((path, data)))

    with pytest.raises(KeyError):
        resource_service.consume_medicine("prescription-2", 0, {"id": "doctor-1", "role": "doctor"})

    assert writes == []
