import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Esquema para la petición de inicio de sesión."""
    email: str = Field(..., description="Correo electrónico del usuario")
    password: str = Field(..., min_length=12, max_length=128, description="Contraseña de la cuenta")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Formato de correo electrónico no válido")
        return v


class UserPublicResponse(BaseModel):
    """Datos públicos no sensibles de un usuario."""
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """
    Respuesta retornada tras autenticación exitosa o en /auth/me.
    Incluye los datos públicos del usuario y el token CSRF opaco que el frontend
    debe mantener exclusivamente en memoria RAM para peticiones mutables.
    """
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    csrf_token: str

    model_config = ConfigDict(from_attributes=True)

