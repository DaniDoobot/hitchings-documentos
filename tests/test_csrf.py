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


def test_consecutive_calls_to_auth_me_maintain_consistent_valid_csrf(unauthenticated_client, active_session_tokens):
    """
    Requisito 1: Dos llamadas consecutivas a /auth/me para la misma sesión
    deben retornar un CSRF consistente e idéntico, y permitir peticiones POST.
    """
    _, raw_session_token, _ = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    res1 = unauthenticated_client.get("/api/v1/auth/me")
    assert res1.status_code == 200
    csrf_token_1 = res1.json()["csrf_token"]

    res2 = unauthenticated_client.get("/api/v1/auth/me")
    assert res2.status_code == 200
    csrf_token_2 = res2.json()["csrf_token"]

    # El token debe ser idéntico y determinista para la sesión
    assert csrf_token_1 == csrf_token_2

    # Ambas referencias funcionan para peticiones mutables
    unauthenticated_client.headers.update({"X-CSRF-Token": csrf_token_1})
    post1 = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Texto prueba 1"})
    assert post1.status_code == 200

    unauthenticated_client.headers.update({"X-CSRF-Token": csrf_token_2})
    post2 = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Texto prueba 2"})
    assert post2.status_code == 200


def test_simulated_multi_tab_does_not_invalidate_first_tab_csrf(unauthenticated_client, active_session_tokens):
    """
    Requisito 2: Simulación de múltiples pestañas de navegador compartiendo la cookie de sesión.
    La apertura y llamada a /auth/me desde una segunda pestaña no invalida el CSRF de la primera pestaña.
    """
    _, raw_session_token, _ = active_session_tokens

    # Pestaña A consulta su sesión
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
    tab_a_res = unauthenticated_client.get("/api/v1/auth/me")
    csrf_tab_a = tab_a_res.json()["csrf_token"]

    # Pestaña B abre la misma aplicación (mismo session cookie) y consulta su sesión
    tab_b_res = unauthenticated_client.get("/api/v1/auth/me")
    csrf_tab_b = tab_b_res.json()["csrf_token"]

    assert csrf_tab_a == csrf_tab_b

    # Pestaña A realiza un POST con su token: debe funcionar
    unauthenticated_client.headers.update({"X-CSRF-Token": csrf_tab_a})
    post_a = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Petición desde Pestaña A"})
    assert post_a.status_code == 200

    # Pestaña B realiza un POST con su token: debe funcionar
    unauthenticated_client.headers.update({"X-CSRF-Token": csrf_tab_b})
    post_b = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Petición desde Pestaña B"})
    assert post_b.status_code == 200

    # Pestaña A realiza una segunda petición posterior: no ha sido invalidada
    unauthenticated_client.headers.update({"X-CSRF-Token": csrf_tab_a})
    post_a_again = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "Segunda petición Pestaña A"})
    assert post_a_again.status_code == 200


def test_logout_requires_valid_csrf(unauthenticated_client, active_session_tokens):
    """
    Requisito 4: Logout exige un token CSRF válido.
    Sin CSRF o con CSRF incorrecto produce 403 y no revoca la sesión.
    Con CSRF válido produce 200 y revoca la sesión.
    """
    _, raw_session_token, raw_csrf_token = active_session_tokens
    unauthenticated_client.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

    # 1. Logout sin CSRF -> 403
    unauthenticated_client.headers.pop("X-CSRF-Token", None)
    res_no_csrf = unauthenticated_client.post("/api/v1/auth/logout")
    assert res_no_csrf.status_code == 403

    # 2. Logout con CSRF inválido -> 403
    unauthenticated_client.headers.update({"X-CSRF-Token": "csrf_falso_invalido"})
    res_bad_csrf = unauthenticated_client.post("/api/v1/auth/logout")
    assert res_bad_csrf.status_code == 403

    # Sesión sigue viva
    assert unauthenticated_client.get("/api/v1/auth/me").status_code == 200

    # 3. Logout con CSRF válido -> 200 y revoca sesión
    unauthenticated_client.headers.update({"X-CSRF-Token": raw_csrf_token})
    res_good_csrf = unauthenticated_client.post("/api/v1/auth/logout")
    assert res_good_csrf.status_code == 200

    # Sesión revocada
    assert unauthenticated_client.get("/api/v1/auth/me").status_code == 401


def test_raw_csrf_token_is_never_persisted_in_database(db, active_session_tokens):
    """
    Requisito 5: El CSRF token raw nunca se almacena en texto claro en PostgreSQL.
    Solo se almacena su hash criptográfico SHA-256.
    """
    from app.core.security import hash_token
    session_entry, raw_session_token, raw_csrf_token = active_session_tokens

    # La columna en BD contiene el hash, nunca el valor en claro
    assert session_entry.csrf_token_hash != raw_csrf_token
    assert session_entry.token_hash != raw_session_token

    # El valor almacenado es exactamente el hash SHA-256 del token raw
    assert session_entry.csrf_token_hash == hash_token(raw_csrf_token)
    assert session_entry.token_hash == hash_token(raw_session_token)
    assert len(session_entry.csrf_token_hash) == 64

