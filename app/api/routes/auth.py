from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import authenticate_user, create_user, issue_token, list_users


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: Request) -> TokenResponse:
	content_type = request.headers.get("content-type", "")

	try:
		if "application/x-www-form-urlencoded" in content_type:
			form_data = await request.form()
			username_value = str(form_data.get("username", "")).strip()
			password_value = str(form_data.get("password", "")).strip()
		else:
			payload = await request.json()
			username_value = str(payload.get("username", "")).strip()
			password_value = str(payload.get("password", "")).strip()
	except Exception:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username va password la bat buoc.")

	if not username_value or not password_value:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username va password la bat buoc.")

	user = authenticate_user(username_value, password_value)
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai username hoac password.")
	return TokenResponse(
		access_token=issue_token(user),
		username=user["username"],
		role=user["role"],
	)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate) -> TokenResponse:
	try:
		user = create_user(payload)
		return TokenResponse(
			access_token=issue_token(user.model_dump()),
			username=user.username,
			role=user.role,
		)
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/bootstrap", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: UserCreate) -> TokenResponse:
	if list_users():
		raise HTTPException(status_code=409, detail="Admin da duoc khoi tao.")
	try:
		user = create_user(payload.model_copy(update={"role": "admin"}))
		return TokenResponse(
			access_token=issue_token(user.model_dump()),
			username=user.username,
			role=user.role,
		)
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error
