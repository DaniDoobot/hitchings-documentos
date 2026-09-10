from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_session, get_current_user, get_db, verify_csrf
from app.core.config import settings
from app.core.logging import logger
from app.core.security import derive_csrf_token
from app.models.session import Session as SessionModel
from app.models.user import User as UserModel
from app.schemas.auth import AuthResponse, LoginRequest
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=AuthResponse, summary="Iniciar sesión")
async def login(
    request: LoginRequest,
    response: Response,
    db: DbSession = Depends(get_db),
):
    """
    Inicia sesión validando las credenciales con Argon2id.
    Emite una cookie HttpOnly 'hyg_session' con el token de sesión
    y retorna los datos públicos del usuario junto al CSRF token para memoria RAM.
    """
    user = auth_service.authenticate_user(db, request.email, request.password)
    if not user:
        logger.warning("Intento fallido de inicio de sesión | Email: %s", request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )

    if not user.is_active:
        logger.warning("Intento de login con cuenta inactiva | User ID: %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo o suspendido. Contacte al administrador.",
        )

    session_entry, raw_session_token, raw_csrf_token = auth_service.create_session(db, user)

    # Configurar cookie HttpOnly
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_session_token,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite="lax",
        path="/",
    )

    logger.info("Inicio de sesión exitoso | User ID: %s | Rol: %s", user.id, user.role)

    return AuthResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        csrf_token=raw_csrf_token,
    )


@router.get("/me", response_model=AuthResponse, summary="Obtener sesión y usuario actual")
async def get_me(
    current_user: UserModel = Depends(get_current_user),
    session_entry: SessionModel = Depends(get_current_session),
):
    """
    Verifica la cookie de sesión activa y retorna los datos del usuario
    junto al CSRF token estable derivado criptográficamente para la sesión.
    No rota el token ni invalida pestañas concurrentes.
    """
    csrf_token = derive_csrf_token(session_entry.id, session_entry.token_hash)

    return AuthResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at,
        csrf_token=csrf_token,
    )


@router.post("/logout", summary="Cerrar sesión")
async def logout(
    response: Response,
    session_entry: SessionModel = Depends(get_current_session),
    _: None = Depends(verify_csrf),
    db: DbSession = Depends(get_db),
):
    """
    Invalida y elimina la sesión activa de la base de datos y borra la cookie HttpOnly.
    Requiere CSRF token válido.
    """
    user_id = session_entry.user_id
    auth_service.revoke_session(db, session_entry)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.is_cookie_secure,
    )

    logger.info("Sesión cerrada y revocada | User ID: %s", user_id)
    return {"message": "Sesión cerrada correctamente"}
