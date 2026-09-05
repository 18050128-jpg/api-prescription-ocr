from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.user import UserCreate, UserResponse


USER_DB_PATH = Path(__file__).resolve().parent.parent / "database" / "User.json"
_tokens: dict[str, str] = {}


def _read_users() -> list[dict[str, Any]]:
	USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
	if not USER_DB_PATH.exists() or not USER_DB_PATH.read_text(encoding="utf-8").strip():
		return []
	data = json.loads(USER_DB_PATH.read_text(encoding="utf-8"))
	if not isinstance(data, list):
		raise ValueError("User.json phai chua mot danh sach user.")
	return data


def _write_users(users: list[dict[str, Any]]) -> None:
	USER_DB_PATH.write_text(json.dumps(users, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hash_password(password: str, salt: str | None = None) -> str:
	salt = salt or secrets.token_hex(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
	return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def create_user(payload: UserCreate) -> UserResponse:
	users = _read_users()
	username = payload.username.strip()
	email = str(payload.email).strip().lower()
	full_name = payload.full_name.strip() if payload.full_name else None
	if any(user.get("username", "").lower() == username.lower() for user in users):
		raise ValueError("Username da ton tai.")
	if any(user.get("email", "").lower() == email for user in users):
		raise ValueError("Email da ton tai.")
	now = datetime.now(timezone.utc)
	user = {
		"id": str(uuid.uuid4()),
		"username": username,
		"email": email,
		"full_name": full_name,
		"password_hash": _hash_password(payload.password),
		"role": payload.role,
		"is_active": True,
		"created_at": now.isoformat(),
		"updated_at": now.isoformat(),
	}
	users.append(user)
	_write_users(users)
	return UserResponse.model_validate(user)


def list_users() -> list[UserResponse]:
	return [UserResponse.model_validate(user) for user in _read_users()]


def update_user_role(user_id: str, role: str) -> UserResponse:
	users = _read_users()
	user = next((item for item in users if item.get("id") == user_id), None)
	if not user:
		raise KeyError("Khong tim thay nguoi dung.")
	if role not in {"admin", "doctor", "user"}:
		raise ValueError("Role khong hop le.")
	user["role"] = role
	user["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write_users(users)
	return UserResponse.model_validate(user)


def toggle_user_active(user_id: str) -> UserResponse:
	users = _read_users()
	user = next((item for item in users if item.get("id") == user_id), None)
	if not user:
		raise KeyError("Khong tim thay nguoi dung.")
	user["is_active"] = not user.get("is_active", True)
	user["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write_users(users)
	return UserResponse.model_validate(user)


def reset_user_password(user_id: str, password: str) -> UserResponse:
	users = _read_users()
	user = next((item for item in users if item.get("id") == user_id), None)
	if not user:
		raise KeyError("Khong tim thay nguoi dung.")
	if len(password.strip()) < 8:
		raise ValueError("Mat khau moi phai co it nhat 8 ky tu.")
	user["password_hash"] = _hash_password(password)
	user["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write_users(users)
	return UserResponse.model_validate(user)


def change_password_for_user(user_id: str, current_password: str, new_password: str) -> None:
	users = _read_users()
	user = next((item for item in users if item.get("id") == user_id), None)
	if not user:
		raise KeyError("Khong tim thay nguoi dung.")
	if not _verify_password(current_password, user.get("password_hash", "")):
		raise ValueError("Mat khau hien tai khong dung.")
	if len(new_password.strip()) < 8:
		raise ValueError("Mat khau moi phai co it nhat 8 ky tu.")
	user["password_hash"] = _hash_password(new_password)
	user["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write_users(users)


def reset_password_by_identity(username: str, email: str, new_password: str) -> None:
	users = _read_users()
	normalized_username = username.strip().lower()
	normalized_email = email.strip().lower()
	user = next(
		(
			item
			for item in users
			if item.get("username", "").lower() == normalized_username
			and item.get("email", "").lower() == normalized_email
		),
		None,
	)
	if not user:
		raise ValueError("Username hoac email khong dung.")
	if len(new_password.strip()) < 8:
		raise ValueError("Mat khau moi phai co it nhat 8 ky tu.")
	user["password_hash"] = _hash_password(new_password)
	user["updated_at"] = datetime.now(timezone.utc).isoformat()
	_write_users(users)


def delete_user(user_id: str) -> None:
	users = _read_users()
	remaining_users = [user for user in users if user.get("id") != user_id]
	if len(remaining_users) == len(users):
		raise KeyError("Khong tim thay nguoi dung.")
	_write_users(remaining_users)
	for token, token_user_id in list(_tokens.items()):
		if token_user_id == user_id:
			del _tokens[token]


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
	user = next((item for item in _read_users() if item.get("username", "").lower() == username.lower()), None)
	if not user or not user.get("is_active") or not _verify_password(password, user.get("password_hash", "")):
		return None
	return user


def _verify_password(password: str, encoded: str) -> bool:
	try:
		algorithm, iterations, salt, expected = encoded.split("$", 3)
		if algorithm != "pbkdf2_sha256":
			return False
		actual = _hash_password(password, salt).split("$", 3)[3]
		return secrets.compare_digest(actual, expected) and iterations == "120000"
	except ValueError:
		return False


def issue_token(user: dict[str, Any]) -> str:
	token = secrets.token_urlsafe(32)
	_tokens[token] = user["id"]
	return token


def user_from_token(token: str) -> dict[str, Any] | None:
	user_id = _tokens.get(token)
	return next((user for user in _read_users() if user.get("id") == user_id), None) if user_id else None
