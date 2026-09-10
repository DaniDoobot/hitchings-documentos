import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.schemas.auth import UserPublicResponse
from app.schemas.users import (
    UserChangePasswordRequest,
    UserCreateRequest,
    UserListResponse,
    UserUpdateRequest,
)
from app.services.user_service import (
    LastAdminError,
    UserAlreadyExistsError,
    UserNotFoundError,
    user_service,
)

router = APIRouter(prefix="/admin/users", tags=["Admin - Usuarios"])


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar todos los usuarios del sistema",
    description="Retorna el listado completo de usuarios registrados. Requiere rol de administrador.",
)
@router.get(
    "/",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_users(
    db: DbSession = Depends(get_db),
) -> UserListResponse:
    users = user_service.list_users(db)
    return UserListResponse(users=users, total=len(users))


@router.post(
    "",
    response_model=UserPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo usuario",
    description="Crea un nuevo usuario con credenciales iniciales. Requiere rol de administrador.",
)
@router.post(
    "/",
    response_model=UserPublicResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_user(
    body: UserCreateRequest,
    db: DbSession = Depends(get_db),
) -> UserPublicResponse:
    try:
        user = user_service.create_user(
            db=db,
            email=body.email,
            password=body.password,
            role=body.role,
        )
        return UserPublicResponse.model_validate(user)
    except UserAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


@router.patch(
    "/{user_id}",
    response_model=UserPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar atributos de un usuario",
    description="Permite modificar email, rol o estado activo/inactivo. Protege contra la degradación del último admin.",
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: DbSession = Depends(get_db),
) -> UserPublicResponse:
    try:
        user = user_service.update_user(
            db=db,
            user_id=user_id,
            email=body.email,
            role=body.role,
            is_active=body.is_active,
        )
        return UserPublicResponse.model_validate(user)
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except UserAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err
    except LastAdminError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


@router.post(
    "/{user_id}/password",
    response_model=UserPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Restablecer contraseña de un usuario",
    description="Establece una nueva contraseña y revoca de inmediato todas las sesiones activas del usuario.",
)
async def change_user_password(
    user_id: uuid.UUID,
    body: UserChangePasswordRequest,
    db: DbSession = Depends(get_db),
) -> UserPublicResponse:
    try:
        user = user_service.change_user_password(
            db=db,
            user_id=user_id,
            new_password=body.password,
        )
        return UserPublicResponse.model_validate(user)
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
