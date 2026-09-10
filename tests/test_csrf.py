from app.core.config import settings


def test_post_without_csrf_returns_403(unauthenticated_client, active_session_tokens):
    """Verifica que una petición mutable (POST) sin X-CSRF-Token es rechazada con HTTP 403."""
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    # Intento de petición POST sin cabecera X-CSRF-Token
    response = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Texto prueba"})
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_post_with_invalid_csrf_returns_403(unauthenticated_client, active_session_tokens):
    """Verifica que una petición mutable con X-CSRF-Token erróneo es rechazada con HTTP 403."""
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
    unauthenticated_client.headers.update({"X-CSRF-Token": "token_falso_invalido"})

    response = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Texto prueba"})
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


def test_post_with_valid_csrf_succeeds(unauthenticated_client, active_session_tokens):
    """Verifica que con sesión y X-CSRF-Token válido la petición mutable es aceptada."""
    _, raw_session_token, raw_csrf_token = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
    unauthenticated_client.headers.update({"X-CSRF-Token": raw_csrf_token})

    response = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Texto prueba"})
    assert response.status_code == 200


def test_get_does_not_require_csrf(unauthenticated_client, active_session_tokens):
    """Verifica que las peticiones idempotentes (GET) protegidas no exigen cabecera CSRF."""
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    # Petición GET sin cabecera X-CSRF-Token
    response = unauthenticated_client.get("/api/v1/prompts")
    assert response.status_code == 200
