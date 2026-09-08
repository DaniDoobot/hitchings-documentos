import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.prompts import AnalysisOptions, AnalysisRequest


def test_list_prompts_active_by_default(client: TestClient):
    response = client.get("/api/v1/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert "total" in data
    assert data["total"] == 5
    assert len(data["prompts"]) == 5

    # Comprobar que todos los devueltos están activos
    for p in data["prompts"]:
        assert p["is_active"] is True
        assert p["is_system"] is True


def test_list_prompts_has_stable_ids(client: TestClient):
    response = client.get("/api/v1/prompts")
    assert response.status_code == 200
    ids = [p["id"] for p in response.json()["prompts"]]

    expected_ids = {
        "executive-summary",
        "legal-analysis",
        "key-points",
        "timeline",
        "custom-analysis",
    }
    assert set(ids) == expected_ids


def test_get_specific_prompt_valid(client: TestClient):
    response = client.get("/api/v1/prompts/legal-analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "legal-analysis"
    assert data["name"] == "Análisis jurídico"
    assert "partes intervinientes" in data["instructions"].lower()
    assert data["is_active"] is True
    assert data["is_system"] is True


def test_get_nonexistent_prompt_returns_404(client: TestClient):
    response = client.get("/api/v1/prompts/prompt-fantasma-inexistente")
    assert response.status_code == 404
    assert "No se encontró el prompt" in response.json()["detail"]


def test_list_prompts_include_inactive_flag(client: TestClient):
    response = client.get("/api/v1/prompts?include_inactive=true")
    assert response.status_code == 200
    assert response.json()["total"] >= 5


def test_analysis_options_defaults():
    options = AnalysisOptions()
    assert options.detail_level == "standard"
    assert options.output_format == "sections"
    assert options.additional_instructions is None


def test_analysis_options_valid_custom_values():
    options = AnalysisOptions(
        detail_level="detailed",
        output_format="bullet_points",
        additional_instructions="Centrarse en la prescripción de la acción.",
    )
    assert options.detail_level == "detailed"
    assert options.output_format == "bullet_points"
    assert options.additional_instructions == "Centrarse en la prescripción de la acción."


def test_analysis_options_invalid_detail_level_raises_validation_error():
    with pytest.raises(ValidationError):
        AnalysisOptions(detail_level="ultra-detailed")  # type: ignore


def test_analysis_options_invalid_output_format_raises_validation_error():
    with pytest.raises(ValidationError):
        AnalysisOptions(output_format="xml_table")  # type: ignore


def test_analysis_options_max_additional_instructions_length():
    valid_long_text = "x" * 10000
    options = AnalysisOptions(additional_instructions=valid_long_text)
    assert len(options.additional_instructions) == 10000

    too_long_text = "x" * 10001
    with pytest.raises(ValidationError):
        AnalysisOptions(additional_instructions=too_long_text)


def test_analysis_request_schema_structure():
    req = AnalysisRequest(
        text="Texto legal preparado para análisis.",
        prompt_id="executive-summary",
        options=AnalysisOptions(detail_level="brief", output_format="prose"),
    )
    assert req.text == "Texto legal preparado para análisis."
    assert req.prompt_id == "executive-summary"
    assert req.options.detail_level == "brief"
    assert req.options.output_format == "prose"
