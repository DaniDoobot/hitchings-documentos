import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core.security import hash_password
from app.models.user import User
from app.services.auth_service import auth_service


class UserNotFoundError(Exception):
    """El usuario solicitado no existe en la base de datos."""


class UserAlreadyExistsError(Exception):
    """Ya existe un usuario con el correo electrónico proporcionado."""


class LastAdminError(Exception):
    """No puede desactivarse o degradarse el último administrador activo del sistema."""


class UserService:
    """Servicio de gestión administrativa de usuarios."""

    def list_users(self, db: DbSession) -> list[User]:
        """Retorna todos los usuarios registrados ordenados por fecha de creación descendente."""
        stmt = select(User).order_by(User.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    def get_user_by_id(self, db: DbSession, user_id: uuid.UUID) -> User:
        """Obtiene un usuario por su identificador único o lanza UserNotFoundError."""
        user = db.get(User, user_id)
        if not user:
            raise UserNotFoundError("Usuario no encontrado.")
        return user

    def create_user(
        self,
        db: DbSession,
        email: str,
        password: str,
        role: str = "user",
    ) -> User:
        """
        Crea un nuevo usuario con email normalizado y contraseña cifrada con Argon2id.
        Lanza UserAlreadyExistsError si el email ya se encuentra registrado.
        """
        normalized_email = email.strip().lower()

        # Verificar unicidad de email
        stmt = select(User).where(User.email == normalized_email)
        existing_user = db.execute(stmt).scalar_one_or_none()
        if existing_user:
            raise UserAlreadyExistsError("Ya existe un usuario registrado con ese correo electrónico.")

        now = datetime.now(timezone.utc)
        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login_at=None,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(
        self,
        db: DbSession,
        user_id: uuid.UUID,
        email: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        """
        Actualiza parcialmente los atributos de un usuario.
        Aplica protección estricta para no dejar el sistema sin ningún administrador activo.
        Si se desactiva la cuenta, revoca inmediatamente todas sus sesiones activas.
        """
        user = self.get_user_by_id(db, user_id)
        has_changes = False

        # 1. Validación y protección de último administrador activo
        if user.role == "admin" and user.is_active:
            will_demote = role is not None and role != "admin"
            will_deactivate = is_active is False

            if will_demote or will_deactivate:
                other_active_admins_stmt = select(func.count(User.id)).where(
                    User.role == "admin",
                    User.is_active.is_(True),
                    User.id != user.id,
                )
                other_admins_count = db.execute(other_active_admins_stmt).scalar() or 0
                if other_admins_count < 1:
                    raise LastAdminError(
                        "No puede desactivarse o degradarse el último administrador activo."
                    )

        # 2. Validación de unicidad de email si se intenta cambiar
        if email is not None:
            normalized_email = email.strip().lower()
            if normalized_email != user.email:
                stmt = select(User).where(User.email == normalized_email, User.id != user.id)
                conflict_user = db.execute(stmt).scalar_one_or_none()
                if conflict_user:
                    raise UserAlreadyExistsError(
                        "Ya existe un usuario registrado con ese correo electrónico."
                    )
                user.email = normalized_email
                has_changes = True

        # 3. Cambio de rol
        if role is not None and role != user.role:
            user.role = role
            has_changes = True

        # 4. Cambio de estado de activación
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            has_changes = True
            if is_active is False:
                # Al desactivar la cuenta, revocar de inmediato todas sus sesiones activas
                auth_service.revoke_all_user_sessions(db, user.id)

        # 5. Persistir y actualizar updated_at solo si hubo cambios reales
        if has_changes:
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)

        return user

    def change_user_password(
        self,
        db: DbSession,
        user_id: uuid.UUID,
        new_password: str,
    ) -> User:
        """
        Restablece la contraseña de un usuario con un nuevo hash Argon2id.
        Revoca inmediatamente TODAS las sesiones activas del usuario afectado.
        Actualiza updated_at y preserva intacto last_login_at.
        """
        user = self.get_user_by_id(db, user_id)
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Revocación inmediata de todas las sesiones de este usuario
        auth_service.revoke_all_user_sessions(db, user.id)

        db.commit()
        db.refresh(user)
        return user


user_service = UserService()
