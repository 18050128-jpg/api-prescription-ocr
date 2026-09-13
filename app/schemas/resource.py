from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MedicineUpdate(BaseModel):
	ten: str = Field(min_length=1)
	lieu_luong: str | None = None
	so_luong: str | None = None
	huong_dan: str | None = None
	drug_info: dict[str, Any] | None = None


class MedicineResponse(MedicineUpdate):
	id: str
	medicine_id: str | None = None
	prescription_id: str | None = None
	prescription_ids: list[str] = Field(default_factory=list)
	updated_at: datetime


class PrescriptionRecord(BaseModel):
	id: str
	owner_id: str
	tep_anh: str
	created_at: datetime
	data: dict


class PrescriptionPage(BaseModel):
	items: list[PrescriptionRecord]
	page: int
	page_size: int
	total: int
	total_pages: int
	summary: dict[str, int] = Field(default_factory=dict)
