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
	ocr_data = pytesseract.image_to_data(image, lang="vie+eng", config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT)
	data = _parse_ocr_data(ocr_data, image_path)
	fallback_data = pytesseract.image_to_data(image, lang="vie+eng", config=TESSERACT_FALLBACK_CONFIG, output_type=pytesseract.Output.DICT)
	fallback = _parse_ocr_data(fallback_data, image_path)
	for key, value in data.items():
		if value in (None, [], "") and fallback.get(key) not in (None, [], ""):
			data[key] = fallback[key]
	if len(fallback["thuoc"]) > len(data["thuoc"]):
		data["thuoc"] = fallback["thuoc"]
	return data


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