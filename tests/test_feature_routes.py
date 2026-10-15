
"""Automated tests for HydroVision feature routes."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_summary_route_is_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/dashboard/summary" in paths


def test_gauge_readings_route_is_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/readings/gauges" in paths


def test_alert_routes_are_registered():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/alerts" in paths
    assert "/api/v1/alerts/{alert_id}/approve" in paths
    assert "/api/v1/alerts/{alert_id}/reject" in paths


def test_gauge_readings_reject_invalid_date_range():
    response = client.get(
        "/api/v1/readings/gauges",
        params={
            "start_at": "2026-10-15T12:00:00Z",
            "end_at": "2026-10-10T12:00:00Z",
        },
    )

    assert response.status_code == 422


def test_alert_creation_rejects_invalid_tier():
    response = client.post(
        "/api/v1/alerts",
        json={
            "village_code": "HV-TEST-001",
            "tier": "INVALID",
            "edited_message": "Test alert",
            "is_simulated": True,
        },
    )

    assert response.status_code == 422