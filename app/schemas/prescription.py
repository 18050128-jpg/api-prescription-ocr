from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Medicine(BaseModel):
	ten: str
	so_luong: str | None = None
	huong_dan: str | None = None
	reminder_times: list[str] = Field(default_factory=list)


class MedicineScheduleUpdate(BaseModel):
	reminder_times: list[str] = Field(default_factory=list)


class OcrInfo(BaseModel):
	so_doan_van_ban: int
	do_tin_cay_trung_binh: float = Field(ge=0, le=1)
	engine: str = "tesseract"


class PrescriptionResponse(BaseModel):
	id: str | None = None
	tep_anh: str
	ten_benh_vien: str | None = None
	bac_si: list[str] = Field(default_factory=list)
	ma_y_te: str | None = None
	so_luu_tru: str | None = None
	ma_don: str | None = None
	ma_nguoi_benh: str | None = None
	so_ho_so: str | None = None
	ngay_ke: str | None = None
	ho_ten: str | None = None
	nam_sinh: str | None = None
	gioi_tinh: str | None = None
	dia_chi: str | None = None
	chan_doan: str | None = None
	thuoc: list[Medicine]
	van_ban_ocr: str
	ocr: OcrInfo

	@classmethod
	def from_result(cls, result: dict[str, Any]) -> "PrescriptionResponse":
		return cls.model_validate(result)