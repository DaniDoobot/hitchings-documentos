import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis_type import AnalysisType
from app.services.analysis_prompt_builder import analysis_prompt_builder
from app.services.analysis_type_service import analysis_type_service


def test_seed_analysis_types_exist_and_active(db: Session):
    types = analysis_type_service.list_analysis_types(db, include_inactive=True)
    assert len(types) == 5
    codes = {t.code for t in types}
    assert codes == {
        "executive-summary",
        "legal-analysis",
        "key-points",
        "timeline",
        "custom-analysis",
    }
    for t in types:
        assert t.is_active is True
        assert t.created_by_user_id is None


def test_list_analysis_types_unauthenticated_returns_401(unauthenticated_client: TestClient):
    resp = unauthenticated_client.get("/api/v1/analysis-types")
    assert resp.status_code == 401


def test_regular_user_can_list_analysis_types(client: TestClient):
    resp = client.get("/api/v1/analysis-types")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 5
    assert len(data["items"]) == 5


def test_admin_user_can_list_analysis_types(admin_client: TestClient):
    resp = admin_client.get("/api/v1/analysis-types")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


def test_regular_user_can_get_analysis_type_by_id(client: TestClient):
    list_resp = client.get("/api/v1/analysis-types")
    item_id = list_resp.json()["items"][0]["id"]

    resp = client.get(f"/api/v1/analysis-types/{item_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == item_id
    assert data["name"] == list_resp.json()["items"][0]["name"]


def test_get_nonexistent_analysis_type_returns_404(client: TestClient):
    random_uuid = str(uuid.uuid4())
    resp = client.get(f"/api/v1/analysis-types/{random_uuid}")
    assert resp.status_code == 404


def test_regular_user_can_create_analysis_type(client: TestClient):
    payload = {
        "name": "Análisis de Daños Antitrust",
        "description": "Evaluación cuantitativa y cualitativa del daño derivado de infracciones del Derecho de la Competencia.",
        "instructions": "Examinar minuciosamente la documentación contable y pericial aportada. Contrastar el sobreprecio estimado con el escenario contrafactual.",
        "is_active": True,
    }
    resp = client.post("/api/v1/analysis-types", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == payload["name"]
    assert created["code"] == "analisis-de-danos-antitrust"
    assert created["is_active"] is True
    assert created["created_by_user_id"] is not None

    # Verificar que aparece en el catálogo de prompts
    prompts_resp = client.get("/api/v1/prompts")
    assert prompts_resp.status_code == 200
    prompt_ids = [p["id"] for p in prompts_resp.json()["prompts"]]
    assert "analisis-de-danos-antitrust" in prompt_ids


def test_slug_uniqueness_on_name_collision(client: TestClient):
    payload1 = {
        "name": "Revisión Contractual",
        "description": "Primera versión",
        "instructions": "Instrucciones detalladas de revisión de cláusulas contractuales.",
        "is_active": True,
    }
    resp1 = client.post("/api/v1/analysis-types", json=payload1)
    assert resp1.status_code == 201
    assert resp1.json()["code"] == "revision-contractual"

    payload2 = {
        "name": "Revisión Contractual",
        "description": "Segunda versión con mismo nombre",
        "instructions": "Instrucciones adicionales para revisión de cláusulas contractuales.",
        "is_active": True,
    }
    resp2 = client.post("/api/v1/analysis-types", json=payload2)
    assert resp2.status_code == 201
    assert resp2.json()["code"] == "revision-contractual-2"


def test_regular_user_can_update_analysis_type(client: TestClient):
    create_payload = {
        "name": "Tipo Inicial para Modificar",
        "description": "Descripción inicial",
        "instructions": "Instrucciones de prueba iniciales para modificación posterior.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=create_payload).json()
    item_id = created["id"]
    original_code = created["code"]

    update_payload = {
        "name": "Tipo Modificado con Nuevo Nombre",
        "description": "Descripción actualizada",
        "instructions": "Instrucciones actualizadas y perfeccionadas.",
        "is_active": False,
    }
    patch_resp = client.patch(f"/api/v1/analysis-types/{item_id}", json=update_payload)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["name"] == "Tipo Modificado con Nuevo Nombre"
    assert updated["description"] == "Descripción actualizada"
    assert updated["is_active"] is False
    # El código debe permanecer inmutable
    assert updated["code"] == original_code


def test_inactive_analysis_type_excluded_from_default_prompts_and_rejected_in_analysis(client: TestClient):
    create_payload = {
        "name": "Tipo Temporal a Desactivar",
        "description": "Tipo para verificar exclusión y rechazo",
        "instructions": "Instrucciones que no deben ser ejecutadas cuando esté inactivo.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=create_payload).json()
    item_id = created["id"]
    code = created["code"]

    # Activo: aparece en /prompts
    prompts_resp = client.get("/api/v1/prompts")
    assert any(p["id"] == code for p in prompts_resp.json()["prompts"])

    # Desactivar
    client.patch(f"/api/v1/analysis-types/{item_id}", json={"is_active": False})

    # Inactivo: NO aparece en /prompts (por defecto include_inactive=False)
    prompts_resp_after = client.get("/api/v1/prompts")
    assert not any(p["id"] == code for p in prompts_resp_after.json()["prompts"])

    # Inactivo: SÍ aparece con include_inactive=True
    prompts_inc_resp = client.get("/api/v1/prompts?include_inactive=true")
    assert any(p["id"] == code for p in prompts_inc_resp.json()["prompts"])

    # Intentar analizar con prompt inactivo retorna HTTP 400
    analysis_req = {
        "text": "Contenido para prueba de análisis con tipo inactivo.",
        "prompt_id": code,
        "options": {"detail_level": "standard", "output_format": "sections"},
    }
    analysis_resp = client.post("/api/v1/analysis", json=analysis_req)
    assert analysis_resp.status_code == 400
    assert "no está activo" in analysis_resp.json()["detail"]


def test_regular_user_cannot_access_admin_users(client: TestClient):
    """Verifica que el permiso ampliado en analysis-types NO compromete la seguridad de admin/users."""
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 403


def test_admin_user_can_access_admin_users(admin_client: TestClient):
    resp = admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200


def test_csrf_required_on_post_and_patch_analysis_types(active_session_tokens):
    """Verifica que mutaciones a /analysis-types exigen CSRF válido."""
    _, raw_session_token, _ = active_session_tokens

    from app.core.config import settings
    from app.main import app

    with TestClient(app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)

        # POST sin cabecera X-CSRF-Token retorna 403
        resp = tc.post("/api/v1/analysis-types", json={"name": "X", "instructions": "Y" * 10})
        assert resp.status_code == 403

        # POST con cabecera X-CSRF-Token inválida retorna 403
        resp_invalid = tc.post(
            "/api/v1/analysis-types",
            json={"name": "X", "instructions": "Y" * 10},
            headers={"X-CSRF-Token": "token-falso"},
        )
        assert resp_invalid.status_code == 403


def test_base_estructural_juridica_content():
    """Verifica que el prompt del sistema contenga la base estructural jurídica intacta."""
    system_instruction = analysis_prompt_builder.get_system_instruction()
    assert "HITCHINGS & GONZÁLEZ" in system_instruction
    assert "defensa de la competencia (antitrust)" in system_instruction
    assert "Unión Europea" in system_instruction
    assert "acciones colectivas" in system_instruction
    assert "PROMPT INJECTION" in system_instruction
    assert "SEPARACIÓN EPISTÉMICA ESTRICTA" in system_instruction
    assert "SUBORDINACIÓN INVIOLABLE" in system_instruction


# ============================================================
# DELETE /api/v1/analysis-types/{id}
# ============================================================

def test_admin_can_delete_analysis_type(admin_client: TestClient, db: Session):
    """Admin puede eliminar cualquier tipo de análisis — responde 204."""
    # Crear un tipo nuevo para eliminar
    payload = {
        "name": "Tipo para Borrar Admin",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para el test de borrado admin.",
        "is_active": True,
    }
    created = admin_client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]

    resp = admin_client.delete(f"/api/v1/analysis-types/{type_id}")
    assert resp.status_code == 204
    assert resp.content == b""


def test_regular_user_can_delete_analysis_type(client: TestClient):
    """Usuario normal puede eliminar cualquier tipo — responde 204."""
    payload = {
        "name": "Tipo para Borrar Usuario",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para el test de borrado usuario.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]

    resp = client.delete(f"/api/v1/analysis-types/{type_id}")
    assert resp.status_code == 204


def test_anonymous_cannot_delete_analysis_type(unauthenticated_client: TestClient, client: TestClient):
    """Anónimo recibe 401 al intentar eliminar."""
    payload = {
        "name": "Tipo para Borrar Anon",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para test anónimo.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]

    resp = unauthenticated_client.delete(f"/api/v1/analysis-types/{type_id}")
    assert resp.status_code == 401


def test_delete_without_csrf_returns_403(active_session_tokens):
    """DELETE sin cabecera CSRF retorna 403."""
    _, raw_session_token, _ = active_session_tokens

    from app.core.config import settings
    from app.main import app

    with TestClient(app) as tc:
        tc.cookies.set(settings.SESSION_COOKIE_NAME, raw_session_token)
        # Primero crear un tipo con CSRF (usar el client fixture indirectamente)
        # Para este test verificamos que sin CSRF el DELETE falla
        random_uuid = str(uuid.uuid4())
        resp = tc.delete(f"/api/v1/analysis-types/{random_uuid}")
        assert resp.status_code == 403


def test_delete_nonexistent_type_returns_404(client: TestClient):
    """DELETE de un ID inexistente retorna 404."""
    random_uuid = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/analysis-types/{random_uuid}")
    assert resp.status_code == 404


def test_deleted_type_not_in_analysis_types_list(client: TestClient):
    """Tipo eliminado no aparece en GET /api/v1/analysis-types."""
    payload = {
        "name": "Tipo a Desaparecer del Listado",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para verificar desaparición del listado.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]

    # Verificar que aparece antes de borrar
    list_before = client.get("/api/v1/analysis-types").json()
    assert any(t["id"] == type_id for t in list_before["items"])

    # Eliminar
    del_resp = client.delete(f"/api/v1/analysis-types/{type_id}")
    assert del_resp.status_code == 204

    # Verificar que ya no aparece
    list_after = client.get("/api/v1/analysis-types").json()
    assert not any(t["id"] == type_id for t in list_after["items"])


def test_deleted_type_not_in_prompts(client: TestClient):
    """Tipo eliminado no aparece en GET /api/v1/prompts."""
    payload = {
        "name": "Tipo a Desaparecer de Prompts",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para verificar desaparición de prompts.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]
    code = created["code"]

    # Verificar que aparece en /prompts
    prompts_before = client.get("/api/v1/prompts").json()
    assert any(p["id"] == code for p in prompts_before["prompts"])

    # Eliminar
    client.delete(f"/api/v1/analysis-types/{type_id}")

    # Verificar que no aparece en /prompts
    prompts_after = client.get("/api/v1/prompts").json()
    assert not any(p["id"] == code for p in prompts_after["prompts"])


def test_analysis_rejects_deleted_type(client: TestClient):
    """Intentar analizar con un código eliminado retorna 404."""
    payload = {
        "name": "Tipo Eliminado Para Análisis",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para verificar rechazo post-borrado.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    type_id = created["id"]
    code = created["code"]

    # Eliminar
    client.delete(f"/api/v1/analysis-types/{type_id}")

    # Intentar análisis con el código eliminado
    analysis_req = {
        "text": "Contenido para prueba de análisis con tipo eliminado.",
        "prompt_id": code,
        "options": {"detail_level": "standard", "output_format": "sections"},
    }
    analysis_resp = client.post("/api/v1/analysis", json=analysis_req)
    assert analysis_resp.status_code == 404


def test_delete_does_not_affect_users(client: TestClient, admin_client: TestClient):
    """Eliminar un tipo de análisis no afecta a los usuarios del sistema."""
    # Verificar cantidad de usuarios antes
    users_before = admin_client.get("/api/v1/admin/users").json()
    user_count_before = len(users_before["users"])

    # Crear y eliminar un tipo
    payload = {
        "name": "Tipo Inocuo Para Usuarios",
        "description": "Descripción",
        "instructions": "Instrucciones suficientes para verificar inocuidad sobre usuarios.",
        "is_active": True,
    }
    created = client.post("/api/v1/analysis-types", json=payload).json()
    client.delete(f"/api/v1/analysis-types/{created['id']}")

    # Verificar que los usuarios siguen igual
    users_after = admin_client.get("/api/v1/admin/users").json()
    assert len(users_after["users"]) == user_count_before


def test_seeded_type_can_be_deleted(client: TestClient):
    """Los tipos históricos (seeded) también pueden eliminarse físicamente."""
    # Obtener el primer tipo seeded
    list_resp = client.get("/api/v1/analysis-types").json()
    seeded = next(t for t in list_resp["items"] if t["code"] == "executive-summary")
    seeded_id = seeded["id"]

    resp = client.delete(f"/api/v1/analysis-types/{seeded_id}")
    assert resp.status_code == 204

    # Verificar que ya no existe
    get_resp = client.get(f"/api/v1/analysis-types/{seeded_id}")
    assert get_resp.status_code == 404
