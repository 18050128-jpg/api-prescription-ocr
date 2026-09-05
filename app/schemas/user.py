from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["admin", "doctor", "pharmacist", "user"]


class UserCreate(BaseModel):
	username: str = Field(min_length=3, max_length=50)
	email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
	full_name: str | None = Field(default=None, max_length=100)
	password: str = Field(min_length=8, max_length=128)
	role: UserRole = "user"


class UserRoleUpdate(BaseModel):
	role: UserRole


class PasswordReset(BaseModel):
	password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: str
	username: str
	email: str
	full_name: str | None = None
	role: UserRole
	is_active: bool
	created_at: datetime
	updated_at: datetime
