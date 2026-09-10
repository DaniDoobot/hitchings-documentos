from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.models.user import User


def test_login_success(unauthenticated_client, test_user):
    """Verifica inicio de sesión exitoso, emisión de cookie HttpOnly y respuesta con CSRF token."""
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@hitchings.example.com",
            "password": "PasswordSegura123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@hitchings.example.com"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20

    # Cookie HttpOnly y SameSite
    assert settings.SESSION_COOKIE_NAME in response.cookies
    set_cookie_header = response.headers.get("set-cookie", "")
    assert f"{settings.SESSION_COOKIE_NAME}=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


def test_login_invalid_password(unauthenticated_client, test_user):
    """Verifica fallo con mensaje genérico ante contraseña incorrecta."""
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@hitchings.example.com",
            "password": "PasswordIncorrecta123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email o contraseña incorrectos."
    assert settings.SESSION_COOKIE_NAME not in response.cookies


def test_login_nonexistent_email_anti_enumeration(unauthenticated_client):
    """Verifica mensaje idéntico ante usuario inexistente para evitar enumeración."""
    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={
            "email": "inexistente@hitchings.example.com",
            "password": "PasswordCualquiera123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email o contraseña incorrectos."


def test_login_inactive_user(unauthenticated_client, db, test_user):
    """Verifica bloqueo a usuarios inactivos."""
    test_user.is_active = False
    db.commit()

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@hitchings.example.com",
            "password": "PasswordSegura123!",
        },
    )
    assert response.status_code == 403
    assert "inactivo" in response.json()["detail"].lower()


def test_login_validation_rules(unauthenticated_client):
    """Verifica validación de email y longitud mínima de contraseña (12 caracteres)."""
    # Email inválido
    res = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "no-email", "password": "PasswordSegura123!"},
    )
    assert res.status_code == 422

    # Contraseña demasiado corta (< 12)
    res2 = unauthenticated_client.post(
        "/api/v1/auth/login",
        json={"email": "test@hitchings.com", "password": "corta"},
    )
    assert res2.status_code == 422


def test_get_me_authenticated(unauthenticated_client, active_session_tokens, test_user):
    """Verifica que /auth/me retorna datos de sesión cuando la cookie es válida."""
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    response = unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert "csrf_token" in data


def test_get_me_unauthenticated(unauthenticated_client):
    """Verifica 401 en /auth/me sin cookie de sesión."""
    response = unauthenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_success(unauthenticated_client, active_session_tokens):
    """Verifica que logout con sesión y CSRF token invalida la sesión y borra la cookie."""
    _, raw_session_token, raw_csrf_token = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
    unauthenticated_client.headers.update({"X-CSRF-Token": raw_csrf_token})

    response = unauthenticated_client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    # Cookie eliminada (vacía o expirada)
    # Intentar acceder a /auth/me debe dar 401 ahora
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
    res_me = unauthenticated_client.get("/api/v1/auth/me")
    assert res_me.status_code == 401


def test_logout_without_csrf_forbidden(unauthenticated_client, active_session_tokens):
    """Verifica que logout sin cabecera X-CSRF-Token es rechazado con 403."""
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    response = unauthenticated_client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_absence_of_public_registration_endpoint(unauthenticated_client):
    """Verifica que no existe ningún endpoint público de registro/signup."""
    res1 = unauthenticated_client.post("/api/v1/auth/register", json={})
    assert res1.status_code in (404, 405)

    res2 = unauthenticated_client.post("/api/v1/auth/signup", json={})
    assert res2.status_code in (404, 405)
