import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.auth import UserPublicResponse


class UserCreateRequest(BaseModel):
    """Esquema para la creación de un nuevo usuario por parte de un administrador."""
    email: str = Field(..., max_length=255, description="Correo electrónico único del usuario")
    password: str = Field(..., min_length=12, max_length=128, description="Contraseña inicial del usuario")
    confirm_password: Optional[str] = Field(None, min_length=12, max_length=128, description="Confirmación de contraseña")
    role: str = Field(default="user", pattern="^(user|admin)$", description="Rol asignado ('user' o 'admin')")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Formato de correo electrónico no válido")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserCreateRequest":
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class UserUpdateRequest(BaseModel):
    """Esquema para la edición parcial de los datos de un usuario."""
    email: Optional[str] = Field(None, max_length=255, description="Nuevo correo electrónico")
    role: Optional[str] = Field(None, pattern="^(user|admin)$", description="Nuevo rol ('user' o 'admin')")
    is_active: Optional[bool] = Field(None, description="Estado de activación de la cuenta")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v or "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Formato de correo electrónico no válido")
            return v
        return v


class UserChangePasswordRequest(BaseModel):
    """Esquema para el restablecimiento de contraseña de un usuario."""
    password: str = Field(..., min_length=12, max_length=128, description="Nueva contraseña")
    confirm_password: Optional[str] = Field(None, min_length=12, max_length=128, description="Confirmación de la nueva contraseña")

    @model_validator(mode="after")
    def check_passwords_match(self) -> "UserChangePasswordRequest":
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class UserListResponse(BaseModel):
    """Listado paginado o completo de usuarios retornados al administrador."""
    users: list[UserPublicResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
