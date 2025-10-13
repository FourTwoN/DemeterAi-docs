"""Integration tests for health check endpoint.

These tests verify the /health endpoint works correctly with:
- FastAPI test client
- Middleware (correlation ID)
- Response headers
"""

import pytest


@pytest.mark.integration
async def test_health_endpoint_returns_200(client):
    """Test health endpoint returns 200 OK."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "DemeterAI v2.0"


@pytest.mark.integration
async def test_health_endpoint_includes_correlation_id(client):
    """Test health endpoint returns correlation ID in headers."""
    response = await client.get("/health")

    assert "X-Correlation-ID" in response.headers
    correlation_id = response.headers["X-Correlation-ID"]
    assert len(correlation_id) == 36  # UUID format


@pytest.mark.integration
async def test_health_endpoint_with_custom_correlation_id(client):
    """Test health endpoint accepts custom correlation ID."""
    custom_id = "test-correlation-123"

    response = await client.get("/health", headers={"X-Correlation-ID": custom_id})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_id
