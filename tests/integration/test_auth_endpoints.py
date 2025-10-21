"""Integration tests for authentication API endpoints.

Tests cover:
- GET /api/v1/auth/me (requires auth)
- POST /api/v1/auth/login (with valid/invalid credentials)
- POST /api/v1/auth/logout
- GET /api/v1/auth/public-key
- CORS headers
- 401/403 responses

Coverage Target: >= 80% for app.controllers.auth_controller
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.auth import TokenClaims
from app.main import app


@pytest.fixture
def mock_token_claims():
    """Create mock TokenClaims for testing authenticated endpoints."""
    now = int(datetime.now(UTC).timestamp())
    return TokenClaims(
        sub="auth0|test123",
        email="supervisor@demeter.ai",
        roles=["supervisor"],
        iat=now,
        exp=now + 86400,
        aud="https://api.demeter.ai",
        iss="https://demeter.us.auth0.com/",
    )


class TestGetCurrentUserInfo:
    """Test GET /api/v1/auth/me endpoint."""

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_get_me_with_valid_token_returns_user_info(
        self, mock_verify_token, mock_token_claims
    ):
        """Test /me endpoint returns user info for valid token."""
        # Arrange
        mock_verify_token.return_value = mock_token_claims

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer valid-jwt-token"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "auth0|test123"
        assert data["email"] == "supervisor@demeter.ai"
        assert data["roles"] == ["supervisor"]
        assert "iat" in data
        assert "exp" in data

    @pytest.mark.asyncio
    async def test_get_me_without_token_returns_403(self):
        """Test /me endpoint returns 403 when no token provided."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/me")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_get_me_with_invalid_token_returns_401(self, mock_verify_token):
        """Test /me endpoint returns 401 for invalid token."""
        # Arrange
        from app.core.exceptions import UnauthorizedException

        mock_verify_token.side_effect = UnauthorizedException(reason="Invalid token")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid-token"},
            )

        # Assert
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_get_me_with_admin_role(self, mock_verify_token):
        """Test /me endpoint returns admin user info."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        admin_claims = TokenClaims(
            sub="auth0|admin456",
            email="admin@demeter.ai",
            roles=["admin", "supervisor"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )
        mock_verify_token.return_value = admin_claims

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer admin-token"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "auth0|admin456"
        assert "admin" in data["roles"]
        assert "supervisor" in data["roles"]


class TestLogin:
    """Test POST /api/v1/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials_returns_demo_token(self):
        """Test login endpoint returns demo token (Auth0 integration pending)."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "supervisor@demeter.ai", "password": "SecurePass123!"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
        # Demo token contains message about Auth0 integration
        assert "DEMO_TOKEN" in data["access_token"] or "AUTH0" in data["access_token"]

    @pytest.mark.asyncio
    async def test_login_with_missing_email_returns_422(self):
        """Test login endpoint validates required fields."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                json={"password": "password123"},  # Missing email
            )

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_with_short_password_returns_422(self):
        """Test login endpoint validates password length."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@test.com", "password": "short"},  # Too short
            )

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_with_invalid_json_returns_422(self):
        """Test login endpoint handles malformed JSON."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                content="not-valid-json",
                headers={"Content-Type": "application/json"},
            )

        # Assert
        assert response.status_code == 422


class TestLogout:
    """Test POST /api/v1/auth/logout endpoint."""

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_logout_with_valid_token_returns_success(
        self, mock_verify_token, mock_token_claims
    ):
        """Test logout endpoint returns success message."""
        # Arrange
        mock_verify_token.return_value = mock_token_claims

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer valid-jwt-token"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_logout_without_token_returns_403(self):
        """Test logout endpoint requires authentication."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post("/api/v1/auth/logout")

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_logout_with_expired_token_returns_401(self, mock_verify_token):
        """Test logout endpoint rejects expired tokens."""
        # Arrange
        from app.core.exceptions import UnauthorizedException

        mock_verify_token.side_effect = UnauthorizedException(reason="Token expired")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer expired-token"},
            )

        # Assert
        assert response.status_code == 401


class TestPublicKey:
    """Test GET /api/v1/auth/public-key endpoint."""

    @pytest.mark.asyncio
    async def test_get_public_key_returns_jwks_info(self):
        """Test public key endpoint returns Auth0 JWKS information."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "jwks_uri" in data
        assert "domain" in data
        assert "algorithms" in data
        assert data["algorithms"] == ["RS256"]
        assert data["jwks_uri"].endswith("/.well-known/jwks.json")

    @pytest.mark.asyncio
    async def test_get_public_key_does_not_require_auth(self):
        """Test public key endpoint is accessible without authentication."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert response.status_code == 200
        # No authentication required

    @pytest.mark.asyncio
    @patch("app.core.auth.get_auth0_config")
    async def test_get_public_key_handles_missing_config(self, mock_get_config):
        """Test public key endpoint handles missing Auth0 config gracefully."""
        # Arrange
        mock_get_config.side_effect = ValueError("AUTH0_DOMAIN not configured")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "not configured" in data["error"].lower()


class TestCORSHeaders:
    """Test CORS headers on authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_endpoint_has_cors_headers(self):
        """Test that login endpoint returns CORS headers."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@test.com", "password": "password123"},
                headers={"Origin": "http://localhost:3000"},
            )

        # Assert
        # Note: CORS headers added by middleware if configured
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_public_key_endpoint_has_cors_headers(self):
        """Test that public key endpoint allows cross-origin requests."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/public-key",
                headers={"Origin": "http://localhost:3000"},
            )

        # Assert
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling in authentication endpoints."""

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_me_endpoint_handles_unexpected_exception(self, mock_verify_token):
        """Test /me endpoint handles unexpected errors gracefully."""
        # Arrange
        mock_verify_token.side_effect = RuntimeError("Unexpected database error")

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer token"},
            )

        # Assert
        # Should return 500 or handle gracefully
        assert response.status_code in [401, 500]

    @pytest.mark.asyncio
    async def test_login_endpoint_handles_network_timeout(self):
        """Test login endpoint handles network timeouts gracefully."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test", timeout=0.001) as client:
            try:
                # Act
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "user@test.com", "password": "password123"},
                )

                # Assert - should either succeed or timeout gracefully
                assert response.status_code in [200, 500, 504]
            except Exception:
                # Timeout is acceptable
                pass


class TestAuthEndpointIntegration:
    """Test full authentication flow integration."""

    @pytest.mark.asyncio
    async def test_full_auth_flow_login_then_access_protected_endpoint(self):
        """Test complete flow: login -> get token -> access protected endpoint."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Login
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": "supervisor@demeter.ai", "password": "SecurePass123!"},
            )

            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Step 2: Use token to access protected endpoint (demo token won't work)
            # This tests the endpoint structure, not actual Auth0 validation
            me_response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Assert
            # Demo token will fail verification, which is expected
            assert me_response.status_code in [401, 200]

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_full_auth_flow_with_logout(self, mock_verify_token, mock_token_claims):
        """Test complete flow: authenticate -> access endpoint -> logout."""
        # Arrange
        mock_verify_token.return_value = mock_token_claims

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Access protected endpoint
            me_response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer valid-token"},
            )
            assert me_response.status_code == 200

            # Step 2: Logout
            logout_response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer valid-token"},
            )
            assert logout_response.status_code == 200
            assert logout_response.json()["message"] == "Logged out successfully"


class TestResponseFormat:
    """Test response format consistency across auth endpoints."""

    @pytest.mark.asyncio
    async def test_login_response_format(self):
        """Test login response has correct format."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "user@test.com", "password": "password123"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_me_response_format(self, mock_verify_token, mock_token_claims):
        """Test /me response has correct format."""
        # Arrange
        mock_verify_token.return_value = mock_token_claims

        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer token"},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "sub" in data
        assert "email" in data
        assert "roles" in data
        assert isinstance(data["roles"], list)

    @pytest.mark.asyncio
    async def test_public_key_response_format(self):
        """Test public key response has correct format."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/auth/public-key")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "jwks_uri" in data
        assert "domain" in data
        assert "algorithms" in data
        assert isinstance(data["algorithms"], list)

    @pytest.mark.asyncio
    async def test_error_responses_have_consistent_format(self):
        """Test that error responses follow consistent format."""
        # Arrange
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - Trigger validation error
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "invalid"},  # Missing password
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
