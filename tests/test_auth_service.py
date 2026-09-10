from datetime import datetime, timedelta, timezone
from app.core.security import hash_password, verify_csrf_token
from app.models.user import User
from app.services.auth_service import auth_service


def test_authenticate_user_success(db, test_user):
    """Verifica autenticación exitosa con credenciales correctas."""
    user = auth_service.authenticate_user(db, "test@hitchings.example.com", "PasswordSegura123!")
    assert user is not None
    assert user.id == test_user.id


def test_authenticate_user_wrong_password(db, test_user):
    """Verifica fallo ante contraseña incorrecta."""
    user = auth_service.authenticate_user(db, "test@hitchings.example.com", "PasswordErronea123!")
    assert user is None


def test_authenticate_user_nonexistent_email(db):
    """Verifica que un email no registrado retorna None."""
    user = auth_service.authenticate_user(db, "noexiste@hitchings.example.com", "PasswordSegura123!")
    assert user is None


def test_authenticate_user_email_case_insensitivity(db, test_user):
    """Verifica que el email se normaliza a minúsculas y no depende de mayúsculas/minúsculas."""
    user = auth_service.authenticate_user(db, "  TEST@HITCHINGS.EXAMPLE.COM  ", "PasswordSegura123!")
    assert user is not None
    assert user.id == test_user.id


def test_create_session_hashes_tokens(db, test_user):
    """Verifica que create_session retorna tokens RAW y persiste únicamente hashes."""
    session_entry, raw_token, raw_csrf = auth_service.create_session(db, test_user)

    assert raw_token not in session_entry.token_hash
    assert raw_csrf not in session_entry.csrf_token_hash
    assert verify_csrf_token(raw_csrf, session_entry.csrf_token_hash) is True
    exp = session_entry.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    assert exp > datetime.now(timezone.utc)
    assert test_user.last_login_at is not None


def test_get_session_by_token_active(db, test_user):
    """Verifica que una sesión válida se recupera correctamente por su token raw."""
    session_entry, raw_token, _ = auth_service.create_session(db, test_user)

    retrieved = auth_service.get_session_by_token(db, raw_token)
    assert retrieved is not None
    assert retrieved.id == session_entry.id
    assert retrieved.user.id == test_user.id


def test_get_session_by_token_expired(db, test_user):
    """Verifica que una sesión vencida es rechazada."""
    session_entry, raw_token, _ = auth_service.create_session(db, test_user)
    # Forzar fecha de expiración en el pasado
    session_entry.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    retrieved = auth_service.get_session_by_token(db, raw_token)
    assert retrieved is None


def test_revoke_session(db, test_user):
    """Verifica que la revocación de sesión elimina el registro y deniega accesos posteriores."""
    session_entry, raw_token, _ = auth_service.create_session(db, test_user)

    auth_service.revoke_session(db, session_entry)
    assert auth_service.get_session_by_token(db, raw_token) is None
