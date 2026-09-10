import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_password
from app.models.session import Session
from app.models.user import User


def test_list_users_as_admin(admin_client: TestClient, test_user: User, test_admin_user: User):
    """Admin puede listar todos los usuarios del sistema (200 OK) sin exponer hashes."""
    for endpoint in ["/api/v1/admin/users", "/api/v1/admin/users/"]:
        response = admin_client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 2

        emails = [u["email"] for u in data["users"]]
        assert test_admin_user.email in emails
        assert test_user.email in emails

        # Verificar que ningún campo sensible se expone
        for u in data["users"]:
            assert "password_hash" not in u
            assert "hashed_password" not in u
            assert "password" not in u
            assert "token" not in u
            assert "token_hash" not in u
            assert "csrf_token" not in u


def test_list_users_as_regular_user_forbidden(client: TestClient):
    """Usuario normal (role=user) recibe 403 Forbidden al intentar listar usuarios."""
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 403
    assert "Permisos insuficientes" in response.json()["detail"]


def test_list_users_unauthenticated_unauthorized(unauthenticated_client: TestClient):
    """Petición anónima recibe 401 Unauthorized."""
    response = unauthenticated_client.get("/api/v1/admin/users")
    assert response.status_code == 401


def test_create_user_success(admin_client: TestClient, db):
    """Admin crea un usuario nuevo con email normalizado a minúsculas y contraseña segura."""
    payload = {
        "email": "  Nuevo.Abogado@Hitchings.ES  ",
        "password": "PasswordSeguraParaAbogado123!",
        "confirm_password": "PasswordSeguraParaAbogado123!",
        "role": "user",
    }
    response = admin_client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "nuevo.abogado@hitchings.es"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data
    assert "password_hash" not in data

    # Verificar en base de datos que el hash es Argon2id y distinto de la clave en texto plano
    user_in_db = db.scalar(select(User).where(User.email == "nuevo.abogado@hitchings.es"))
    assert user_in_db is not None
    assert user_in_db.password_hash.startswith("$argon2id$")
    assert user_in_db.password_hash != "PasswordSeguraParaAbogado123!"
    assert verify_password("PasswordSeguraParaAbogado123!", user_in_db.password_hash)


def test_create_admin_user_success(admin_client: TestClient, db):
    """Admin puede crear otro administrador."""
    payload = {
        "email": "segundo.admin@hitchings.es",
        "password": "PasswordSeguraParaSegundoAdmin123!",
        "role": "admin",
    }
    response = admin_client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_create_user_duplicate_email_conflict(admin_client: TestClient, test_user: User):
    """Intento de crear un usuario con email duplicado responde 409 Conflict."""
    payload = {
        "email": test_user.email.upper(),  # Prueba de insensibilidad a mayúsculas
        "password": "PasswordSeguraNueva123!",
        "role": "user",
    }
    response = admin_client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 409
    assert "Ya existe un usuario registrado con ese correo" in response.json()["detail"]


def test_create_user_short_password_validation_error(admin_client: TestClient):
    """Contraseña menor de 12 caracteres es rechazada con 422 Unprocessable Entity."""
    payload = {
        "email": "corto@hitchings.es",
        "password": "corta",
        "role": "user",
    }
    response = admin_client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 422


def test_create_user_mismatched_confirm_password(admin_client: TestClient):
    """Contraseñas que no coinciden son rechazadas con 422."""
    payload = {
        "email": "mismatch@hitchings.es",
        "password": "PasswordSegura1234!",
        "confirm_password": "PasswordDiferente1234!",
        "role": "user",
    }
    response = admin_client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 422


def test_create_user_forbidden_for_regular_user(client: TestClient):
    """Usuario normal recibe 403 al intentar crear usuarios."""
    payload = {
        "email": "intruso@hitchings.es",
        "password": "PasswordSegura1234!",
        "role": "user",
    }
    response = client.post("/api/v1/admin/users", json=payload)
    assert response.status_code == 403


def test_create_user_csrf_missing_rejected(admin_session_tokens):
    """Petición sin CSRF es rechazada con 403."""
    _, raw_session_token, _ = admin_session_tokens
    with TestClient(app_under_test := __import__("app.main", fromlist=["app"]).app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
        # No se envía cabecera X-CSRF-Token
        response = tc.post("/api/v1/admin/users", json={
            "email": "sin-csrf@hitchings.es",
            "password": "PasswordSegura1234!",
        })
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]


def test_update_user_attributes(admin_client: TestClient, test_user: User, db):
    """Admin puede actualizar email, rol y estado de un usuario normal."""
    old_updated_at = test_user.updated_at
    payload = {
        "email": "actualizado@hitchings.es",
        "role": "admin",
    }
    response = admin_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "actualizado@hitchings.es"
    assert data["role"] == "admin"

    db.refresh(test_user)
    assert test_user.email == "actualizado@hitchings.es"
    assert test_user.role == "admin"
    assert test_user.updated_at >= old_updated_at


def test_update_user_duplicate_email_conflict(admin_client: TestClient, test_user: User, test_admin_user: User):
    """Intentar cambiar el email de un usuario al de otro existente responde 409."""
    payload = {"email": test_admin_user.email}
    response = admin_client.patch(f"/api/v1/admin/users/{test_user.id}", json=payload)
    assert response.status_code == 409
    assert "Ya existe un usuario registrado" in response.json()["detail"]


def test_update_user_not_found(admin_client: TestClient):
    """Intentar actualizar un ID inexistente responde 404."""
    non_existent_id = uuid.uuid4()
    response = admin_client.patch(f"/api/v1/admin/users/{non_existent_id}", json={"role": "user"})
    assert response.status_code == 404


def test_deactivate_user_revokes_sessions(admin_client: TestClient, test_user: User, active_session_tokens, db):
    """Desactivar un usuario (is_active=false) revoca todas sus sesiones activas de inmediato."""
    _, raw_session_token, _ = active_session_tokens

    # Comprobar que la sesión existe en BD antes
    active_sessions = db.scalars(select(Session).where(Session.user_id == test_user.id)).all()
    assert len(active_sessions) >= 1

    # Desactivar usuario
    response = admin_client.patch(f"/api/v1/admin/users/{test_user.id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Comprobar que todas sus sesiones fueron eliminadas de la BD
    remaining_sessions = db.scalars(select(Session).where(Session.user_id == test_user.id)).all()
    assert len(remaining_sessions) == 0

    # Comprobar que una petición con la cookie antigua es rechazada
    with TestClient(app_under_test := __import__("app.main", fromlist=["app"]).app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
        req = tc.get("/api/v1/auth/me")
        assert req.status_code == 401


def test_change_user_password_revokes_sessions(admin_client: TestClient, test_user: User, active_session_tokens, db):
    """Cambiar la contraseña de un usuario revoca todas sus sesiones activas y actualiza el hash."""
    _, raw_session_token, _ = active_session_tokens
    old_last_login = test_user.last_login_at

    payload = {
        "password": "NuevaPasswordCompletamenteSegura123!",
        "confirm_password": "NuevaPasswordCompletamenteSegura123!",
    }
    response = admin_client.post(f"/api/v1/admin/users/{test_user.id}/password", json=payload)
    assert response.status_code == 200

    db.refresh(test_user)
    assert verify_password("NuevaPasswordCompletamenteSegura123!", test_user.password_hash)
    assert test_user.last_login_at == old_last_login  # No se debe alterar last_login_at

    # Las sesiones antiguas deben haber sido revocadas
    remaining_sessions = db.scalars(select(Session).where(Session.user_id == test_user.id)).all()
    assert len(remaining_sessions) == 0

    # Petición con la cookie previa es rechazada
    with TestClient(app_under_test := __import__("app.main", fromlist=["app"]).app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
        req = tc.get("/api/v1/auth/me")
        assert req.status_code == 401


def test_last_admin_cannot_be_deactivated(admin_client: TestClient, test_admin_user: User, db):
    """El único administrador activo NO puede ser desactivado (protección contra orfandad)."""
    # Solo existe test_admin_user como admin en la BD
    response = admin_client.patch(f"/api/v1/admin/users/{test_admin_user.id}", json={"is_active": False})
    assert response.status_code == 409
    assert "último administrador activo" in response.json()["detail"]

    # Sigue activo
    db.refresh(test_admin_user)
    assert test_admin_user.is_active is True


def test_last_admin_cannot_be_demoted(admin_client: TestClient, test_admin_user: User, db):
    """El único administrador activo NO puede ser degradado a rol 'user'."""
    response = admin_client.patch(f"/api/v1/admin/users/{test_admin_user.id}", json={"role": "user"})
    assert response.status_code == 409
    assert "último administrador activo" in response.json()["detail"]

    # Sigue siendo admin
    db.refresh(test_admin_user)
    assert test_admin_user.role == "admin"


def test_admin_can_be_demoted_or_deactivated_if_another_admin_exists(admin_client: TestClient, test_admin_user: User, db):
    """Si existe otro admin activo, un administrador sí puede ser desactivado o degradado."""
    # Crear un segundo admin activo
    second_admin = User(
        email="otro.admin@hitchings.es",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummyhash$dummy",
        role="admin",
        is_active=True,
    )
    db.add(second_admin)
    db.commit()

    # Ahora sí se permite desactivar test_admin_user
    response = admin_client.patch(f"/api/v1/admin/users/{test_admin_user.id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_can_edit_own_email(admin_client: TestClient, test_admin_user: User, db):
    """Un administrador puede actualizar su propio email."""
    response = admin_client.patch(f"/api/v1/admin/users/{test_admin_user.id}", json={"email": "nuevo.email.admin@hitchings.es"})
    assert response.status_code == 200
    assert response.json()["email"] == "nuevo.email.admin@hitchings.es"

    db.refresh(test_admin_user)
    assert test_admin_user.email == "nuevo.email.admin@hitchings.es"
