from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import IMAGE_EXTENSIONS
from app.core.ocr import recognize_image
from app.services.image_service import store_existing_image
from app.services.resource_service import save_prescription


def collect_images(input_path: Path) -> list[Path]:
	if input_path.is_file():
		return [input_path]
	if input_path.is_dir():
		return sorted(path for path in input_path.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
	raise FileNotFoundError(f"Khong tim thay dau vao: {input_path}")


def main() -> None:
	parser = argparse.ArgumentParser(description="So hoa toa thuoc bang OCR tieng Viet")
	parser.add_argument("input", type=Path, help="Duong dan anh hoac thu muc anh")
	args = parser.parse_args()
	image_paths = collect_images(args.input)
	if not image_paths:
		raise SystemExit("Khong co anh phu hop trong thu muc dau vao.")
	for image_path in image_paths:
		stored_path, stored_name = store_existing_image(image_path)
		result = recognize_image(stored_path)
		result["tep_anh"] = stored_name
		saved = save_prescription("cli", result)
		print(f"OK: {image_path} -> Prescriptions.json ({saved.id})")


if __name__ == "__main__":
	main()