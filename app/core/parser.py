from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def normalize_text(text: str) -> str:
	return re.sub(r"\s+", " ", text).strip()


def usable_value(value: str | None) -> str | None:
	value = normalize_text(value or "")
	value = value.strip(" :;©*—")
	return value or None


def clean_name(value: str | None) -> str | None:
	value = usable_value(value)
	if not value:
		return None
	value = re.split(r"\s+(?:Năm|Nam|aM)\s+sinh\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0]
	value = re.split(r"\s+(?:Tuổi|Tuoi|Giới|Gioi)\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0]
	value = re.sub(r"[,.;_\-]+\s*$", "", value)
	value = re.sub(r"[,.;_\-\.]+\s*\d+[A-Za-zÀ-ỹ]*\s*$", "", value)
	value = re.sub(r"\s+(?:mm|ae|re|iin|TAD)\s*$", "", value, flags=re.IGNORECASE)
	value = re.sub(r"\bNGUYT\b", "NGUYỆT", value, flags=re.IGNORECASE)
	return normalize_vietnamese(value.strip())


def normalize_vietnamese(value: str | None) -> str | None:
	value = usable_value(value)
	if not value:
		return None
	corrections = {
		"BENH VIEN UNG BUOU": "BỆNH VIỆN UNG BƯỚU",
		"BỆNH VIEN UNG BƯỚU": "BỆNH VIỆN UNG BƯỚU",
		"Xién": "Xiển",
		"Long Binh": "Long Bình",
		"Thủ Dau Một": "Thủ Dầu Một",
		"Bình Duong": "Bình Dương",
		"nguyên phat": "nguyên phát",
		"căng thang": "căng thẳng",
		"Chi DA ot": "Đình Chi",
		"Óng": "Ống",
		"Tran Dang Ngoc Linh": "Trần Đặng Ngọc Linh",
		"Nguyén Minh Triét": "Nguyễn Minh Triết",
		"NGUYEN VĂN HÙNG": "NGUYỄN VĂN HÙNG",
		"Etoposide Ebewe 100mg/Smil": "Etoposide Ebewe 100mg/5ml",
		"S0ml": "50ml",
		"thr": "thư",
		"tuyên giáp": "tuyến giáp",
		"thé biệt hóa": "thể biệt hóa",
	}
	for source, target in corrections.items():
		value = value.replace(source, target)
	return value


def clean_diagnosis(value: str | None) -> str | None:
	value = usable_value(value)
	if not value:
		return None
	value = re.sub(r"\.{2,}.*$", "", value).strip(" .,-")
	value = re.sub(r"\s*[.,-]?\s*\d+\s*$", "", value).strip(" .,-")
	corrections = {
		r"\bthr\b": "thư",
		r"\bco\b": "cổ",
		r"\bbenh\b": "bệnh",
		r"\bung\b": "Ung",
	}
	for pattern, replacement in corrections.items():
		value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
	value = re.sub(r"\s+(?:mm|ssn|ea|ICO)\s*$", "", value, flags=re.IGNORECASE)
	return normalize_vietnamese(normalize_text(value).strip(" .,-")) or None


def clean_address(value: str | None) -> str | None:
	value = usable_value(value)
	if not value:
		return None
	value = re.sub(r"\s*(?:[_\.\-]\s*){3,}\d{2,}.*$", "", value)
	value = re.sub(r"\s+\d{4,}\s*$", "", value)
	value = re.sub(r"\s+Điện\s*$", "", value, flags=re.IGNORECASE)
	return normalize_vietnamese(value.strip(" .,-_")) or None


def find_pattern(text: str, pattern: str) -> str | None:
	match = re.search(pattern, text, re.IGNORECASE)
	return usable_value(match.group(1)) if match else None


def find_date(text: str) -> str | None:
	date = find_pattern(text, r"\b(\d{2}/\d{2}/\d{4})\b")
	if date:
		return date
	match = re.search(r"Ng(?:ày|ay)\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", text, re.IGNORECASE)
	return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}" if match else None


def extract_hospital(lines: list[str]) -> str | None:
	for line in lines:
		if not re.search(r"BỆNH\s+VIỆN|BỆNH\s+VIEN|BENH\s+VIEN|TRUNG\s+TÂM\s+KHÁM\s+BỆNH|TRUNG\s+TAM\s+KHAM\s+BENH", line, re.IGNORECASE):
			continue
		name = re.split(r"\s+(?:Số|So)\s*:", line, maxsplit=1, flags=re.IGNORECASE)[0]
		name = re.sub(r"^.*?(?=BỆNH\s+VIỆN|BỆNH\s+VIEN|BENH\s+VIEN|TRUNG\s+TÂM\s+KHÁM\s+BỆNH|TRUNG\s+TAM\s+KHAM\s+BENH)", "", name, flags=re.IGNORECASE)
		return normalize_vietnamese(name)
	return None


def extract_doctors(lines: list[str]) -> list[str]:
	doctors: list[str] = []
	line_pattern = re.compile(r"^\s*(?:(?:Ts|ThS)\s*\.?(?:Bs|BS)\.?|BS\.(?:\s*CKI)?|BÁC SĨ|BAC SI)\s*(.+)$", re.IGNORECASE)
	inline_pattern = re.compile(r"(?:(?:Ts|ThS)\s*\.?(?:Bs|BS)\.?|BS\.(?:\s*CKI)?)\s*(.+)$", re.IGNORECASE)
	for line in lines:
		normalized_line = normalize_text(line)
		match = line_pattern.match(normalized_line) or inline_pattern.search(normalized_line)
		if match:
			name = normalize_vietnamese(re.sub(r"^\s*[Il]\s+|\s+(?:th|tt|bs)\s*$", "", match.group(1), flags=re.IGNORECASE))
			if name and name not in doctors:
				doctors.append(name)
	return doctors


def field_from_text(text: str, labels: tuple[str, ...], next_labels: tuple[str, ...]) -> str | None:
	label_pattern = "|".join(re.escape(label) for label in labels)
	stop_pattern = "|".join(re.escape(label) for label in next_labels)
	match = re.search(rf"(?:{label_pattern})\s*:\s*(.*?)(?=\s+(?:{stop_pattern})\s*:?|\n|$)", text, re.IGNORECASE)
	return usable_value(match.group(1)) if match else None


def last_field_from_text(text: str, labels: tuple[str, ...], next_labels: tuple[str, ...]) -> str | None:
	label_pattern = "|".join(re.escape(label) for label in labels)
	stop_pattern = "|".join(re.escape(label) for label in next_labels)
	matches = re.finditer(rf"(?:{label_pattern})\s*:\s*(.*?)(?=\s+(?:{stop_pattern})\s*:?|\n|$)", text, re.IGNORECASE)
	values = [usable_value(match.group(1)) for match in matches]
	return next((value for value in reversed(values) if value), None)


def value_near_label(lines: list[str], labels: tuple[str, ...], lookback: int = 3) -> str | None:
	label_pattern = re.compile("|".join(re.escape(label) for label in labels), re.IGNORECASE)
	other_label_pattern = re.compile(
		r"^(?:Mã|Ma|Số|So|Ngày|Ngay|Họ|Ho|Năm|Nam|Giới|Gioi|Địa|Dia|Chẩn|Chan|Căn|Can|Tuổi|Tuoi|Điện|Dien|Hướng|Huong|Lời|Loi)\b.*[:：]?\s*$",
		re.IGNORECASE,
	)
	for index, line in enumerate(lines):
		match = label_pattern.search(line)
		if not match:
			continue
		inline = usable_value(line[match.end() :])
		if inline:
			return usable_value(inline.rsplit(":", 1)[-1])
		for offset in range(1, lookback + 1):
			for candidate_index in (index + offset, index - offset):
				if 0 <= candidate_index < len(lines):
					candidate = usable_value(lines[candidate_index])
					if candidate and ":" in candidate:
						candidate = usable_value(candidate.rsplit(":", 1)[-1])
					if candidate and not label_pattern.search(candidate) and not other_label_pattern.match(candidate) and not re.fullmatch(r"\(?\s*(?:nam|nữ|nu)\s*\)?", candidate, re.IGNORECASE) and not re.fullmatch(r"\d+[.\/\-\d ]*", candidate) and not re.search(r"\b(?:tuổi|tuoi|tháng|thang)\b", candidate, re.IGNORECASE):
						return candidate
	return None


def value_before_label(lines: list[str], labels: tuple[str, ...], lookback: int = 4) -> str | None:
	label_pattern = re.compile("|".join(re.escape(label) for label in labels), re.IGNORECASE)
	for index, line in enumerate(lines):
		match = label_pattern.search(line)
		if not match:
			continue
		inline = usable_value(line[match.end() :])
		if inline:
			return inline.rsplit(":", 1)[-1].strip()
		for offset in range(1, lookback + 1):
			candidate_index = index - offset
			if candidate_index < 0:
				break
			candidate = usable_value(lines[candidate_index])
			if candidate and not re.search(r"\b(?:tuổi|tuoi|tuối|số|so|địa|dia)\b", candidate, re.IGNORECASE):
				return candidate
	return None


def year_near_label(lines: list[str]) -> str | None:
	for index, line in enumerate(lines):
		if re.search(r"Năm sinh|Nam sinh", line, re.IGNORECASE):
			for candidate in lines[max(0, index - 2) : min(len(lines), index + 3)]:
				if re.fullmatch(r"\s*(?:19|20)\d{2}\s*", candidate):
					return candidate.strip()
	return None


def diagnosis_near_label(lines: list[str]) -> str | None:
	label_pattern = re.compile(r"Chan doan|Chan đoán|Chẩn đoán|Chẩn doán|Căn bệnh|Can bénh", re.IGNORECASE)
	for index, line in enumerate(lines):
		if not label_pattern.search(line):
			continue
		parts = []
		for candidate in lines[index + 1 : index + 4]:
			if re.match(r"^\s*(?:II|III)\.", candidate, re.IGNORECASE) or re.search(r"ĐƠN THUỐC|DON THUOC", candidate, re.IGNORECASE):
				break
			if not re.search(r"^(?:Số [Il]ượng|So luong|Điều trị|Dieu tri)", candidate, re.IGNORECASE):
				parts.append(candidate)
		if parts:
			return normalize_text(" ".join(parts))
	return value_before_label(lines, ("Chan doan", "Chẩn đoán", "Chẩn doán", "Căn bệnh", "Can bénh"), lookback=3)


def legacy_medicines(lines: list[str]) -> list[dict[str, str]]:
	medicines: list[dict[str, str]] = []
	item_marker = re.compile(r"^\s*\d+\s*(?:[-.)])?\s*$")
	number = re.compile(r"^\s*\d+(?:\.\d+)?\s*$")
	for index, line in enumerate(lines):
		if not item_marker.match(line):
			continue
		name = None
		for candidate_index in range(index - 1, max(-1, index - 5), -1):
			candidate = normalize_text(lines[candidate_index])
			if candidate and not number.match(candidate) and ":" not in candidate and not is_non_medicine_label(candidate) and len(candidate) >= 4 and re.search(r"[A-Za-zÀ-ỹĐđ]", candidate):
				name = candidate
				break
		if not name:
			continue
		quantity = next((normalize_text(lines[candidate_index]) for candidate_index in range(index - 1, max(-1, index - 5), -1) if number.match(lines[candidate_index])), None)
		medicine = {"ten": name}
		if quantity:
			medicine["so_luong"] = quantity
		instruction_parts = []
		for instruction_line in lines[index + 1 : min(len(lines), index + 6)]:
			if item_marker.match(instruction_line):
				break
			if re.search(r"Uống|Uong|Truyền|Truyen|Iruyền|Iruyen|Sáng|Sang|Chiều|Chieu|Tối|Toi", instruction_line, re.IGNORECASE):
				instruction_parts.append(normalize_text(instruction_line))
		if instruction_parts:
			medicine["huong_dan"] = normalize_text(" ".join(instruction_parts))
		medicines.append(medicine)
	return medicines


def oncology_medicines(lines: list[str]) -> list[dict[str, str]]:
	medicines: list[dict[str, str]] = []
	inline = re.compile(r"^\s*\d+\s*[-.)]\s*(.+?)\s+(?:Số lượng|So luong)\s*:\s*(\d+(?:\.\d+)?)\s*$", re.IGNORECASE)
	for index, line in enumerate(lines):
		match = inline.match(normalize_text(line))
		if not match:
			continue
		name = re.sub(r"\.{2,}.*$", "", match.group(1)).strip(" .")
		name = re.sub(r"\bL[oọ]\s*$", "", name, flags=re.IGNORECASE).strip(" .")
		medicine: dict[str, str] = {"ten": name, "so_luong": match.group(2)}
		for instruction in lines[index + 1 : min(len(lines), index + 4)]:
			instruction = normalize_text(instruction)
			if re.search(r"Sáng|Sang|Trưa|Trua|Chiều|Chieu|Tối|Toi|Uống|Uong|Truyền|Truyen|Iruyền", instruction, re.IGNORECASE):
				medicine["huong_dan"] = instruction
				break
		medicines.append(medicine)
	return medicines or legacy_medicines(lines)


def is_non_medicine_label(line: str) -> bool:
	return bool(re.match(r"^\s*(?:SL|Số|So|Mạch|Mach|Năm|Nam|Tuổi|Tuoi|Ngày|Ngay|Địa|Dia|Điện|Dien|Chẩn|Chan|Căn|Can|Hướng|Huong|Lời|Loi|Uống|Uong|Sáng|Sang|Chiều|Chieu|Tối|Toi|Viên|Vien|Gói|Goi)\b", line, re.IGNORECASE))


def is_quantity_only(line: str) -> bool:
	return bool(re.fullmatch(r"\s*\d*\s*(?:vien|viên|goi|gói|ong|ống|chai)\s*", line, re.IGNORECASE))


def outpatient_medicines(lines: list[str]) -> list[dict[str, str]]:
	medicines: list[dict[str, str]] = []
	quantity_units = r"mg|ml|mcg|g|viên|vien|gói|goi|ống|Óng|ong|chai"
	quantity_value = re.compile(rf"^\s*\d+(?:\.\d+)?\s+(?:{quantity_units})\s*$", re.IGNORECASE)
	inline_medicine = re.compile(rf"^\s*(?:\d+\s*[-.)]?\s*)?(.+?)\s+(?:Số lượng|SL)\s*:?\s*(\d+(?:\.\d+)?\s+(?:{quantity_units}))\s*$", re.IGNORECASE)
	start = next((index for index, line in enumerate(lines) if re.search(r"Điều trị|Dieu tri", line, re.IGNORECASE)), 0)
	end = next((index for index in range(start + 1, len(lines)) if re.search(r"Ngày tái khám|Ngay tai kham|Lời dặn|Loi dan", lines[index], re.IGNORECASE)), len(lines))
	for line_index, line in enumerate(lines[start:end], start=start):
		match = inline_medicine.match(normalize_text(line))
		if match:
			medicine = {"ten": normalize_text(match.group(1)), "so_luong": normalize_vietnamese(match.group(2)) or normalize_text(match.group(2))}
			for instruction_line in lines[line_index + 1 : min(end, line_index + 3)]:
				instruction = normalize_text(instruction_line)
				if re.match(r"^(?:Uống|Uong|Hướng dẫn|Huong dan|Hòa|Hoa|Pha)", instruction, re.IGNORECASE):
					medicine["huong_dan"] = re.sub(r"^(?:Hướng dẫn|Huong dan)\s*:?\s*", "", instruction, flags=re.IGNORECASE)
					break
			medicines.append(medicine)
	if medicines:
		return medicines
	medicine_line = re.compile(r"^(?=.*[A-Za-zÀ-ỹĐđ])(?=.*(?:\d|\(|[A-ZĐÀ-Ỹ]{3,}))[A-Za-zÀ-ỹĐđ0-9() .-]{4,}$", re.IGNORECASE)
	ignored = re.compile(r"^(?:Số|So|Điều|Dieu|Uống|Uong|Sáng|Sang|Chiều|Chieu|Tối|Toi|Ngày|Ngay|Viên|Vien|Gói|Goi|phút|giờ|x\s*\d)", re.IGNORECASE)
	quantities = [(start + index, normalize_text(line)) for index, line in enumerate(lines[start:end]) if quantity_value.match(normalize_text(line))]
	for relative_index, line in enumerate(lines[start:end]):
		candidate = normalize_text(line)
		if not medicine_line.match(candidate) or ignored.match(candidate) or is_non_medicine_label(candidate) or is_quantity_only(candidate) or re.search(r"\b(?:trước ăn|sau ăn|lần ?ngày|buổi sáng|buổi tối|Tháng)\b", candidate, re.IGNORECASE):
			continue
		if re.search(r"(?:Vp|mmHg|SĐT|Zalo|Bác sĩ|BS\.)", candidate, re.IGNORECASE):
			continue
		absolute_index = start + relative_index
		nearby = min(quantities, key=lambda item: abs(item[0] - absolute_index), default=None)
		if nearby is not None and abs(nearby[0] - absolute_index) <= 5 and not any(existing["ten"] == candidate for existing in medicines):
			medicines.append({"ten": candidate, "so_luong": nearby[1]})
	return medicines


def nearby_quantity(lines: list[str], index: int) -> str | None:
	for distance in range(1, 5):
		for candidate_index in (index - distance, index + distance):
			if 0 <= candidate_index < len(lines):
				match = re.search(r"\b(?:SL|Số lượng)\s*:\s*(.+)$", lines[candidate_index], re.IGNORECASE)
				if match:
					return usable_value(match.group(1))
	return None


def extract_medicines(lines: list[str]) -> list[dict[str, str]]:
	is_oncology = any(re.search(r"Căn bệnh|Can benh|Can bénh|Số lưu trữ|So luu tru|BỆNH VIỆN UNG BƯỚU|BENH VIEN UNG BUOU", line, re.IGNORECASE) for line in lines)
	if is_oncology:
		return oncology_medicines(lines)
	if any(re.search(r"Điều trị|Dieu tri|ĐƠN THUỐC|DON THUOC|BON THUOC", line, re.IGNORECASE) for line in lines):
		return outpatient_medicines(lines)
	medicines = []
	medicine_pattern = re.compile(r"^\s*(?:\d+[.)]?\s+)?(.+?)(?:\s+SL\s*:\s*(.+))?$", re.IGNORECASE)
	for index, line in enumerate(lines):
		match = medicine_pattern.match(line)
		split_dosage = index + 1 < len(lines) and bool(re.fullmatch(r"(?:mg|ml|mcg|g)", lines[index + 1], re.IGNORECASE))
		if not match or (not re.search(r"\b(?:mg|ml|mcg|g|vien|viên|goi|gói|ong|ống|chai)\b", line, re.IGNORECASE) and not split_dosage) or is_quantity_only(match.group(1)) or is_non_medicine_label(match.group(1)):
			continue
		name = normalize_text(match.group(1))
		if split_dosage:
			name = f"{name} {lines[index + 1]}"
		medicine = {"ten": name}
		quantity = usable_value(match.group(2)) or nearby_quantity(lines, index)
		if quantity:
			medicine["so_luong"] = quantity
		medicines.append(medicine)
	return medicines


def extract_prescription(lines: list[str], image_path: Path) -> dict[str, Any]:
	raw_text = "\n".join(lines)
	field_stops = ("Mã người bệnh", "Số hồ sơ", "Ngày kê", "Họ và tên", "Họ tên người bệnh", "Ho tên người bệnh", "Năm sinh", "Nam sinh", "Giới tính", "Tuổi", "Địa chỉ", "Điện thoại", "Chẩn đoán", "Can bénh", "Điều trị")
	return {
		"tep_anh": str(image_path),
		"ten_benh_vien": normalize_vietnamese(extract_hospital(lines)),
		"bac_si": [normalize_vietnamese(name) or name for name in extract_doctors(lines)],
		"ma_y_te": find_pattern(raw_text, r"Mã YT\s*:\s*([\d.]+)"),
		"so_luu_tru": find_pattern(raw_text, r"Số lưu trữ\s*:\s*([\d/]+)"),
		"ma_don": find_pattern(raw_text, r"\b(DT[-\s]?\d{6}[-\s]?\d{3})\b") or find_pattern(raw_text, r"(?:BỆNH\s+VIỆN|BỆNH\s+VIEN|BENH\s+VIEN)[^\n]*?Số\s*:\s*(\d{7})"),
		"ma_nguoi_benh": find_pattern(raw_text, r"\b(?:Mã người bệnh|Ma nguoi benh|ã người bệnh)\s*:\s*(BN[-\s]?\d{5,})\b") or find_pattern(raw_text, r"\b(BN[-\s]?\d{5,})\b"),
		"so_ho_so": find_pattern(raw_text, r"\b(HS[-\s]?\d{6,})\b"),
		"ngay_ke": find_date(raw_text),
		"ho_ten": clean_name(field_from_text(raw_text, ("Họ và tên", "Họ tên", "Họ tên người bệnh", "Ho tên người bệnh", "Họ vatén"), field_stops) or value_before_label(lines, ("Ho va ten", "Họ và tên", "Họ tên", "Họ tên người bệnh", "Ho tên người bệnh", "Họ vatén"))),
		"nam_sinh": field_from_text(raw_text, ("Năm sinh", "Nam sinh"), field_stops + ("Giới tinh",)) or year_near_label(lines),
		"gioi_tinh": field_from_text(raw_text, ("Giới tính", "Gioi tinh", "Giới tinh"), field_stops) or find_pattern(raw_text, r"\((Nam|Nữ|Nu)\)" ) or next((line for line in lines if re.fullmatch(r"\s*(?:Nam|Nữ|Nu)\s*", line, re.IGNORECASE)), None),
		"dia_chi": clean_address(last_field_from_text(raw_text, ("Địa chỉ", "Địa chi", "Dia chi", "Dia chỉ"), field_stops) or value_near_label(lines, ("Dia chi", "Dia chỉ", "Địa chỉ", "Địa chi"))),
		"chan_doan": clean_diagnosis(field_from_text(raw_text, ("Chẩn đoán", "Chẩn doán", "Chan doan", "Chan đoán", "Căn bệnh", "Can bénh"), ("Điều trị", "II. ĐƠN THUỐC", "II. ĐƠN THUỐC")) or diagnosis_near_label(lines)),
		"thuoc": extract_medicines(lines),
		"van_ban_ocr": raw_text,
	}