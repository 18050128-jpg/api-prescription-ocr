from __future__ import annotations

from pathlib import Path
import os
import shutil


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
DEFAULT_OUTPUT = Path("data/output")
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CONFIG = "--psm 3"
TESSERACT_FALLBACK_CONFIG = "--psm 6"