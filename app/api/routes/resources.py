from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_roles
from app.schemas.resource import MedicineResponse, MedicineUpdate, PrescriptionPage, PrescriptionRecord
from app.services.resource_service import list_medicines, list_prescriptions, list_prescriptions_page, update_medicine


router = APIRouter(tags=["database"])


@router.get("/prescriptions", response_model=list[PrescriptionRecord])
def get_prescriptions(user: dict[str, Any] = Depends(require_roles("doctor", "user"))) -> list[PrescriptionRecord]:
	return list_prescriptions(user)


@router.get("/prescriptions/page", response_model=PrescriptionPage)
def get_prescriptions_page(
	page: int = Query(1, ge=1),
	page_size: int = Query(10, ge=1, le=100),
	search: str = Query("", max_length=120),
	status: str = Query("all", pattern="^(all|success|review|unknown)$"),
	sort: str = Query("newest", pattern="^(newest|oldest|patient|confidence)$"),
	user: dict[str, Any] = Depends(require_roles("doctor", "user")),
) -> PrescriptionPage:
	return list_prescriptions_page(user, page, page_size, search, status, sort)


@router.get("/medicines", response_model=list[MedicineResponse])
def get_medicines(_: dict[str, Any] = Depends(require_roles("doctor", "pharmacist"))) -> list[MedicineResponse]:
	return list_medicines()


@router.patch("/medicines/{medicine_id}", response_model=MedicineResponse)
def edit_medicine(medicine_id: str, payload: MedicineUpdate, _: dict[str, Any] = Depends(require_roles("doctor", "pharmacist"))) -> MedicineResponse:
	medicine = update_medicine(medicine_id, payload)
	if not medicine:
		raise HTTPException(status_code=404, detail="Khong tim thay thuoc.")
	return medicine
