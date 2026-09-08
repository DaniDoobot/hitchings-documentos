import logging
from fastapi.testclient import TestClient

from app.core.config import settings


def test_prepare_text_valid(client: TestClient):
    raw_input = "   Este es un texto legal con espacios y saltos.\r\n\r\nSegunda línea.   "
    response = client.post("/api/v1/text/prepare", json={"text": raw_input})

    assert response.status_code == 200
    data = response.json()
    assert "Este es un texto legal con espacios y saltos." in data["text"]
    assert "Segunda línea." in data["text"]
    assert data["word_count"] > 0
    assert data["character_count"] == len(data["text"])


def test_prepare_text_empty_returns_400(client: TestClient):
    response = client.post("/api/v1/text/prepare", json={"text": ""})
    assert response.status_code == 400
    assert "está vacío" in response.json()["detail"]


def test_prepare_text_whitespace_only_returns_400(client: TestClient):
    response = client.post("/api/v1/text/prepare", json={"text": "   \n\t  \r\n   "})
    assert response.status_code == 400
    assert "está vacío" in response.json()["detail"]


def test_prepare_text_exceeds_max_characters_returns_413(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "MAX_TEXT_CHARACTERS", 100)
    oversized_text = "A" * 101

    response = client.post("/api/v1/text/prepare", json={"text": oversized_text})
    assert response.status_code == 413
    assert "excede el límite máximo" in response.json()["detail"]


def test_prepare_text_conservative_normalization(client: TestClient):
    raw_input = "Línea 1 con espacios al final    \r\n\r\n\r\n\r\nLínea 2 tras múltiples saltos."
    response = client.post("/api/v1/text/prepare", json={"text": raw_input})

    assert response.status_code == 200
    data = response.json()
    assert "\n\n\n" not in data["text"]
    assert "Línea 1 con espacios al final\n\nLínea 2 tras múltiples saltos." == data["text"]


def test_prepare_text_word_and_character_counts(client: TestClient):
    sample = "Uno dos tres cuatro cinco."
    response = client.post("/api/v1/text/prepare", json={"text": sample})

    assert response.status_code == 200
    data = response.json()
    assert data["word_count"] == 5
    assert data["character_count"] == 26


def test_prepare_text_confidentiality_logs_do_not_contain_text(client: TestClient, caplog):
    secret_text = "Secreto confidencial: Cláusula secreta número 987654321 de la empresa XYZ."

    with caplog.at_level(logging.INFO):
        response = client.post("/api/v1/text/prepare", json={"text": secret_text})

    assert response.status_code == 200
    # Comprobar que en los logs técnicos NO aparece el contenido
    assert "Cláusula secreta número 987654321" not in caplog.text
    assert "empresa XYZ" not in caplog.text
    # Comprobar que sí aparecen métricas técnicas seguras
    assert "Texto preparado con éxito" in caplog.text
    assert "Caracteres recibidos:" in caplog.text
