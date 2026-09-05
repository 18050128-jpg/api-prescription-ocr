from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_roles
from app.schemas.resource import MedicineResponse, MedicineUpdate, PrescriptionRecord
from app.services.resource_service import list_medicines, list_prescriptions, update_medicine


router = APIRouter(tags=["database"])


@router.get("/prescriptions", response_model=list[PrescriptionRecord])
def get_prescriptions(user: dict[str, Any] = Depends(require_roles("doctor", "user"))) -> list[PrescriptionRecord]:
	return list_prescriptions(user)


@router.get("/medicines", response_model=list[MedicineResponse])
def get_medicines(_: dict[str, Any] = Depends(require_roles("doctor", "pharmacist"))) -> list[MedicineResponse]:
	return list_medicines()


@router.patch("/medicines/{medicine_id}", response_model=MedicineResponse)
def edit_medicine(medicine_id: str, payload: MedicineUpdate, _: dict[str, Any] = Depends(require_roles("doctor", "pharmacist"))) -> MedicineResponse:
	medicine = update_medicine(medicine_id, payload)
	if not medicine:
		raise HTTPException(status_code=404, detail="Khong tim thay thuoc.")
	return medicine
