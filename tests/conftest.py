import os
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import generate_random_token, hash_password, hash_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.session import Session
from app.models.user import User

from sqlalchemy.pool import StaticPool

# Motor de base de datos para tests (en memoria por defecto o TEST_DATABASE_URL)
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")

test_engine_kwargs = {}
if TEST_DB_URL.startswith("sqlite"):
    test_engine_kwargs["connect_args"] = {"check_same_thread": False}
    test_engine_kwargs["poolclass"] = StaticPool

test_engine = create_engine(TEST_DB_URL, **test_engine_kwargs)

if TEST_DB_URL.startswith("sqlite"):
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Crea todas las tablas antes de cada test y las elimina al finalizar para aislamiento absoluto."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Proporciona una sesión de base de datos aislada para el test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def override_get_db(db):
    """Sobrescribe la dependencia get_db de FastAPI para apuntar a la BD de pruebas."""
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def unauthenticated_client():
    """TestClient sin cookies ni cabeceras de autenticación."""
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def test_user(db):
    """Crea un usuario estándar activo para pruebas."""
    user = User(
        email="test@hitchings.example.com",
        password_hash=hash_password("PasswordSegura123!"),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db):
    """Crea un usuario administrador activo para pruebas."""
    admin = User(
        email="admin@hitchings.example.com",
        password_hash=hash_password("AdminSeguro123!"),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def active_session_tokens(db, test_user):
    """Crea una sesión activa para test_user y retorna (session_model, raw_session_token, raw_csrf_token)."""
    raw_session_token = generate_random_token(32)
    raw_csrf_token = generate_random_token(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=12)

    sess = Session(
        user_id=test_user.id,
        token_hash=hash_token(raw_session_token),
        csrf_token_hash=hash_token(raw_csrf_token),
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess, raw_session_token, raw_csrf_token


@pytest.fixture
def client(active_session_tokens):
    """
    TestClient por defecto para la suite de tests existente.
    Viene pre-autenticado con cookie de sesión y cabecera X-CSRF-Token
    para que los 121 tests existentes continúen pasando sin regresiones.
    """
    _, raw_session_token, raw_csrf_token = active_session_tokens
    with TestClient(app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
        tc.headers.update({"X-CSRF-Token": raw_csrf_token})
        yield tc
