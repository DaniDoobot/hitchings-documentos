from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.security import verify_csrf_token
from app.db.session import get_db
from app.models.session import Session
from app.models.user import User
from app.services.auth_service import auth_service


def get_current_session(
    request: Request,
    db: DbSession = Depends(get_db),
) -> Session:
    """
    Extrae la cookie HttpOnly de sesión, busca la sesión activa en base de datos
    y valida que no haya expirado. Si es inválida o no existe, aborta con HTTP 401.
    """
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Inicie sesión para continuar.",
        )

    session_entry = auth_service.get_session_by_token(db, session_token)
    if not session_entry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o expirada. Inicie sesión nuevamente.",
        )

    return session_entry


def get_current_user(
    session_entry: Session = Depends(get_current_session),
    db: DbSession = Depends(get_db),
) -> User:
    """
    Retorna el usuario asociado a la sesión activa y verifica que la cuenta esté activa.
    Si el usuario está inactivo, aborta con HTTP 403.
    """
    user = session_entry.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado para la sesión.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo o suspendido. Contacte al administrador.",
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Exige que el usuario autenticado tenga el rol de administrador ('admin').
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere rol de administrador.",
        )
    return current_user


def verify_csrf(
    request: Request,
    session_entry: Session = Depends(get_current_session),
) -> None:
    """
    Protección CSRF obligatoria para peticiones mutables (POST, PUT, PATCH, DELETE).
    Compara de forma segura la cabecera X-CSRF-Token enviada por el frontend
    con el hash CSRF almacenado en la sesión de base de datos.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header or not verify_csrf_token(csrf_header, session_entry.csrf_token_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token CSRF no válido o ausente.",
            )
