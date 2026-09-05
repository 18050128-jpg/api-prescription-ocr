from __future__ import annotations

import uuid
from pathlib import Path


UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def store_uploaded_image(content: bytes, filename: str) -> tuple[Path, str]:
	if not content:
		raise ValueError("File anh rong.")
	suffix = Path(filename).suffix.lower()
	if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
		suffix = ".png"
	stored_name = f"prescription_{uuid.uuid4().hex}{suffix}"
	stored_path = UPLOAD_DIR / stored_name
	UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
	stored_path.write_bytes(content)
	return stored_path, stored_name


def store_existing_image(source: Path) -> tuple[Path, str]:
	if not source.is_file():
		raise FileNotFoundError(f"Khong tim thay anh: {source}")
	return store_uploaded_image(source.read_bytes(), source.name)
