import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_cors_preflight_allowed_origin(client):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/v1/prompts", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_get_allowed_origin(client):
    headers = {"Origin": "http://localhost:5173"}
    response = client.get("/api/v1/prompts", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_disallowed_origin(client):
    headers = {"Origin": "http://malicious-site.example.com"}
    response = client.get("/api/v1/prompts", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
