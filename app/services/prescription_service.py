from __future__ import annotations

import tempfile
from pathlib import Path

from app.schemas.prescription import PrescriptionResponse
from app.core.ocr import recognize_image


def process_prescription(content: bytes, filename: str) -> PrescriptionResponse:
	if not content:
		raise ValueError("File anh rong.")
	with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix or ".png", delete=False) as temporary_file:
		temporary_file.write(content)
		temporary_path = Path(temporary_file.name)
	try:
		result = recognize_image(temporary_path)
		result["tep_anh"] = filename
		return PrescriptionResponse.from_result(result)
	finally:
		temporary_path.unlink(missing_ok=True)