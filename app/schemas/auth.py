from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
	username: str = Field(min_length=3, max_length=50)
	password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
	access_token: str
	token_type: str = "bearer"
	username: str | None = None
	role: str | None = None


class ChangePasswordRequest(BaseModel):
	current_password: str = Field(min_length=8, max_length=128)
	new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordRequest(BaseModel):
	username: str = Field(min_length=3, max_length=50)
	email: str = Field(min_length=5, max_length=254)
	new_password: str = Field(min_length=8, max_length=128)
