from __future__ import annotations

import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen


OPENFDA_URL = "https://api.fda.gov/drug/label.json"
LOOKUP_TIMEOUT_SECONDS = 3


def _clean_name(name: str) -> str:
	return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", name)).strip()


def lookup_drug_info(name: str) -> dict[str, object]:
	clean_name = _clean_name(name)
	if not clean_name:
		return {}

	url = f'{OPENFDA_URL}?search=openfda.brand_name:"{quote(clean_name)}"&limit=1'
	request = Request(url, headers={"Accept": "application/json", "User-Agent": "PrescriptionOCR/1.0"})
	try:
		with urlopen(request, timeout=LOOKUP_TIMEOUT_SECONDS) as response:
			payload = json.load(response)
		result = (payload.get("results") or [{}])[0]
	except (OSError, ValueError, json.JSONDecodeError):
		return {}

	openfda = result.get("openfda") or {}
	fields = {
		"brand_name": openfda.get("brand_name", [clean_name])[0],
		"generic_name": openfda.get("generic_name", [""])[0],
		"manufacturer": openfda.get("manufacturer_name", [""])[0],
		"purpose": (result.get("purpose") or [""])[0],
		"indications": (result.get("indications_and_usage") or [""])[0],
		"warnings": (result.get("warnings") or [""])[0],
		"side_effects": (result.get("adverse_reactions") or [""])[0],
		"dosage": (result.get("dosage_and_administration") or [""])[0],
		"contraindications": (result.get("contraindications") or [""])[0],
		"source": "OpenFDA",
	}
	return {key: value for key, value in fields.items() if value}


def enrich_medicines(medicines: list[dict[str, object]]) -> list[dict[str, object]]:
	for medicine in medicines:
		if not medicine.get("drug_info"):
			medicine["drug_info"] = lookup_drug_info(str(medicine.get("ten") or ""))
	return medicines