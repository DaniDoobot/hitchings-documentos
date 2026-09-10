from sqlalchemy import select
from app.core.security import verify_password
from app.models.user import User
from scripts.create_admin import create_admin_user


def test_create_admin_user_success(db):
    """Verifica creación exitosa del administrador con Argon2id y rol admin."""
    success = create_admin_user("SocioAdmin@Hitchings.com", "PasswordMuyLargaYRobusta123!", db=db)
    assert success is True

    stmt = select(User).where(User.email == "socioadmin@hitchings.com")
    user = db.execute(stmt).scalar_one_or_none()

    assert user is not None
    assert user.email == "socioadmin@hitchings.com"
    assert user.role == "admin"
    assert user.is_active is True
    assert verify_password("PasswordMuyLargaYRobusta123!", user.password_hash) is True


def test_create_admin_user_rejects_short_password(db):
    """Verifica rechazo si la contraseña tiene menos de 12 caracteres."""
    success = create_admin_user("admin2@hitchings.com", "corta123", db=db)
    assert success is False

    stmt = select(User).where(User.email == "admin2@hitchings.com")
    assert db.execute(stmt).scalar_one_or_none() is None


def test_create_admin_user_prevents_duplicates(db, test_user):
    """Verifica que no permite registrar un administrador con un email ya existente."""
    success = create_admin_user("test@hitchings.example.com", "PasswordMuyLargaYRobusta123!", db=db)
    assert success is False
