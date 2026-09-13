from __future__ import annotations

from pathlib import Path
from typing import Any

import pytesseract

from .config import TESSERACT_CMD, TESSERACT_CONFIG, TESSERACT_FALLBACK_CONFIG
from .image import preprocess_image
from .parser import extract_prescription, normalize_text


pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def recognize_image(image_path: Path) -> dict[str, Any]:
	image = preprocess_image(image_path)
	candidates = []
	for config in (TESSERACT_CONFIG, TESSERACT_FALLBACK_CONFIG, "--psm 11"):
		ocr_data = pytesseract.image_to_data(image, lang="vie+eng", config=config, output_type=pytesseract.Output.DICT)
		candidates.append(_parse_ocr_data(ocr_data, image_path))
	best = max(candidates, key=_candidate_score)
	for candidate in candidates:
		for key, value in best.items():
			if value in (None, [], "") and candidate.get(key) not in (None, [], ""):
				best[key] = candidate[key]
	return best


def _candidate_score(candidate: dict[str, Any]) -> tuple[int, float, int]:
	ocr = candidate.get("ocr", {})
	return (
		len(candidate.get("thuoc", [])),
		float(ocr.get("do_tin_cay_trung_binh") or 0),
		len(candidate.get("van_ban_ocr", "")),
	)


def _parse_ocr_data(ocr_data: dict[str, list[Any]], image_path: Path) -> dict[str, Any]:
	line_items: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
	confidences: list[float] = []
	for index, text in enumerate(ocr_data["text"]):
		value = normalize_text(text)
		try:
			confidence = float(ocr_data["conf"][index])
		except (TypeError, ValueError):
			confidence = -1.0
		if value:
			key = (
				int(ocr_data["block_num"][index]),
				int(ocr_data["par_num"][index]),
				int(ocr_data["line_num"][index]),
			)
			line_items.setdefault(key, []).append((int(ocr_data["left"][index]), value))
		if confidence >= 0:
			confidences.append(confidence / 100)
	lines = [normalize_text(" ".join(value for _, value in sorted(line_items[key]))) for key in sorted(line_items)]
	data = extract_prescription(lines, image_path)
	data["ocr"] = {
		"so_doan_van_ban": len(lines),
		"do_tin_cay_trung_binh": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
		"engine": "tesseract",
	}
	return data