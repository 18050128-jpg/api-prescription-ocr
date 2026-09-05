from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.resource import MedicineResponse, MedicineUpdate, PrescriptionRecord


DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
PRESCRIPTIONS_PATH = DATABASE_DIR / "Prescriptions.json"
MEDICINES_PATH = DATABASE_DIR / "Medicines.json"


def _normalize_quantity(value: Any) -> Any:
	if not isinstance(value, str):
		return value
	quantity = value.strip()
	match = re.fullmatch(r"([+-]?\d+)(?:\.0+)?(\s*.*)?", quantity)
	return f"{match.group(1)}{match.group(2) or ''}" if match else value


def _read(path: Path) -> list[dict[str, Any]]:
	DATABASE_DIR.mkdir(parents=True, exist_ok=True)
	if not path.exists() or not path.read_text(encoding="utf-8").strip():
		return []
	data = json.loads(path.read_text(encoding="utf-8"))
	if not isinstance(data, list):
		raise ValueError(f"{path.name} phai chua mot danh sach.")
	return data


def _write(path: Path, data: list[dict[str, Any]]) -> None:
	path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_prescription(owner_id: str, result: dict[str, Any]) -> PrescriptionRecord:
	now = datetime.now(timezone.utc).isoformat()
	prescription_id = str(uuid.uuid4())
	prescription = {"id": prescription_id, "owner_id": owner_id, "tep_anh": result["tep_anh"], "created_at": now, "data": result}
	prescriptions = _read(PRESCRIPTIONS_PATH)
	prescriptions.append(prescription)
	_write(PRESCRIPTIONS_PATH, prescriptions)
	medicines = _read(MEDICINES_PATH)
	for item in result.get("thuoc", []):
		medicines.append({"id": str(uuid.uuid4()), "prescription_id": prescription_id, "ten": item["ten"], "so_luong": _normalize_quantity(item.get("so_luong")), "huong_dan": item.get("huong_dan"), "updated_at": now})
	_write(MEDICINES_PATH, medicines)
	return PrescriptionRecord.model_validate(prescription)


def list_prescriptions(user: dict[str, Any]) -> list[PrescriptionRecord]:
	items = _read(PRESCRIPTIONS_PATH)
	if user.get("role") == "user":
		items = [item for item in items if item.get("owner_id") == user.get("id")]
	return [PrescriptionRecord.model_validate(item) for item in items]


def list_medicines() -> list[MedicineResponse]:
	return [
		MedicineResponse.model_validate({**item, "so_luong": _normalize_quantity(item.get("so_luong"))})
		for item in _read(MEDICINES_PATH)
	]


def update_medicine(medicine_id: str, payload: MedicineUpdate) -> MedicineResponse | None:
	medicines = _read(MEDICINES_PATH)
	for item in medicines:
		if item.get("id") == medicine_id:
			item.update(payload.model_dump())
			item["so_luong"] = _normalize_quantity(item.get("so_luong"))
			item["updated_at"] = datetime.now(timezone.utc).isoformat()
			_write(MEDICINES_PATH, medicines)
			return MedicineResponse.model_validate(item)
	return None


def consume_medicine(prescription_id: str, medicine_index: int, user: dict[str, Any]) -> PrescriptionRecord:
	prescriptions = _read(PRESCRIPTIONS_PATH)
	prescription = next((item for item in prescriptions if item.get("id") == prescription_id), None)
	if not prescription or (user.get("role") == "user" and prescription.get("owner_id") != user.get("id")):
		raise KeyError("Khong tim thay don thuoc.")

	medicines = prescription.get("data", {}).get("thuoc", [])
	if not 0 <= medicine_index < len(medicines):
		raise IndexError("Khong tim thay thuoc trong don.")

	quantity = str(medicines[medicine_index].get("so_luong") or "").strip()
	match = re.match(r"^([+-]?\d+(?:[.,]\d+)?)(\s*.*)$", quantity)
	if not match or float(match.group(1).replace(",", ".")) <= 0:
		raise ValueError("Thuoc da het so luong.")

	remaining = float(match.group(1).replace(",", ".")) - 1
	quantity_value = str(int(remaining)) if remaining.is_integer() else str(remaining)
	medicines[medicine_index]["so_luong"] = f"{quantity_value}{match.group(2)}"
	prescription["data"]["thuoc"] = medicines
	prescriptions_updated_at = datetime.now(timezone.utc).isoformat()
	prescription["updated_at"] = prescriptions_updated_at
	_write(PRESCRIPTIONS_PATH, prescriptions)

	inventories = _read(MEDICINES_PATH)
	prescription_medicines = [item for item in inventories if item.get("prescription_id") == prescription_id]
	if medicine_index < len(prescription_medicines):
		inventory = prescription_medicines[medicine_index]
		inventory["so_luong"] = medicines[medicine_index]["so_luong"]
		inventory["updated_at"] = prescriptions_updated_at
		_write(MEDICINES_PATH, inventories)

	return PrescriptionRecord.model_validate(prescription)
