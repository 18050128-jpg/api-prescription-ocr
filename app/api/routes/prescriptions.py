from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import require_roles
from app.schemas.prescription import Medicine, MedicineScheduleUpdate, MedicineUseRequest, PrescriptionResponse
from app.schemas.resource import PrescriptionRecord
from app.services.image_service import store_uploaded_image
from app.services.prescription_service import process_prescription
from app.services.drug_info_service import enrich_medicines
from app.services.resource_service import consume_medicine, duplicate_medicine_warnings, prescription_image_path, save_prescription, update_medicine_schedule


router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.get("/{prescription_id}/image")
def get_prescription_image(
	prescription_id: str,
	user: dict[str, Any] = Depends(require_roles("admin", "doctor", "pharmacist", "user")),
) -> FileResponse:
	image_path = prescription_image_path(prescription_id, user)
	if image_path is None:
		raise HTTPException(status_code=404, detail="Khong tim thay anh toa thuoc.")
	return FileResponse(image_path)


@router.post("/ocr", response_model=PrescriptionResponse)
async def recognize_prescription(
	file: UploadFile = File(...),
	persist: bool = True,
	user: dict[str, Any] = Depends(require_roles("doctor", "user")),
) -> PrescriptionResponse:
	if not file.content_type or not file.content_type.startswith("image/"):
		raise HTTPException(status_code=400, detail="File phai la anh toa thuoc.")

	content = await file.read()
	try:
		stored_path, stored_name = store_uploaded_image(content, file.filename or "prescription.png")
		result = process_prescription(stored_path.read_bytes(), stored_name)
		result.tep_anh = stored_name
		enriched = enrich_medicines([medicine.model_dump() for medicine in result.thuoc])
		result.thuoc = [Medicine.model_validate(medicine) for medicine in enriched]
		result.warnings = duplicate_medicine_warnings([medicine.model_dump() for medicine in result.thuoc])
		if persist:
			saved = save_prescription(user["id"], result.model_dump(mode="json"))
			result.id = saved.id
		return result
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("", response_model=PrescriptionRecord, status_code=201)
def create_prescription(
	payload: PrescriptionResponse,
	user: dict[str, Any] = Depends(require_roles("doctor", "user")),
) -> PrescriptionRecord:
	return save_prescription(user["id"], payload.model_dump(mode="json"))


@router.post("/{prescription_id}/medicines/{medicine_index}/use", response_model=PrescriptionResponse)
def use_prescription_medicine(
	prescription_id: str,
	medicine_index: int,
	payload: MedicineUseRequest,
	user: dict[str, Any] = Depends(require_roles("doctor", "user")),
) -> PrescriptionResponse:
	try:
		prescription = consume_medicine(
			prescription_id,
			medicine_index,
			user,
			payload.used_quantity,
		)
		return PrescriptionResponse.model_validate(prescription.data)
	except (KeyError, IndexError) as error:
		raise HTTPException(status_code=404, detail=str(error)) from error
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error


@router.patch("/{prescription_id}/medicines/{medicine_index}/schedule", response_model=PrescriptionResponse)
def update_prescription_medicine_schedule(
	prescription_id: str,
	medicine_index: int,
	payload: MedicineScheduleUpdate,
	user: dict[str, Any] = Depends(require_roles("doctor", "user")),
) -> PrescriptionResponse:
	try:
		prescription = update_medicine_schedule(prescription_id, medicine_index, payload, user)
		return PrescriptionResponse.model_validate(prescription.data)
	except (KeyError, IndexError) as error:
		raise HTTPException(status_code=404, detail=str(error)) from error
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error