import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, joinedload

from app.core.config import settings
from app.core.logging import logger
from app.core.security import derive_csrf_token, generate_random_token, hash_token, verify_password
from app.models.session import Session
from app.models.user import User


class AuthService:
    """Servicio para la gestión de autenticación, verificación de credenciales y ciclo de vida de sesiones."""

    def authenticate_user(
        self, db: DbSession, email: str, password: str
    ) -> Optional[User]:
        """
        Verifica las credenciales del usuario sin revelar si el correo existe o no.
        Retorna la entidad User si la contraseña coincide con el hash Argon2id, o None en caso contrario.
        """
        normalized_email = email.strip().lower()
        stmt = select(User).where(User.email == normalized_email)
        user = db.execute(stmt).scalar_one_or_none()

        if not user:
            # Ejecutar verificación simulada para mitigar ataques de temporización por enumeración
            verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$dummyhashfordummyuser$dummy")
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    def create_session(
        self, db: DbSession, user: User
    ) -> Tuple[Session, str, str]:
        """
        Genera una nueva sesión server-side.
        Retorna:
          (entidad_sesión, raw_session_token, raw_csrf_token)
        Solo los hashes SHA-256 de ambos tokens se persisten en base de datos.
        """
        session_id = uuid.uuid4()
        raw_session_token = generate_random_token(32)
        token_hash = hash_token(raw_session_token)

        # Derivación determinista HMAC del token CSRF vinculado a esta sesión
        raw_csrf_token = derive_csrf_token(session_id, token_hash)
        csrf_token_hash = hash_token(raw_csrf_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.SESSION_TTL_HOURS)

        session_entry = Session(
            id=session_id,
            user_id=user.id,
            token_hash=token_hash,
            csrf_token_hash=csrf_token_hash,
            created_at=now,
            expires_at=expires_at,
            last_seen_at=now,
        )

        # Actualizar last_login_at en el usuario (sin alterar updated_at)
        user.last_login_at = now

        db.add(session_entry)
        db.commit()
        db.refresh(session_entry)

        return session_entry, raw_session_token, raw_csrf_token

    def get_session_by_token(
        self, db: DbSession, raw_session_token: str
    ) -> Optional[Session]:
        """
        Busca y valida una sesión activa mediante el token opaco de la cookie.
        Comprueba que la sesión no haya expirado.
        """
        if not raw_session_token:
            return None

        token_hash = hash_token(raw_session_token)
        now = datetime.now(timezone.utc)

        stmt = (
            select(Session)
            .options(joinedload(Session.user))
            .where(Session.token_hash == token_hash)
            .where(Session.expires_at > now)
        )
        session_entry = db.execute(stmt).scalar_one_or_none()

        if not session_entry:
            return None

        # Actualizar last_seen_at
        session_entry.last_seen_at = now
        try:
            db.commit()
        except Exception:
            db.rollback()

        return session_entry

    def revoke_session(self, db: DbSession, session_entry: Session) -> None:
        """Invalida y elimina la sesión activa de la base de datos."""
        db.delete(session_entry)
        db.commit()

    def revoke_all_user_sessions(self, db: DbSession, user_id: uuid.UUID) -> None:
        """Invalida y elimina todas las sesiones activas de un usuario."""
        stmt = select(Session).where(Session.user_id == user_id)
        sessions = db.execute(stmt).scalars().all()
        for s in sessions:
            db.delete(s)
        db.commit()


auth_service = AuthService()
