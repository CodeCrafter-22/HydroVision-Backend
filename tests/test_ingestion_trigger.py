"""Automated test suite for HydroVision n8n ingestion trigger and worker pipeline."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.ingestion_trigger import IngestionTriggerRequest
from app.workers.geo_utils import parse_ewkb_point
from app.workers.ingestion_worker import (
    run_ingestion_job,
    send_wf03_failure_callback,
)

client = TestClient(app)
VALID_TOKEN = "test-secret-worker-token"
SAMPLE_EWKB = "0101000020e6100000a4703d0ad7a352409a99999999d93040"  # (74.56, 16.85)


@pytest.fixture(autouse=True)
def setup_test_token(monkeypatch):
    """Ensure worker token is configured for all tests."""
    monkeypatch.setattr(settings, "INGESTION_WORKER_TOKEN", VALID_TOKEN)


# ------------------------------------------------------------------------------
# 1. Trigger Endpoint Authentication & Validation Tests
# ------------------------------------------------------------------------------


def test_trigger_missing_token():
    """Verify HTTP 401 when X-Worker-Token is missing."""
    payload = {
        "active_source": "open_meteo",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00Z",
    }
    response = client.post("/api/v1/ingestion/trigger", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_trigger_invalid_token():
    """Verify HTTP 401 when X-Worker-Token is incorrect."""
    payload = {
        "active_source": "open_meteo",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00Z",
    }
    response = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": "wrong-token"},
        json=payload,
    )
    assert response.status_code == 401


def test_trigger_unsupported_source():
    """Verify HTTP 422 when active_source is not in confirmed list."""
    payload = {
        "active_source": "unknown_provider",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00Z",
    }
    response = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": VALID_TOKEN},
        json=payload,
    )
    assert response.status_code == 422


def test_trigger_naive_timestamp_rejected():
    """Verify HTTP 422 when timestamp lacks timezone."""
    payload = {
        "active_source": "open_meteo",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00",  # Naive
    }
    response = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": VALID_TOKEN},
        json=payload,
    )
    assert response.status_code == 422


def test_trigger_successful_acknowledgement():
    """Verify HTTP 202 Accepted with canonical response shape."""
    payload = {
        "active_source": "cwc_gauge",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00Z",
    }
    response = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": VALID_TOKEN},
        json=payload,
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "cwc_gauge" in data["message"]
    assert data["execution_id"].startswith("job_")


def test_trigger_generates_unique_execution_ids():
    """Verify distinct execution IDs are generated for consecutive requests."""
    payload = {
        "active_source": "open_meteo",
        "is_fallback": False,
        "triggered_at": "2026-10-11T18:19:00Z",
    }
    resp1 = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": VALID_TOKEN},
        json=payload,
    )
    resp2 = client.post(
        "/api/v1/ingestion/trigger",
        headers={"X-Worker-Token": VALID_TOKEN},
        json=payload,
    )
    assert resp1.status_code == 202
    assert resp2.status_code == 202
    assert resp1.json()["execution_id"] != resp2.json()["execution_id"]


# ------------------------------------------------------------------------------
# 2. EWKB Geometry Parser Unit Tests
# ------------------------------------------------------------------------------


def test_parse_ewkb_point_valid():
    """Verify valid EWKB hex string extracts correct lon/lat."""
    coords = parse_ewkb_point(SAMPLE_EWKB)
    assert coords is not None
    lon, lat = coords
    assert pytest.approx(lon, 0.01) == 74.56
    assert pytest.approx(lat, 0.01) == 16.85


def test_parse_ewkb_point_geojson_fallback():
    """Verify parser handles GeoJSON dictionary fallback."""
    geojson = {"type": "Point", "coordinates": [74.56, 16.85]}
    coords = parse_ewkb_point(geojson)
    assert coords == (74.56, 16.85)


def test_parse_ewkb_point_null_and_corrupt():
    """Verify parser handles None, invalid types, and corrupt hex cleanly."""
    assert parse_ewkb_point(None) is None
    assert parse_ewkb_point("") is None
    assert parse_ewkb_point("not-hex") is None
    assert parse_ewkb_point("0101") is None  # Too short


# ------------------------------------------------------------------------------
# 3. Worker Ingestion Pipeline Unit Tests
# ------------------------------------------------------------------------------


def test_worker_cwc_gauge_fails_explicitly():
    """Verify cwc_gauge logs status=down and triggers failure callback."""
    async def _test():
        req = IngestionTriggerRequest(
            active_source="cwc_gauge",
            is_fallback=False,
            triggered_at=datetime.now(timezone.utc),
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": 1}])
        )

        with patch(
            "app.workers.ingestion_worker.get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.workers.ingestion_worker.send_wf03_failure_callback",
            new_callable=AsyncMock,
        ) as mock_cb:
            result = await run_ingestion_job(execution_id="job_cwc_test", request=req)

            assert result["status"] == "down"
            assert "explicitly non-operational" in result["error"]
            mock_cb.assert_called_once()
            assert mock_cb.call_args.kwargs["is_fallback"] is False

    asyncio.run(_test())


def test_worker_nasa_gpm_deferred_fails_explicitly():
    """Verify nasa_gpm logs status=down and triggers failure callback."""
    async def _test():
        req = IngestionTriggerRequest(
            active_source="nasa_gpm",
            is_fallback=True,
            triggered_at=datetime.now(timezone.utc),
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": 1}])
        )

        with patch(
            "app.workers.ingestion_worker.get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.workers.ingestion_worker.send_wf03_failure_callback",
            new_callable=AsyncMock,
        ) as mock_cb:
            result = await run_ingestion_job(execution_id="job_nasa_test", request=req)

            assert result["status"] == "down"
            assert "explicitly deferred" in result["error"]
            mock_cb.assert_called_once()
            assert mock_cb.call_args.kwargs["is_fallback"] is True

    asyncio.run(_test())


def test_worker_open_meteo_success_and_deduplication():
    """Verify Open-Meteo fetches, validates, deduplicates, and saves."""
    async def _test():
        req = IngestionTriggerRequest(
            active_source="open_meteo",
            is_fallback=False,
            triggered_at=datetime.now(timezone.utc),
        )

        village = {
            "id": "11111111-1111-1111-1111-111111111111",
            "code": "VIL-001",
            "name": "Sangli Test",
            "geom": SAMPLE_EWKB,
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[village])
        )

        select_query = mock_supabase.table.return_value.select.return_value
        select_query.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        mock_readings = [
            {
                "gauge_id": None,
                "observed_at": datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc),
                "level_m": None,
                "discharge_m3s": 150.5,
                "quality": "good",
                "raw_payload": {"model": "GloFAS"},
            }
        ]

        with patch(
            "app.workers.ingestion_worker.get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.workers.ingestion_worker.fetch_open_meteo_flood",
            new_callable=AsyncMock,
            return_value=mock_readings,
        ):
            result = await run_ingestion_job(execution_id="job_om_test", request=req)

            assert result["status"] == "healthy"
            assert result["records_fetched"] == 1
            assert result["records_inserted"] == 1
            assert result["records_deduplicated"] == 0

            # Test deduplication on subsequent run: mock existing reading found
            select_query.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": 101}]
            )
            dedup_result = await run_ingestion_job(
                execution_id="job_om_dedup", request=req
            )
            assert dedup_result["records_deduplicated"] == 1
            assert dedup_result["records_inserted"] == 0

    asyncio.run(_test())


def test_worker_open_meteo_missing_coordinates():
    """Verify village with NULL geom is skipped and marked degraded."""
    async def _test():
        req = IngestionTriggerRequest(
            active_source="open_meteo",
            is_fallback=False,
            triggered_at=datetime.now(timezone.utc),
        )

        village = {
            "id": "22222222-2222-2222-2222-222222222222",
            "code": "VIL-002",
            "name": "No Coords Village",
            "geom": None,
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[village])
        )

        with patch(
            "app.workers.ingestion_worker.get_supabase_client",
            return_value=mock_supabase,
        ):
            result = await run_ingestion_job(execution_id="job_null_geom", request=req)

            assert result["status"] == "degraded"
            assert len(result["village_errors"]) == 1
            assert "Missing or unparseable" in result["village_errors"][0]["error"]

    asyncio.run(_test())


def test_worker_database_and_health_logging_failure_isolation():
    """Verify that a health logging failure does not mask original ingestion error."""
    async def _test():
        req = IngestionTriggerRequest(
            active_source="open_meteo",
            is_fallback=False,
            triggered_at=datetime.now(timezone.utc),
        )

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.execute.side_effect = (
            RuntimeError("Database pool connection lost")
        )
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = (
            RuntimeError("Health table unreachable")
        )

        with patch(
            "app.workers.ingestion_worker.get_supabase_client",
            return_value=mock_supabase,
        ), patch(
            "app.workers.ingestion_worker.send_wf03_failure_callback",
            new_callable=AsyncMock,
        ) as mock_cb:
            result = await run_ingestion_job(execution_id="job_err_test", request=req)

            assert result["status"] == "down"
            assert "Database pool connection lost" in result["error"]
            mock_cb.assert_called_once()

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# 4. WF-03 Failure Callback Unit Tests
# ------------------------------------------------------------------------------


def test_wf03_callback_unconfigured(monkeypatch):
    """Verify callback is safely skipped if WF03_CALLBACK_URL is empty."""
    async def _test():
        monkeypatch.setattr(settings, "WF03_CALLBACK_URL", "")
        success = await send_wf03_failure_callback(
            is_fallback=False, error_message="Test failure"
        )
        assert success is False

    asyncio.run(_test())


def test_wf03_callback_success(monkeypatch):
    """Verify callback delivers JSON payload and returns True on HTTP 200."""
    async def _test():
        monkeypatch.setattr(
            settings, "WF03_CALLBACK_URL", "https://n8n.test/webhook/wf03"
        )

        mock_resp = MagicMock(is_success=True, status_code=200)
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            success = await send_wf03_failure_callback(
                is_fallback=True, error_message="Simulated failure"
            )
            assert success is True
            mock_post.assert_called_once()
            sent_body = mock_post.call_args.kwargs["json"]
            assert sent_body["status"] == "failed"
            assert sent_body["is_fallback"] is True
            assert sent_body["message"] == "Simulated failure"

    asyncio.run(_test())


def test_wf03_callback_timeout_handled(monkeypatch):
    """Verify callback timeout does not crash and returns False."""
    async def _test():
        monkeypatch.setattr(
            settings, "WF03_CALLBACK_URL", "https://n8n.test/webhook/wf03"
        )

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Connection timed out"),
        ):
            success = await send_wf03_failure_callback(
                is_fallback=False, error_message="Timeout test"
            )
            assert success is False

    asyncio.run(_test())


# ------------------------------------------------------------------------------
# 5. Regression Tests for Existing Ingestion Endpoints
# ------------------------------------------------------------------------------


def test_regression_gauge_reading_endpoint():
    """Verify POST /api/v1/ingestion/gauge-readings preserves original behavior."""
    payload = {
        "village_id": "11111111-1111-1111-1111-111111111111",
        "source": "cwc",
        "gauge_id": "G-01",
        "observed_at": "2026-10-11T12:00:00Z",
        "level_m": 4.5,
    }

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        MagicMock(data=[{"id": 1, **payload}])
    )

    with patch(
        "app.api.v1.ingestion.get_supabase_client", return_value=mock_supabase
    ):
        resp = client.post(
            "/api/v1/ingestion/gauge-readings",
            headers={"X-Worker-Token": VALID_TOKEN},
            json=payload,
        )
        assert resp.status_code == 201
        assert resp.json()["level_m"] == 4.5


def test_regression_rain_reading_endpoint():
    """Verify POST /api/v1/ingestion/rain-readings preserves original behavior."""
    payload = {
        "village_id": "11111111-1111-1111-1111-111111111111",
        "source": "aws",
        "observed_at": "2026-10-11T12:00:00Z",
        "rain_mm": 25.0,
        "accumulation_minutes": 60,
    }

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        MagicMock(data=[{"id": 2, **payload}])
    )

    with patch(
        "app.api.v1.ingestion.get_supabase_client", return_value=mock_supabase
    ):
        resp = client.post(
            "/api/v1/ingestion/rain-readings",
            headers={"X-Worker-Token": VALID_TOKEN},
            json=payload,
        )
        assert resp.status_code == 201
        assert resp.json()["rain_mm"] == 25.0


def test_regression_source_health_endpoint():
    """Verify POST /api/v1/ingestion/source-health preserves original behavior."""
    payload = {
        "source": "open-meteo",
        "status": "healthy",
        "last_checked_at": "2026-10-11T12:00:00Z",
        "is_backup_active": False,
    }

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        MagicMock(data=[{"id": 3, **payload}])
    )

    with patch(
        "app.api.v1.ingestion.get_supabase_client", return_value=mock_supabase
    ):
        resp = client.post(
            "/api/v1/ingestion/source-health",
            headers={"X-Worker-Token": VALID_TOKEN},
            json=payload,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "healthy"
