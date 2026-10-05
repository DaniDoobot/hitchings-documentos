import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.prompt_setting import PromptSetting
from app.models.user import User
from app.services.analysis_prompt_builder import analysis_prompt_builder
from app.services.prompt_setting_service import (
    BasePromptNotFoundError,
    prompt_setting_service,
)


@pytest.fixture
def normal_user_client(db: Session) -> tuple[TestClient, User, str, str]:
    """Crea un usuario normal (role='user') y una sesión autenticada con cookie y CSRF."""
    from app.services.auth_service import auth_service

    user = User(
        email="abogado_asociado@hitchings.com",
        password_hash=hash_password("PasswordSegura123!"),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _, raw_session_token, raw_csrf = auth_service.create_session(db, user)

    client = TestClient(
        from_app := __import__("app.main", fromlist=["app"]).app,
        cookies={settings.SESSION_COOKIE_NAME: raw_session_token},
        headers={"X-CSRF-Token": raw_csrf},
    )
    return client, user, raw_session_token, raw_csrf


# -------------------------------------------------------------
# Tests de Permisos y Endpoints de Prompt Base (GET y PATCH)
# -------------------------------------------------------------

def test_get_base_prompt_authenticated_admin(client: TestClient):
    """Admin autenticado puede consultar el Prompt Base global (HTTP 200)."""
    response = client.get("/api/v1/prompt-settings/base")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "analysis_base_prompt"
    assert "NORMAS INVIOLABLES DE MÁXIMA PRIORIDAD" in data["content"]
    assert "created_at" in data
    assert "updated_at" in data


def test_get_base_prompt_authenticated_user(normal_user_client):
    """Usuario normal autenticado (role='user') puede consultar el Prompt Base global (HTTP 200)."""
    client, _, _, _ = normal_user_client
    response = client.get("/api/v1/prompt-settings/base")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "analysis_base_prompt"
    assert len(data["content"]) > 100


def test_get_base_prompt_unauthenticated_returns_401(unauthenticated_client: TestClient):
    """Acceso anónimo a GET /api/v1/prompt-settings/base es rechazado con HTTP 401."""
    response = unauthenticated_client.get("/api/v1/prompt-settings/base")
    assert response.status_code == 401


def test_patch_base_prompt_authenticated_admin(client: TestClient, db: Session):
    """Admin autenticado puede modificar el Prompt Base global con CSRF válido (HTTP 200)."""
    new_content = "Nueva base estructural jurídica modificada por el socio director de HITCHINGS & GONZÁLEZ."
    response = client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": new_content},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == new_content
    assert data["updated_by_email"] == "test@hitchings.example.com"

    # Verificar en PostgreSQL
    stmt = select(PromptSetting).where(PromptSetting.key == "analysis_base_prompt")
    record = db.execute(stmt).scalar_one()
    assert record.content == new_content


def test_patch_base_prompt_authenticated_user(normal_user_client, db: Session):
    """Usuario normal autenticado (role='user') puede modificar el Prompt Base global con CSRF válido (HTTP 200)."""
    client, user, _, _ = normal_user_client
    new_content = "Prompt base actualizado por abogado del despacho con nuevas directivas probatorias."
    response = client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": new_content},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == new_content
    assert data["updated_by_email"] == user.email


def test_patch_base_prompt_unauthenticated_returns_401(unauthenticated_client: TestClient):
    """Petición anónima a PATCH /api/v1/prompt-settings/base es rechazada con HTTP 401."""
    response = unauthenticated_client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": "Intento de modificación no autorizada"},
    )
    assert response.status_code == 401


def test_patch_base_prompt_without_csrf_returns_403(client: TestClient):
    """Petición sin cabecera X-CSRF-Token es rechazada con HTTP 403 Forbidden."""
    client_no_csrf = TestClient(
        from_app := __import__("app.main", fromlist=["app"]).app,
        cookies=client.cookies,
    )
    response = client_no_csrf.patch(
        "/api/v1/prompt-settings/base",
        json={"content": "Texto sin token CSRF"},
    )
    assert response.status_code == 403


def test_patch_base_prompt_validation_rejects_empty_or_too_short(client: TestClient):
    """Rechaza contenido vacío o inferior a 10 caracteres con HTTP 422."""
    for invalid in ["", "   ", "corto"]:
        response = client.patch(
            "/api/v1/prompt-settings/base",
            json={"content": invalid},
        )
        assert response.status_code == 422


def test_patch_base_prompt_validation_rejects_exceeding_max_length(client: TestClient):
    """Rechaza contenido superior a 30.000 caracteres con HTTP 422."""
    too_long = "a" * 30001
    response = client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": too_long},
    )
    assert response.status_code == 422


def test_patch_base_prompt_updates_timestamp_and_user_id(client: TestClient, db: Session):
    """Verifica que al guardar el Prompt base, updated_at y updated_by_user_id se actualizan."""
    initial = client.get("/api/v1/prompt-settings/base").json()

    updated = client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": "Actualización verificando timestamp y autoría en PostgreSQL."},
    ).json()

    assert updated["content"] != initial["content"]
    assert updated["updated_by_email"] == "test@hitchings.example.com"
    assert updated["updated_at"] >= initial["updated_at"]


# -------------------------------------------------------------
# Tests de Integración con /analysis (Flujo de Ejecución Dinámico)
# -------------------------------------------------------------

def test_analysis_uses_dynamic_base_prompt_from_db_without_redeploy(
    client: TestClient,
    db: Session,
):
    """
    Verifica que cada ejecución de /analysis obtiene en tiempo real el Prompt Base de PostgreSQL.
    Al modificar el Prompt Base en la BD, la siguiente llamada a /analysis pasa la nueva directiva
    a Gemini en system_instruction sin requerir redeploy ni reinicio.
    """
    custom_base = "DIRECTIVA_PERSONALIZADA_TEST: Analizar únicamente cláusulas penales y plazos de caducidad."
    client.patch(
        "/api/v1/prompt-settings/base",
        json={"content": custom_base},
    )

    with patch("app.services.analysis_service.gemini_client") as mock_gemini:
        mock_genai_client = MagicMock()
        mock_gemini.get_client.return_value = mock_genai_client
        mock_genai_client.models.count_tokens.return_value = MagicMock(total_tokens=100)

        mock_interaction = MagicMock()
        mock_interaction.output_text = json.dumps({
            "title": "Análisis Dinámico",
            "content": "Contenido analizado con prompt base dinámico.",
            "warnings": [],
        })
        mock_interaction.usage = MagicMock(total_input_tokens=100, total_output_tokens=50, total_tokens=150)
        mock_genai_client.interactions.create.return_value = mock_interaction

        payload = {
            "text": "Texto documental de prueba sobre cláusula penal de 50.000 euros.",
            "prompt_id": "key-points",
            "options": {"detail_level": "standard", "output_format": "sections"},
        }
        response = client.post("/api/v1/analysis", json=payload)
        assert response.status_code == 200

        # Verificar qué recibió Gemini en system_instruction
        call_kwargs = mock_genai_client.interactions.create.call_args[1]
        assert call_kwargs["system_instruction"] == custom_base
        assert "DIRECTIVA_PERSONALIZADA_TEST" in call_kwargs["system_instruction"]


def test_analysis_fails_fast_when_base_prompt_record_missing(
    client: TestClient,
    db: Session,
):
    """
    Requisito 16 (Fail Fast sin fallback silencioso):
    Si por una anomalía grave no existe el registro de analysis_base_prompt en la BD,
    el sistema NO recurre a una copia vieja hardcodeada en Python: eleva HTTP 500 informando del error.
    """
    # Eliminar deliberadamente el registro de la BD
    db.query(PromptSetting).filter(PromptSetting.key == "analysis_base_prompt").delete()
    db.commit()

    payload = {
        "text": "Texto documental para verificar fail fast.",
        "prompt_id": "key-points",
    }
    response = client.post("/api/v1/analysis", json=payload)
    assert response.status_code == 500
    assert "Prompt Base ('analysis_base_prompt')" in response.json()["detail"]


# -------------------------------------------------------------
# Tests de Transparencia: Guidelines y Preview de Instrucciones
# -------------------------------------------------------------

def test_get_options_guidelines_endpoint(client: TestClient):
    """El endpoint /guidelines retorna las directivas exactas de nivel de detalle y formato."""
    response = client.get("/api/v1/prompt-settings/guidelines")
    assert response.status_code == 200
    data = response.json()
    assert "detail_levels" in data
    assert "output_formats" in data
    assert "brief" in data["detail_levels"]
    assert "standard" in data["detail_levels"]
    assert "detailed" in data["detail_levels"]
    assert "prose" in data["output_formats"]
    assert "sections" in data["output_formats"]
    assert "bullet_points" in data["output_formats"]


def test_preview_effective_instructions_breakdown(client: TestClient):
    """
    Verifica que el preview desglosa con absoluta transparencia:
    1. Prompt Base
    2. Prompt del Tipo seleccionado
    3. Modificador de nivel de detalle
    4. Modificador de formato
    5. Instrucciones específicas adicionales
    Sin incluir documentos, secretos ni configuración interna de Gemini.
    """
    payload = {
        "prompt_id": "legal-analysis",
        "detail_level": "detailed",
        "output_format": "bullet_points",
        "additional_instructions": "Verificar legitimación activa de la mercantil demandante.",
    }
    response = client.post("/api/v1/prompt-settings/preview-instructions", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "NORMAS INVIOLABLES DE MÁXIMA PRIORIDAD" in data["base_prompt"]
    assert data["type_name"] == "Análisis jurídico"
    assert "partes intervinientes" in data["type_instructions"].lower()
    assert "Detallada y exhaustiva" in data["detail_modifier"]
    assert "listas y viñetas" in data["format_modifier"]
    assert data["additional_instructions"] == "Verificar legitimación activa de la mercantil demandante."

    # Composición efectiva
    full_prompt = data["effective_full_prompt"]
    assert "=== 1. PROMPT BASE GLOBAL ===" in full_prompt
    assert "=== 2. PROMPT DEL TIPO DE ANÁLISIS: ANÁLISIS JURÍDICO ===" in full_prompt
    assert "=== 3. MODIFICADORES DE OPCIONES DE SALIDA ===" in full_prompt
    assert "=== 4. INSTRUCCIONES ESPECÍFICAS ADICIONALES DEL USUARIO ===" in full_prompt
    assert "Verificar legitimación activa" in full_prompt

    # Asegurar que no hay secretos ni documentos
    assert "GEMINI_API_KEY" not in full_prompt
    assert "document_content" not in full_prompt


def test_runtime_does_not_use_hardcoded_legal_constant(db: Session, test_user: User):
    """
    Verifica que el builder utiliza exclusivamente la base de PostgreSQL
    y que cambiar la base en PostgreSQL no es sobreescrito por ninguna constante estática.
    """
    custom_content = "Base modificada exclusivamente en PostgreSQL para auditoría de competencia."
    prompt_setting_service.update_base_prompt(
        db=db,
        content=custom_content,
        user=test_user,
    )

    resolved = analysis_prompt_builder.get_system_instruction(db=db)
    assert resolved == custom_content
