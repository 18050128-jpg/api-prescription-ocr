from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import require_roles
from app.schemas.user import PasswordReset, UserCreate, UserResponse, UserRoleUpdate
from app.services.user_service import (
	create_user,
	delete_user,
	list_users,
	reset_user_password,
	toggle_user_active,
	update_user_role,
)
from app.services.admin_service import get_admin_stats, get_audit_logs, record_audit


router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_managed_user(payload: UserCreate, admin: dict = Depends(require_roles("admin"))) -> UserResponse:
	try:
		result = create_user(payload)
		record_audit(admin, "user_created", result.id, f"role={result.role}")
		return result
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[UserResponse])
def get_users(_: dict = Depends(require_roles("admin"))) -> list[UserResponse]:
	return list_users()


@admin_router.get("/users", response_model=list[UserResponse])
def get_admin_users(_: dict = Depends(require_roles("admin"))) -> list[UserResponse]:
	return list_users()


@admin_router.get("/stats")
def get_statistics(_: dict = Depends(require_roles("admin"))) -> dict:
	return get_admin_stats()


@admin_router.get("/audit-logs")
def get_logs(_: dict = Depends(require_roles("admin"))) -> list[dict]:
	return get_audit_logs()


@admin_router.post("/users/create-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: UserCreate, admin: dict = Depends(require_roles("admin"))) -> UserResponse:
	try:
		result = create_user(payload.model_copy(update={"role": "admin"}))
		record_audit(admin, "admin_created", result.id, f"username={result.username}")
		return result
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error


@admin_router.put("/users/{user_id}/role", response_model=UserResponse)
def change_user_role(
	user_id: str,
	payload: UserRoleUpdate,
	admin: dict = Depends(require_roles("admin")),
) -> UserResponse:
	if user_id == admin.get("id"):
		raise HTTPException(status_code=400, detail="Ban khong the tu doi role cua minh.")
	try:
		result = update_user_role(user_id, payload.role)
		record_audit(admin, "role_changed", user_id, f"role={payload.role}")
		return result
	except KeyError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error


@admin_router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
def change_user_active(
	user_id: str,
	admin: dict = Depends(require_roles("admin")),
) -> UserResponse:
	if user_id == admin.get("id"):
		raise HTTPException(status_code=400, detail="Ban khong the tu khoa hoac mo khoa minh.")
	try:
		result = toggle_user_active(user_id)
		record_audit(admin, "user_status_changed", user_id, f"is_active={result.is_active}")
		return result
	except KeyError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error


@admin_router.put("/users/{user_id}/reset-password", response_model=UserResponse)
def change_user_password(
	user_id: str,
	payload: PasswordReset,
	_: dict = Depends(require_roles("admin")),
) -> UserResponse:
	try:
		result = reset_user_password(user_id, payload.password)
		record_audit(_, "password_reset", user_id)
		return result
	except KeyError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error
	except ValueError as error:
		raise HTTPException(status_code=400, detail=str(error)) from error


@admin_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
	user_id: str,
	admin: dict = Depends(require_roles("admin")),
) -> Response:
	if user_id == admin.get("id"):
		raise HTTPException(status_code=400, detail="Ban khong the tu xoa minh.")
	try:
		delete_user(user_id)
		record_audit(admin, "user_deleted", user_id)
		return Response(status_code=status.HTTP_204_NO_CONTENT)
	except KeyError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error


# backward compatibility: old routes
@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
def legacy_change_user_role(
	user_id: str,
	payload: UserRoleUpdate,
	admin: dict = Depends(require_roles("admin")),
) -> UserResponse:
	return change_user_role(user_id, payload, admin)


@router.put("/admin/users/{user_id}/toggle-active", response_model=UserResponse)
def legacy_change_user_active(
	user_id: str,
	admin: dict = Depends(require_roles("admin")),
) -> UserResponse:
	return change_user_active(user_id, admin)


@router.put("/admin/users/{user_id}/reset-password", response_model=UserResponse)
def legacy_change_user_password(
	user_id: str,
	payload: PasswordReset,
	_: dict = Depends(require_roles("admin")),
) -> UserResponse:
	return change_user_password(user_id, payload, _)


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def legacy_remove_user(
	user_id: str,
	admin: dict = Depends(require_roles("admin")),
) -> Response:
	return remove_user(user_id, admin)
