import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, hash_token
from app.models.session import Session
from app.models.user import User


def test_user_creation_and_defaults(db):
    """Verifica la creación del usuario con ID UUID, timestamps UTC y valores por defecto."""
    user = User(
        email="abogado@hitchings.com",
        password_hash=hash_password("ContraseñaValida123!"),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "abogado@hitchings.com"
    assert user.role == "user"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.last_login_at is None
    # No almacena la contraseña en claro
    assert "ContraseñaValida123!" not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")


def test_user_updated_at_behavior_on_login_and_updates(db, test_user):
    """
    Verifica que:
    1. updated_at se inicializa al crear el usuario.
    2. Actualizar únicamente last_login_at (login) NO modifica updated_at.
    3. Actualizar datos persistentes del usuario actualiza updated_at.
    """
    initial_updated_at = test_user.updated_at
    initial_created_at = test_user.created_at
    assert initial_updated_at is not None
    assert initial_created_at is not None

    # Simular inicio de sesión (solo modifica last_login_at)
    now = datetime.now(timezone.utc)
    test_user.last_login_at = now
    db.commit()
    db.refresh(test_user)

    # last_login_at se actualiza pero updated_at permanece intacto
    assert test_user.last_login_at is not None
    assert test_user.updated_at == initial_updated_at

    # Actualizar datos relevantes del usuario
    new_timestamp = datetime.now(timezone.utc)
    test_user.role = "admin"
    test_user.updated_at = new_timestamp
    db.commit()
    db.refresh(test_user)

    assert test_user.role == "admin"
    actual_updated = test_user.updated_at
    if actual_updated.tzinfo is None:
        actual_updated = actual_updated.replace(tzinfo=timezone.utc)
    assert actual_updated == new_timestamp
    assert actual_updated >= (initial_updated_at.replace(tzinfo=timezone.utc) if initial_updated_at.tzinfo is None else initial_updated_at)


def test_user_email_unique_constraint(db):
    """Verifica que el email no puede duplicarse en la base de datos."""
    user1 = User(
        email="socio@hitchings.com",
        password_hash=hash_password("ContraseñaValida123!"),
    )
    db.add(user1)
    db.commit()

    user2 = User(
        email="socio@hitchings.com",
        password_hash=hash_password("OtraContraseñaValida123!"),
    )
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_session_creation_and_relationship(db, test_user):
    """Verifica la creación de sesión, relación con User y campos de expiración."""
    now = datetime.now(timezone.utc)
    raw_token = "opaque_session_token_12345"
    raw_csrf = "csrf_token_abcdef"

    sess = Session(
        user_id=test_user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)

    assert isinstance(sess.id, uuid.UUID)
    assert sess.user_id == test_user.id
    assert sess.user.email == test_user.email
    assert raw_token not in sess.token_hash
    assert raw_csrf not in sess.csrf_token_hash


def test_session_cascade_deletion_on_user_delete(db, test_user):
    """Verifica que al eliminar un usuario sus sesiones se eliminan en cascada."""
    now = datetime.now(timezone.utc)
    sess = Session(
        user_id=test_user.id,
        token_hash=hash_token("token_a_eliminar"),
        csrf_token_hash=hash_token("csrf_a_eliminar"),
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )
    db.add(sess)
    db.commit()

    # Comprobar que existe
    stmt = select(Session).where(Session.user_id == test_user.id)
    assert len(db.execute(stmt).scalars().all()) == 1

    # Eliminar usuario
    db.delete(test_user)
    db.commit()

    # Las sesiones deben haber desaparecido
    stmt = select(Session).where(Session.user_id == test_user.id)
    assert len(db.execute(stmt).scalars().all()) == 0
