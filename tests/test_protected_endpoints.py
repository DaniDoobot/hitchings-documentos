def test_unauthenticated_requests_return_401_on_all_functional_endpoints(unauthenticated_client):
    """
    Verifica taxativamente que todos los endpoints funcionales existentes exigen
    autenticación y devuelven HTTP 401 sin sesión activa.
    """
    # 1. Documents
    res = unauthenticated_client.post("/api/v1/documents/extract")
    assert res.status_code == 401

    # 2. Audio
    res = unauthenticated_client.post("/api/v1/audio/transcribe")
    assert res.status_code == 401

    # 3. Text
    res = unauthenticated_client.post("/api/v1/text/prepare", json={"text": "hola"})
    assert res.status_code == 401

    # 4. Prompts
    res = unauthenticated_client.get("/api/v1/prompts")
    assert res.status_code == 401

    # 5. Analysis
    res = unauthenticated_client.post("/api/v1/analysis", json={})
    assert res.status_code == 401

    # 6. Export
    res = unauthenticated_client.post("/api/v1/export/word", json={})
    assert res.status_code == 401


def test_public_endpoints_remain_open_without_session(unauthenticated_client):
    """Verifica que los endpoints de salud y raíz son públicos sin requerir sesión."""
    res_health = unauthenticated_client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_root = unauthenticated_client.get("/")
    assert res_root.status_code == 200
