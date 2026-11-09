"""Tests for /api/v1/health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_healthy(client: AsyncClient, monkeypatch):
    """Health check returns healthy status when database is operational."""
    async def mock_healthy():
        return True, "connected"

    monkeypatch.setattr("api.routers.health.check_db_health", mock_healthy)

    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "environment" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_degraded_when_db_down(client: AsyncClient, monkeypatch):
    """Health check returns 503 degraded status when database is unreachable."""
    async def mock_unhealthy():
        return False, "disconnected: ConnectionRefusedError"

    monkeypatch.setattr("api.routers.health.check_db_health", mock_unhealthy)

    response = await client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "disconnected" in data["database"]
