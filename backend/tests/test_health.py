"""Automated tests for HydroVision health endpoints and response envelopes."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_health_endpoint():
    """Verify GET /health returns 200 with standard envelope structure."""
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert "data" in payload
    assert "meta" in payload

    # Verify data fields
    data = payload["data"]
    assert data["status"] == "healthy"
    assert data["service"] == "HydroVision Backend"
    assert data["version"] == "0.1.0"
    assert data["database"] == "pending_phase_2"

    # Verify meta fields
    meta = payload["meta"]
    assert "request_id" in meta
    assert meta["request_id"].startswith("req_")
    assert "generated_at" in meta


def test_api_v1_health_endpoint():
    """Verify GET /api/v1/health returns 200 with identical contract."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["data"]["status"] == "healthy"
    assert payload["meta"]["request_id"].startswith("req_")


def test_request_id_header_propagation():
    """Verify incoming X-Request-ID header is propagated in metadata and headers."""
    custom_id = "req_custom_trace_12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200

    assert response.headers.get("X-Request-ID") == custom_id
    payload = response.json()
    assert payload["meta"]["request_id"] == custom_id
