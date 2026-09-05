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


router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_managed_user(payload: UserCreate, _: dict = Depends(require_roles("admin"))) -> UserResponse:
	try:
		return create_user(payload)
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("", response_model=list[UserResponse])
def get_users(_: dict = Depends(require_roles("admin"))) -> list[UserResponse]:
	return list_users()


@admin_router.get("/users", response_model=list[UserResponse])
def get_admin_users(_: dict = Depends(require_roles("admin"))) -> list[UserResponse]:
	return list_users()


@admin_router.post("/users/create-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: UserCreate, _: dict = Depends(require_roles("admin"))) -> UserResponse:
	try:
		return create_user(payload.model_copy(update={"role": "admin"}))
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
		return update_user_role(user_id, payload.role)
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
		return toggle_user_active(user_id)
	except KeyError as error:
		raise HTTPException(status_code=404, detail=str(error)) from error


@admin_router.put("/users/{user_id}/reset-password", response_model=UserResponse)
def change_user_password(
	user_id: str,
	payload: PasswordReset,
	_: dict = Depends(require_roles("admin")),
) -> UserResponse:
	try:
		return reset_user_password(user_id, payload.password)
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
