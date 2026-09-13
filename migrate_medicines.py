from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path


DATABASE_DIR = Path(__file__).resolve().parent / "app" / "database"
MEDICINES_PATH = DATABASE_DIR / "Medicines.json"
LINKS_PATH = DATABASE_DIR / "PrescriptionMedicines.json"


def catalog_key(value: str) -> str:
	text = unicodedata.normalize("NFD", str(value or "").strip()).lower().replace("đ", "d")
	text = "".join(character for character in text if unicodedata.category(character) != "Mn")
	return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9./%-]+", " ", text)).strip()


def main() -> None:
	rows = json.loads(MEDICINES_PATH.read_text(encoding="utf-8"))
	if rows and all("prescription_id" not in row for row in rows):
		print("Medicines.json is already normalized; nothing to migrate.")
		return
	catalog: list[dict] = []
	by_key: dict[str, dict] = {}
	links: list[dict] = []
	now = datetime.now(timezone.utc).isoformat()

	for row in rows:
		key = catalog_key(row.get("ten"))
		medicine = by_key.get(key)
		if medicine is None:
			medicine = {
				"id": str(uuid.uuid4()),
				"ten": row.get("ten", "").strip(),
				"drug_info": row.get("drug_info", {}),
				"updated_at": row.get("updated_at", now),
			}
			by_key[key] = medicine
			catalog.append(medicine)
		elif not medicine.get("drug_info") and row.get("drug_info"):
			medicine["drug_info"] = row["drug_info"]

		links.append({
			"id": row.get("id") or str(uuid.uuid4()),
			"prescription_id": row["prescription_id"],
			"medicine_id": medicine["id"],
			"so_luong": row.get("so_luong"),
			"huong_dan": row.get("huong_dan"),
			"reminder_times": row.get("reminder_times", []),
			"updated_at": row.get("updated_at", now),
		})

	MEDICINES_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	LINKS_PATH.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"Migrated {len(rows)} rows into {len(catalog)} medicines and {len(links)} prescription links.")


if __name__ == "__main__":
	main()