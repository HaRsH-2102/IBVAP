"""
IBVAP Backend Tests — API Foundation Validation
================================================
Tests the implemented API endpoints (health, status, WebSocket boundary).
These are the only endpoints that actually return data in Milestone 1.

All other routes return 501 — we verify that behavior too.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        response = await client.get("/api/v1/system/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client: AsyncClient):
        response = await client.get("/api/v1/system/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "service" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data
        assert "websocket" in data


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------

class TestSystemStatusEndpoint:
    @pytest.mark.asyncio
    async def test_status_returns_200(self, client: AsyncClient):
        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_status_response_structure(self, client: AsyncClient):
        response = await client.get("/api/v1/system/status")
        data = response.json()
        assert data["milestone"] == 1
        assert "capabilities" in data
        assert "configuration" in data

    @pytest.mark.asyncio
    async def test_status_capabilities_all_future(self, client: AsyncClient):
        response = await client.get("/api/v1/system/status")
        caps = response.json()["capabilities"]
        for cap_name, cap_info in caps.items():
            assert cap_info["status"] == "not_implemented", (
                f"Capability '{cap_name}' should be 'not_implemented' in Milestone 1"
            )
            assert "milestone" in cap_info


# ---------------------------------------------------------------------------
# Stub endpoints return 501
# ---------------------------------------------------------------------------

class TestStubEndpointsReturn501:
    @pytest.mark.asyncio
    async def test_cameras_list_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/cameras")
        assert response.status_code == 501
        data = response.json()
        assert data["status"] == "not_implemented"

    @pytest.mark.asyncio
    async def test_events_list_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/events")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_alerts_list_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_zones_list_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/zones")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_camera_detail_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/cameras/cam-001")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_event_detail_returns_501(self, client: AsyncClient):
        response = await client.get("/api/v1/events/evt-001")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_alert_ack_returns_501(self, client: AsyncClient):
        response = await client.patch("/api/v1/alerts/alert-001/ack")
        assert response.status_code == 501


# ---------------------------------------------------------------------------
# No fake data returned anywhere
# ---------------------------------------------------------------------------

class TestNoFakeData:
    @pytest.mark.asyncio
    async def test_cameras_does_not_return_fake_cameras(self, client: AsyncClient):
        """Cameras endpoint must NOT return fake camera data — only 501."""
        response = await client.get("/api/v1/cameras")
        assert response.status_code == 501
        # Make absolutely sure there's no 'cameras' list with fake entries
        data = response.json()
        assert "cameras" not in data

    @pytest.mark.asyncio
    async def test_events_does_not_return_fake_events(self, client: AsyncClient):
        """Events endpoint must NOT return fake detection data."""
        response = await client.get("/api/v1/events")
        assert response.status_code == 501
        data = response.json()
        assert "events" not in data

    @pytest.mark.asyncio
    async def test_alerts_does_not_return_fake_alerts(self, client: AsyncClient):
        """Alerts endpoint must NOT return fake alert data."""
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 501
        data = response.json()
        assert "alerts" not in data
