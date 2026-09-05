from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2


def preprocess_image(image_path: Path) -> Any:
	image = cv2.imread(str(image_path))
	if image is None:
		raise ValueError(f"Khong doc duoc anh: {image_path}")
	height, width = image.shape[:2]
	if max(height, width) < 1600:
		image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
	return image