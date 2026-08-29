import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    phone_number: str | None = None
    password: str = Field(min_length=12, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"\+[1-9]\d{7,14}", value) is None:
            raise ValueError("Phone number must use E.164 format")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    phone_number: str | None
    first_name: str
    last_name: str
    is_active: bool
    plan_status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    roles: list[str] = Field(validation_alias="role_names")
    permissions: list[str] = Field(validation_alias="permission_names")
