from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.prescription import MedicineScheduleUpdate
from app.schemas.resource import MedicineResponse, MedicineUpdate, PrescriptionPage, PrescriptionRecord
from app.services.image_service import UPLOAD_DIR


DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
PRESCRIPTIONS_PATH = DATABASE_DIR / "Prescriptions.json"
MEDICINES_PATH = DATABASE_DIR / "Medicines.json"
PRESCRIPTION_MEDICINES_PATH = DATABASE_DIR / "PrescriptionMedicines.json"


def _prescription_medicines_path() -> Path:
	if MEDICINES_PATH == DATABASE_DIR / "Medicines.json":
		return PRESCRIPTION_MEDICINES_PATH
	return MEDICINES_PATH.with_name("PrescriptionMedicines.json")


def _normalize_medicine_name(value: Any) -> str:
	text = str(value or "").strip()
	if not text:
		return ""
	text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
	text = unicodedata.normalize("NFD", text).lower().replace("đ", "d")
	text = "".join(character for character in text if unicodedata.category(character) != "Mn")
	text = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|mui|g|ml|l|%)\b", " ", text)
	text = re.sub(r"\b(?:viên|vien|v|tablet|tab|capsule|cap|chai|goi|gói|ong|ống|hộp|hop|lọ|lo|tuýp|tuyp|amp|ampoule|bottle|tube|sữa|sua|thuốc|thuoc)\b", " ", text)
	text = re.sub(r"[^a-z0-9]+", " ", text)
	return re.sub(r"\s+", " ", text).strip()


def _medicine_catalog_key(value: Any) -> str:
	text = str(value or "").strip()
	text = unicodedata.normalize("NFD", text).lower().replace("đ", "d")
	text = "".join(character for character in text if unicodedata.category(character) != "Mn")
	return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9./%-]+", " ", text)).strip()


def _deduplicate_medicines(medicines: list[dict[str, Any]]) -> list[dict[str, Any]]:
	seen: set[str] = set()
	unique: list[dict[str, Any]] = []
	for medicine in medicines:
		key = _normalize_medicine_name(medicine.get("ten"))
		if not key:
			unique.append(medicine)
			continue
		if key in seen:
			continue
		seen.add(key)
		unique.append(medicine)
	return unique


def duplicate_medicine_warnings(medicines: list[dict[str, Any]]) -> list[str]:
	seen: dict[str, str] = {}
	variants: dict[str, list[str]] = {}
	counts: dict[str, int] = {}
	warnings: list[str] = []
	for medicine in medicines:
		name = str(medicine.get("ten") or "").strip()
		key = _normalize_medicine_name(name)
		if not key:
			continue
		counts[key] = counts.get(key, 0) + 1
		if name not in variants.setdefault(key, []):
			variants[key].append(name)
		if key not in seen:
			seen[key] = name
	for key, count in counts.items():
		if count > 1:
			other_names = [name for name in variants[key] if name != seen[key]]
			quoted_names = ", ".join(f'"{name}"' for name in other_names)
			variant_text = f" (cách ghi khác: {quoted_names})" if other_names else ""
			warnings.append(f'Thuốc "{seen[key]}"{variant_text} xuất hiện {count} lần trong cùng đơn.')
	return warnings


def _normalize_quantity(value: Any) -> Any:
	if not isinstance(value, str):
		return value
	quantity = value.strip()
	match = re.fullmatch(r"([+-]?[\d.,]+)(\s*.*)?", quantity)
	if not match:
		return value
	number = match.group(1)
	if re.fullmatch(r"[+-]?\d{1,3}[.,]\d{3}", number):
		number = number.replace(".", "").replace(",", "")
	else:
		number = number.replace(",", ".")
	return f"{number}{match.group(2) or ''}"


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


def _medicine_response(link: dict[str, Any], catalog_item: dict[str, Any]) -> MedicineResponse:
	return MedicineResponse.model_validate({
		"id": link["id"],
		"medicine_id": link.get("medicine_id"),
		"prescription_id": link["prescription_id"],
		"ten": catalog_item.get("ten", ""),
		"lieu_luong": catalog_item.get("lieu_luong"),
		"so_luong": _normalize_quantity(link.get("so_luong")),
		"huong_dan": link.get("huong_dan"),
		"drug_info": catalog_item.get("drug_info", {}),
		"updated_at": link.get("updated_at") or catalog_item.get("updated_at"),
	})


def _aggregate_quantity(links: list[dict[str, Any]]) -> str | None:
	parts = []
	for link in links:
		match = re.match(r"^\s*(\d+(?:[.,]\d+)?)(?:\s*(.*))?$", str(link.get("so_luong") or ""))
		if not match:
			continue
		parts.append((float(match.group(1).replace(",", ".")), (match.group(2) or "").strip()))
	if not parts:
		return None
	units = {unit for _, unit in parts}
	if len(units) != 1:
		return "; ".join(str(link.get("so_luong")) for link in links if link.get("so_luong"))
	total = sum(value for value, _ in parts)
	value = str(int(total)) if total.is_integer() else str(total)
	unit = next(iter(units))
	return f"{value} {unit}".strip()


def _catalog_medicine_response(catalog_item: dict[str, Any], links: list[dict[str, Any]]) -> MedicineResponse:
	prescription_ids = [str(link["prescription_id"]) for link in links if link.get("prescription_id")]
	instructions = list(dict.fromkeys(str(link["huong_dan"]) for link in links if link.get("huong_dan")))
	return MedicineResponse.model_validate({
		"id": catalog_item["id"],
		"medicine_id": catalog_item["id"],
		"prescription_id": prescription_ids[0] if prescription_ids else None,
		"prescription_ids": prescription_ids,
		"ten": catalog_item.get("ten", ""),
		"lieu_luong": catalog_item.get("lieu_luong"),
		"so_luong": _aggregate_quantity(links),
		"huong_dan": " | ".join(instructions),
		"drug_info": catalog_item.get("drug_info", {}),
		"updated_at": catalog_item.get("updated_at"),
	})


def _sync_inventory_for_prescription(prescription_id: str, medicines: list[dict[str, Any]], updated_at: str) -> None:
	catalog = _read(MEDICINES_PATH)
	links = _read(_prescription_medicines_path())
	rows_for_prescription = [item for item in links if item.get("prescription_id") == prescription_id]
	if not rows_for_prescription:
		return

	for medicine_index, medicine in enumerate(medicines):
		candidate = next(
			(
				row
				for row in rows_for_prescription
				if row.get("ten") == medicine.get("ten")
				and (row.get("huong_dan") == medicine.get("huong_dan") or not row.get("huong_dan") and not medicine.get("huong_dan"))
			),
			None,
		)
		if candidate is None and medicine_index < len(rows_for_prescription):
			candidate = rows_for_prescription[medicine_index]
		if candidate is None:
			continue
		candidate["so_luong"] = medicine.get("so_luong")
		candidate["huong_dan"] = medicine.get("huong_dan")
		candidate["reminder_times"] = medicine.get("reminder_times", candidate.get("reminder_times", []))
		candidate["updated_at"] = updated_at

	_write(MEDICINES_PATH, catalog)
	_write(_prescription_medicines_path(), links)


def save_prescription(owner_id: str, result: dict[str, Any]) -> PrescriptionRecord:
	result = dict(result)
	original_medicines = list(result.get("thuoc", []))
	result["thuoc"] = _deduplicate_medicines(original_medicines)
	result["warnings"] = duplicate_medicine_warnings(original_medicines)
	now = datetime.now(timezone.utc).isoformat()
	prescription_id = str(uuid.uuid4())
	prescription = {"id": prescription_id, "owner_id": owner_id, "tep_anh": result["tep_anh"], "created_at": now, "data": result}
	prescriptions = _read(PRESCRIPTIONS_PATH)
	prescriptions.append(prescription)
	_write(PRESCRIPTIONS_PATH, prescriptions)
	catalog = _read(MEDICINES_PATH)
	links = _read(_prescription_medicines_path())
	for item in result.get("thuoc", []):
		catalog_item = next((medicine for medicine in catalog if _medicine_catalog_key(medicine.get("ten")) == _medicine_catalog_key(item.get("ten"))), None)
		if catalog_item is None:
			catalog_item = {"id": str(uuid.uuid4()), "ten": item["ten"], "lieu_luong": item.get("lieu_luong"), "drug_info": item.get("drug_info", {}), "updated_at": now}
			catalog.append(catalog_item)
		else:
			if not catalog_item.get("lieu_luong") and item.get("lieu_luong"):
				catalog_item["lieu_luong"] = item["lieu_luong"]
			if not catalog_item.get("drug_info") and item.get("drug_info"):
				catalog_item["drug_info"] = item["drug_info"]
		links.append({"id": str(uuid.uuid4()), "prescription_id": prescription_id, "medicine_id": catalog_item["id"], "lieu_luong": catalog_item.get("lieu_luong"), "so_luong": _normalize_quantity(item.get("so_luong")), "huong_dan": item.get("huong_dan"), "reminder_times": item.get("reminder_times", []), "updated_at": now})
	_write(MEDICINES_PATH, catalog)
	_write(_prescription_medicines_path(), links)
	return PrescriptionRecord.model_validate(prescription)


def _can_access_prescription(prescription: dict[str, Any], user: dict[str, Any]) -> bool:
	return user.get("role") not in {"user", "doctor"} or prescription.get("owner_id") == user.get("id")


def list_prescriptions(user: dict[str, Any]) -> list[PrescriptionRecord]:
	items = _read(PRESCRIPTIONS_PATH)
	items = [item for item in items if _can_access_prescription(item, user)]
	return [PrescriptionRecord.model_validate(item) for item in items]


def prescription_image_path(prescription_id: str, user: dict[str, Any]) -> Path | None:
	prescription = next((item for item in _read(PRESCRIPTIONS_PATH) if item.get("id") == prescription_id), None)
	if not prescription or not _can_access_prescription(prescription, user):
		return None
	filename = Path(str(prescription.get("tep_anh") or "")).name
	if not filename:
		return None
	image_path = (UPLOAD_DIR / filename).resolve()
	if image_path.parent != UPLOAD_DIR.resolve() or not image_path.is_file():
		return None
	return image_path


def list_prescriptions_page(
	user: dict[str, Any],
	page: int = 1,
	page_size: int = 10,
	search: str = "",
	status: str = "all",
	sort: str = "newest",
) -> PrescriptionPage:
	all_items = list_prescriptions(user)
	confidence = lambda item: float((item.data.get("ocr") or {}).get("do_tin_cay_trung_binh") or 0)
	summary = {
		"total": len(all_items),
		"success": sum(confidence(item) >= 0.75 for item in all_items),
		"review": sum(0 < confidence(item) < 0.75 for item in all_items),
		"today": sum(item.created_at.date() == datetime.now(timezone.utc).date() for item in all_items),
	}
	normalized_search = search.strip().lower()
	filtered = []
	for item in all_items:
		item_status = "success" if confidence(item) >= 0.75 else "review" if confidence(item) > 0 else "unknown"
		search_text = " ".join(
			str(value)
			for value in (
				item.data.get("ten_benh_vien"),
				item.data.get("ho_ten"),
				item.data.get("ngay_ke"),
				item.data.get("chan_doan"),
				*item.data.get("bac_si", []),
				*(medicine.get("ten", "") for medicine in item.data.get("thuoc", [])),
			)
			if value
		).lower()
		if status != "all" and item_status != status:
			continue
		if normalized_search and normalized_search not in search_text:
			continue
		filtered.append(item)

	if sort == "oldest":
		filtered.sort(key=lambda item: item.created_at)
	elif sort == "patient":
		filtered.sort(key=lambda item: str(item.data.get("ho_ten") or "").lower())
	elif sort == "confidence":
		filtered.sort(key=confidence, reverse=True)
	else:
		filtered.sort(key=lambda item: item.created_at, reverse=True)

	total = len(filtered)
	start = (page - 1) * page_size
	items = filtered[start : start + page_size]
	return PrescriptionPage(
		items=items,
		page=page,
		page_size=page_size,
		total=total,
		total_pages=max(1, (total + page_size - 1) // page_size),
		summary=summary,
	)


def list_medicines() -> list[MedicineResponse]:
	catalog = {item.get("id"): item for item in _read(MEDICINES_PATH)}
	links_by_medicine: dict[str, list[dict[str, Any]]] = {}
	for link in _read(_prescription_medicines_path()):
		if link.get("medicine_id") in catalog:
			links_by_medicine.setdefault(link["medicine_id"], []).append(link)
	return [_catalog_medicine_response(item, links_by_medicine.get(item["id"], [])) for item in catalog.values()]


def update_medicine(medicine_id: str, payload: MedicineUpdate) -> MedicineResponse | None:
	catalog = _read(MEDICINES_PATH)
	links = _read(_prescription_medicines_path())
	catalog_item = next((item for item in catalog if item.get("id") == medicine_id), None)
	if catalog_item is not None:
		linked_items = [item for item in links if item.get("medicine_id") == medicine_id]
		old_name = catalog_item.get("ten")
		changes = payload.model_dump(exclude_unset=True, exclude_none=True)
		for field in ("ten", "lieu_luong", "drug_info"):
			if field in changes:
				catalog_item[field] = changes[field]
		for link in linked_items:
			if "so_luong" in changes:
				link["so_luong"] = _normalize_quantity(changes["so_luong"])
			if "huong_dan" in changes:
				link["huong_dan"] = changes["huong_dan"]
			link["updated_at"] = datetime.now(timezone.utc).isoformat()
		now = datetime.now(timezone.utc).isoformat()
		catalog_item["updated_at"] = now
		_write(MEDICINES_PATH, catalog)
		_write(_prescription_medicines_path(), links)
		for link in linked_items:
			_sync_prescription_medicine(link["prescription_id"], old_name, None, link, catalog_item)
		return _catalog_medicine_response(catalog_item, linked_items)

	link = next((item for item in links if item.get("id") == medicine_id), None)
	if link is None:
		return None
	catalog_item = next((item for item in catalog if item.get("id") == link.get("medicine_id")), None)
	if catalog_item is None:
		return None
	old_name = catalog_item.get("ten")
	old_instruction = link.get("huong_dan")
	changes = payload.model_dump(exclude_unset=True, exclude_none=True)
	for field in ("ten", "lieu_luong", "drug_info"):
		if field in changes:
			catalog_item[field] = changes[field]
	for field in ("so_luong", "huong_dan"):
		if field in changes:
			link[field] = _normalize_quantity(changes[field]) if field == "so_luong" else changes[field]
	now = datetime.now(timezone.utc).isoformat()
	catalog_item["updated_at"] = now
	link["updated_at"] = now
	_write(MEDICINES_PATH, catalog)
	_write(_prescription_medicines_path(), links)
	_sync_prescription_medicine(link["prescription_id"], old_name, old_instruction, link, catalog_item)
	return _medicine_response(link, catalog_item)


def _sync_prescription_medicine(prescription_id: str, old_name: str | None, old_instruction: str | None, link: dict[str, Any], catalog_item: dict[str, Any]) -> None:
	prescriptions = _read(PRESCRIPTIONS_PATH)
	changed = False
	for prescription in prescriptions:
		if prescription.get("id") != prescription_id:
			continue
		for medicine in prescription.get("data", {}).get("thuoc", []):
			if medicine.get("ten") == old_name and (old_instruction is None or medicine.get("huong_dan") == old_instruction):
				medicine["ten"] = catalog_item.get("ten")
				medicine["so_luong"] = link.get("so_luong")
				medicine["huong_dan"] = link.get("huong_dan")
				medicine["drug_info"] = catalog_item.get("drug_info", {})
				changed = True
				break
		break
	if changed:
		_write(PRESCRIPTIONS_PATH, prescriptions)


def delete_medicine(medicine_id: str) -> bool:
	catalog = _read(MEDICINES_PATH)
	links = _read(_prescription_medicines_path())
	catalog_item = next((item for item in catalog if item.get("id") == medicine_id), None)
	if catalog_item is not None:
		selected_links = [item for item in links if item.get("medicine_id") == medicine_id]
		if not selected_links:
			return False
		prescriptions = _read(PRESCRIPTIONS_PATH)
		for prescription in prescriptions:
			items = prescription.get("data", {}).get("thuoc", [])
			prescription["data"]["thuoc"] = [item for item in items if item.get("ten") != catalog_item.get("ten")]
		_write(PRESCRIPTIONS_PATH, prescriptions)
		_write(_prescription_medicines_path(), [item for item in links if item.get("medicine_id") != medicine_id])
		_write(MEDICINES_PATH, [item for item in catalog if item.get("id") != medicine_id])
		return True

	selected = next((item for item in links if item.get("id") == medicine_id), None)
	if selected is None:
		return False
	catalog_item = next((item for item in catalog if item.get("id") == selected.get("medicine_id")), None)
	links = [item for item in links if item.get("id") != medicine_id]
	_write(_prescription_medicines_path(), links)

	prescriptions = _read(PRESCRIPTIONS_PATH)
	for prescription in prescriptions:
		if prescription.get("id") != selected.get("prescription_id"):
			continue
		items = prescription.get("data", {}).get("thuoc", [])
		for index, medicine in enumerate(items):
			if catalog_item and medicine.get("ten") == catalog_item.get("ten") and medicine.get("huong_dan") == selected.get("huong_dan"):
				items.pop(index)
				_write(PRESCRIPTIONS_PATH, prescriptions)
				break
		break
	_write(PRESCRIPTIONS_PATH, prescriptions)
	if catalog_item and not any(item.get("medicine_id") == catalog_item.get("id") for item in links):
		_write(MEDICINES_PATH, [item for item in catalog if item.get("id") != catalog_item.get("id")])
	else:
		_write(MEDICINES_PATH, catalog)
	return True


def consume_medicine(
	prescription_id: str,
	medicine_index: int,
	user: dict[str, Any],
	used_quantity: int,
) -> PrescriptionRecord:
	if used_quantity <= 0:
		raise ValueError("So vien su dung phai lon hon 0.")

	prescriptions = _read(PRESCRIPTIONS_PATH)
	prescription = next((item for item in prescriptions if item.get("id") == prescription_id), None)
	if not prescription or not _can_access_prescription(prescription, user):
		raise KeyError("Khong tim thay don thuoc.")

	medicines = prescription.get("data", {}).get("thuoc", [])
	if not 0 <= medicine_index < len(medicines):
		raise IndexError("Khong tim thay thuoc trong don.")

	quantity = str(medicines[medicine_index].get("so_luong") or "").strip()
	match = re.match(r"^([+-]?\d+(?:[.,]\d+)?)(\s*.*)$", quantity)
	if not match or float(match.group(1).replace(",", ".")) <= 0:
		raise ValueError("Thuoc da het so luong.")

	current_quantity = float(match.group(1).replace(",", "."))
	remaining = current_quantity - used_quantity
	if remaining < 0:
		raise ValueError("So vien su dung vuot qua so luong con lai.")
	quantity_value = str(int(remaining)) if remaining.is_integer() else str(remaining)
	medicines[medicine_index]["so_luong"] = f"{quantity_value}{match.group(2)}"
	prescription["data"]["thuoc"] = medicines
	prescriptions_updated_at = datetime.now(timezone.utc).isoformat()
	prescription["updated_at"] = prescriptions_updated_at
	_write(PRESCRIPTIONS_PATH, prescriptions)

	_sync_inventory_for_prescription(prescription_id, medicines, prescriptions_updated_at)

	return PrescriptionRecord.model_validate(prescription)


def update_medicine_schedule(
	prescription_id: str,
	medicine_index: int,
	payload: MedicineScheduleUpdate,
	user: dict[str, Any],
) -> PrescriptionRecord:
	prescriptions = _read(PRESCRIPTIONS_PATH)
	prescription = next((item for item in prescriptions if item.get("id") == prescription_id), None)
	if not prescription or not _can_access_prescription(prescription, user):
		raise KeyError("Khong tim thay don thuoc.")

	medicines = prescription.get("data", {}).get("thuoc", [])
	if not 0 <= medicine_index < len(medicines):
		raise IndexError("Khong tim thay thuoc trong don.")

	clean_times = [time.strip() for time in payload.reminder_times]
	if len(clean_times) > 4 or any(
		time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time)
		for time in clean_times
	):
		raise ValueError("Gio nhac thuoc khong hop le.")
	medicines[medicine_index]["reminder_times"] = clean_times
	prescription["data"]["thuoc"] = medicines
	prescription["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write(PRESCRIPTIONS_PATH, prescriptions)

	return PrescriptionRecord.model_validate(prescription)
