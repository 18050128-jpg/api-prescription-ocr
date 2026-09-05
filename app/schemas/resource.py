from datetime import datetime

from pydantic import BaseModel, Field


class MedicineUpdate(BaseModel):
	ten: str = Field(min_length=1)
	so_luong: str | None = None
	huong_dan: str | None = None


class MedicineResponse(MedicineUpdate):
	id: str
	prescription_id: str
	updated_at: datetime


class PrescriptionRecord(BaseModel):
	id: str
	owner_id: str
	tep_anh: str
	created_at: datetime
	data: dict
