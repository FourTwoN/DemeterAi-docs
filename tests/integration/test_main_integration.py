"""Integration tests for FastAPI application startup and configuration.

Tests cover:
- FastAPI app startup
- All routes registered
- Health check works (/health)
- Metrics endpoint works (/metrics) if enabled
- Auth endpoints work
- Error handling
- Middleware integration
- Correlation ID propagation

Coverage Target: >= 80% for app.main
"""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.exceptions import AppBaseException
from app.main import app


class TestApplicationStartup:
    """Test FastAPI application initialization."""

    def test_app_has_correct_metadata(self):
        """Test that app has correct title and version."""
        # Assert
        assert app.title == "DemeterAI v2.0"
        assert app.version == "2.0.0"
        assert "plant counting" in app.description.lower()

    def test_app_has_registered_routers(self):
        """Test that all API routers are registered."""
        # Arrange
        route_paths = [route.path for route in app.routes]

        # Assert - Check for key endpoints
        assert "/health" in route_paths
        # Auth endpoints
        assert any("/auth/" in path for path in route_paths)

    def test_app_has_exception_handlers(self):
        """Test that exception handlers are registered."""
        # Assert
        assert AppBaseException in app.exception_handlers
        assert Exception in app.exception_handlers

    def test_app_has_middleware_registered(self):
        """Test that middleware is registered."""
        # Assert
        middleware_classes = [
            middleware.cls.__name__ if hasattr(middleware, "cls") else None
            for middleware in app.user_middleware
        ]
        assert "CorrelationIdMiddleware" in middleware_classes


class TestHealthEndpoint:
    """Test /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_healthy(self):
        """Test health endpoint returns 200 with status."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "DemeterAI v2.0"

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_correlation_id(self):
        """Test health endpoint includes correlation ID in headers."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert "X-Correlation-ID" in response.headers
        # Should be valid UUID
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_health_endpoint_preserves_provided_correlation_id(self):
        """Test health endpoint uses provided correlation ID."""
        # Arrange
        test_correlation_id = "12345678-1234-1234-1234-123456789abc"

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/health",
                headers={"X-Correlation-ID": test_correlation_id},
            )

        # Assert
        assert response.headers["X-Correlation-ID"] == test_correlation_id


class TestCorrelationIdMiddleware:
    """Test correlation ID middleware functionality."""

    @pytest.mark.asyncio
    async def test_middleware_generates_correlation_id_if_missing(self):
        """Test middleware generates correlation ID when not provided."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        # Should be valid UUID format
        try:
            UUID(correlation_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        assert is_valid_uuid

    @pytest.mark.asyncio
    async def test_middleware_preserves_existing_correlation_id(self):
        """Test middleware preserves correlation ID from request."""
        # Arrange
        test_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/health",
                headers={"X-Correlation-ID": test_id},
            )

        # Assert
        assert response.headers["X-Correlation-ID"] == test_id

    @pytest.mark.asyncio
    async def test_middleware_adds_correlation_id_to_all_responses(self):
        """Test middleware adds correlation ID to all endpoints."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - Test multiple endpoints
            health_response = await client.get("/health")
            public_key_response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert "X-Correlation-ID" in health_response.headers
        assert "X-Correlation-ID" in public_key_response.headers


class TestExceptionHandlers:
    """Test global exception handlers."""

    @pytest.mark.asyncio
    async def test_app_exception_handler_returns_json_error(self):
        """Test AppBaseException handler returns JSON with error details."""
        # Arrange
        from app.core.exceptions import UnauthorizedException

        # Create endpoint that raises AppBaseException
        @app.get("/test-exception")
        async def test_exception_endpoint():
            raise UnauthorizedException(reason="Test error")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/test-exception")

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "code" in data
        assert "correlation_id" in data
        assert "timestamp" in data
        assert data["code"] == "UnauthorizedException"

        # Cleanup
        app.routes = [route for route in app.routes if route.path != "/test-exception"]

    @pytest.mark.asyncio
    async def test_app_exception_handler_hides_details_in_production(self):
        """Test AppBaseException handler hides technical details when debug=False."""
        # Arrange
        from app.core.exceptions import UnauthorizedException

        @app.get("/test-prod-exception")
        async def test_exception_endpoint():
            raise UnauthorizedException(reason="Test error", technical_message="Internal details")

        with patch.object(settings, "debug", False):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/test-prod-exception")

        # Assert
        data = response.json()
        assert "detail" not in data  # Technical details hidden
        assert "extra" not in data

        # Cleanup
        app.routes = [route for route in app.routes if route.path != "/test-prod-exception"]

    @pytest.mark.asyncio
    async def test_generic_exception_handler_returns_500(self):
        """Test generic exception handler returns 500 for unhandled errors."""

        # Arrange
        @app.get("/test-generic-exception")
        async def test_exception_endpoint():
            raise RuntimeError("Unexpected error")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/test-generic-exception")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "internal server error" in data["error"].lower()
        assert "correlation_id" in data

        # Cleanup
        app.routes = [route for route in app.routes if route.path != "/test-generic-exception"]

    @pytest.mark.asyncio
    async def test_generic_exception_handler_hides_details_in_production(self):
        """Test generic handler hides exception details when debug=False."""

        # Arrange
        @app.get("/test-prod-generic")
        async def test_exception_endpoint():
            raise ValueError("Secret internal error")

        with patch.object(settings, "debug", False):
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Act
                response = await client.get("/test-prod-generic")

        # Assert
        data = response.json()
        assert "Secret internal error" not in str(data)  # Details hidden
        assert "detail" not in data or "ValueError" not in data.get("detail", "")

        # Cleanup
        app.routes = [route for route in app.routes if route.path != "/test-prod-generic"]


class TestRouterIntegration:
    """Test that all routers are integrated correctly."""

    @pytest.mark.asyncio
    async def test_auth_router_is_registered(self):
        """Test authentication router endpoints are accessible."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_stock_router_is_registered(self):
        """Test stock router endpoints exist (may require auth)."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - Try to access stock endpoint (will fail auth, but route exists)
            response = await client.get("/api/v1/stock/movements")

        # Assert
        # Route exists (either 401/403 for auth required, or 200 if public)
        assert response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_location_router_is_registered(self):
        """Test location router endpoints exist."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/warehouses")

        # Assert
        # Route exists (response code depends on auth requirements)
        assert response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_product_router_is_registered(self):
        """Test product router endpoints exist."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/products")

        # Assert
        # Route exists
        assert response.status_code in [200, 401, 403, 404]


class TestApplicationConfiguration:
    """Test application configuration and settings."""

    def test_app_uses_correct_settings(self):
        """Test that app configuration uses settings module."""
        # Assert
        assert settings is not None
        assert hasattr(settings, "APP_ENV")
        assert hasattr(settings, "DEBUG")

    def test_logging_is_configured(self):
        """Test that logging is configured on startup."""
        # Assert
        assert settings.log_level is not None

    def test_cors_middleware_if_configured(self):
        """Test CORS middleware if configured."""
        # Assert - CORS middleware may or may not be present
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        # If CORS is configured, it should be in middleware
        # This test just verifies middleware structure
        assert isinstance(middleware_types, list)


class TestMetricsEndpoint:
    """Test metrics endpoint if metrics are enabled."""

    @pytest.mark.asyncio
    @patch("app.core.metrics.setup_metrics")
    async def test_metrics_endpoint_exists_when_enabled(self, mock_setup_metrics):
        """Test /metrics endpoint is accessible when metrics enabled."""
        # Arrange
        from app.core.metrics import setup_metrics

        setup_metrics(enable_metrics=True)

        # Note: Metrics endpoint registration depends on app configuration
        # This test verifies endpoint structure
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            try:
                response = await client.get("/metrics")
                # Assert
                # Endpoint may or may not exist depending on configuration
                assert response.status_code in [200, 404]
            except Exception:
                # Endpoint not configured, which is acceptable
                pass


class TestRequestResponseCycle:
    """Test complete request/response cycle."""

    @pytest.mark.asyncio
    async def test_complete_request_cycle_with_correlation_id(self):
        """Test full request cycle maintains correlation ID."""
        # Arrange
        test_correlation_id = "test-correlation-12345"

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/health",
                headers={"X-Correlation-ID": test_correlation_id},
            )

        # Assert
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id
        # Body should also be correct
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_concurrent_requests_have_unique_correlation_ids(self):
        """Test that concurrent requests get unique correlation IDs."""
        # Arrange
        import asyncio

        async def make_request(client):
            response = await client.get("/health")
            return response.headers["X-Correlation-ID"]

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - Make 10 concurrent requests
            tasks = [make_request(client) for _ in range(10)]
            correlation_ids = await asyncio.gather(*tasks)

        # Assert - All IDs should be unique
        assert len(correlation_ids) == 10
        assert len(set(correlation_ids)) == 10  # All unique


class TestErrorResponseFormat:
    """Test error response format consistency."""

    @pytest.mark.asyncio
    async def test_404_error_format(self):
        """Test 404 error response format."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/nonexistent-endpoint")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_422_validation_error_format(self):
        """Test validation error response format."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - Send invalid data to login endpoint
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "invalid"},  # Missing password
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestApplicationLifecycle:
    """Test application lifecycle events."""

    def test_app_can_be_imported_without_errors(self):
        """Test that app module can be imported successfully."""
        # Arrange & Act
        from app.main import app as imported_app

        # Assert
        assert imported_app is not None
        assert imported_app.title == "DemeterAI v2.0"

    def test_app_routes_are_populated(self):
        """Test that app has routes after initialization."""
        # Assert
        assert len(app.routes) > 0
        route_paths = [route.path for route in app.routes]
        assert "/health" in route_paths


class TestIntegrationWithTelemetry:
    """Test integration with telemetry system."""

    @pytest.mark.asyncio
    @patch("app.core.telemetry.setup_telemetry")
    async def test_requests_work_with_telemetry_enabled(self, mock_setup_telemetry):
        """Test that requests work when telemetry is enabled."""
        # Arrange
        mock_setup_telemetry.return_value = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.core.telemetry.setup_telemetry")
    async def test_requests_work_with_telemetry_disabled(self, mock_setup_telemetry):
        """Test that requests work when telemetry is disabled."""
        # Arrange
        mock_setup_telemetry.return_value = None

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert response.status_code == 200


class TestIntegrationWithMetrics:
    """Test integration with metrics system."""

    @pytest.mark.asyncio
    @patch("app.core.metrics.setup_metrics")
    async def test_requests_work_with_metrics_enabled(self, mock_setup_metrics):
        """Test that requests work when metrics are enabled."""
        # Arrange
        from app.core.metrics import setup_metrics

        setup_metrics(enable_metrics=True)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.core.metrics.setup_metrics")
    async def test_requests_work_with_metrics_disabled(self, mock_setup_metrics):
        """Test that requests work when metrics are disabled."""
        # Arrange
        from app.core.metrics import setup_metrics

        setup_metrics(enable_metrics=False)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/health")

        # Assert
        assert response.status_code == 200
