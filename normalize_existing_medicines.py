from __future__ import annotations

import json
import re
from pathlib import Path


DATABASE_DIR = Path(__file__).resolve().parent / "app" / "database"
MEDICINES_PATH = DATABASE_DIR / "Medicines.json"
LINKS_PATH = DATABASE_DIR / "PrescriptionMedicines.json"
PRESCRIPTIONS_PATH = DATABASE_DIR / "Prescriptions.json"


def split_name_strength(value: str) -> tuple[str, str | None]:
	name = re.sub(r"\s+", " ", str(value or "").strip())
	if name == "Natri clorid 0,9% 10 ml":
		return "Natri clorid", "0,9% 10 ml"
	match = re.match(r"^(.*?)\s+(\d+(?:[.,]\d+)?)\s*(mg|mcg|ml|mui|g|%)$", name, re.IGNORECASE)
	if not match:
		return name, None
	return match.group(1).strip(), f"{match.group(2)} {match.group(3)}"


def main() -> None:
	medicines = json.loads(MEDICINES_PATH.read_text(encoding="utf-8"))
	links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
	prescriptions = json.loads(PRESCRIPTIONS_PATH.read_text(encoding="utf-8"))
	changes: dict[str, tuple[str, str | None]] = {}

	for medicine in medicines:
		old_name = medicine.get("ten", "")
		new_name, strength = split_name_strength(old_name)
		if strength and not medicine.get("lieu_luong"):
			medicine["lieu_luong"] = strength
		medicine["ten"] = new_name
		changes[old_name] = (new_name, medicine.get("lieu_luong"))

	for link in links:
		medicine = next((item for item in medicines if item.get("id") == link.get("medicine_id")), None)
		if medicine:
			link["lieu_luong"] = medicine.get("lieu_luong")

	for prescription in prescriptions:
		for medicine in prescription.get("data", {}).get("thuoc", []):
			old_name = medicine.get("ten", "")
			new_name, strength = changes.get(old_name, split_name_strength(old_name))
			medicine["ten"] = new_name
			if strength:
				medicine["lieu_luong"] = strength

	MEDICINES_PATH.write_text(json.dumps(medicines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	LINKS_PATH.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	PRESCRIPTIONS_PATH.write_text(json.dumps(prescriptions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"Normalized {len(medicines)} catalog medicines and {len(links)} links.")


if __name__ == "__main__":
	main()