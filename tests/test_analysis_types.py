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
