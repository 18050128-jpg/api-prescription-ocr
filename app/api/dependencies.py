from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.user_service import user_from_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict[str, Any]:
	if not credentials or credentials.scheme.lower() != "bearer":
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Can dang nhap.")
	user = user_from_token(credentials.credentials)
	if not user:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token khong hop le.")
	return user


def require_roles(*roles: str) -> Callable[..., dict[str, Any]]:
	def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
		if user.get("role") not in roles:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ban khong co quyen.")
		return user
	return dependency
