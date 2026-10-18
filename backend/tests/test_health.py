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


def test_cors_preflight_allowed_deployed_frontend_origin():
    """Verify OPTIONS preflight succeeds with 200 and sets headers for the deployed Vercel frontend."""
    vercel_origin = "https://hydrovision-frontend-l6qep861m-hydro-vision2.vercel.app"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": vercel_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type,Authorization,X-Request-ID",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == vercel_origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_preflight_allowed_localhost_origin():
    """Verify OPTIONS preflight succeeds for local development origins."""
    local_origin = "http://localhost:3000"
    response = client.options(
        "/api/v1/dashboard/summary",
        headers={
            "Origin": local_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == local_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_disallowed_origin():
    """Verify OPTIONS preflight is rejected and does not return allow-origin header for untrusted origins."""
    disallowed_origin = "https://untrusted-external-domain.com"
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None
