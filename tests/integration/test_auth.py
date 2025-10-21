"""Integration tests for Auth0 JWT authentication and RBAC.

Tests cover:
- JWT token validation
- Auth0 JWKS client
- Token expiration handling
- Role-based access control
- Invalid token rejection
- Token claims extraction

Coverage Target: >= 80% for app.core.auth
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.core.auth import (
    ROLE_ADMIN,
    ROLE_SUPERVISOR,
    ROLE_WORKER,
    Auth0Config,
    TokenClaims,
    fetch_jwks,
    get_auth0_config,
    get_current_user,
    get_signing_key,
    has_any_role,
    has_role,
    require_role,
    verify_token,
)
from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException


class TestAuth0Config:
    """Test Auth0 configuration loading."""

    def test_auth0_config_from_settings(self):
        """Test that Auth0Config loads from settings correctly."""
        # Act
        config = Auth0Config.from_settings()

        # Assert
        assert config.domain is not None
        assert config.api_audience is not None
        assert config.algorithms == ["RS256"]
        assert config.jwks_uri.startswith("https://")
        assert config.jwks_uri.endswith("/.well-known/jwks.json")
        assert config.issuer.startswith("https://")
        assert config.issuer.endswith("/")

    def test_auth0_config_strips_protocol_from_domain(self):
        """Test that domain protocol is stripped if provided."""
        # Arrange
        with patch.object(settings, "AUTH0_DOMAIN", "https://test.auth0.com"):
            # Act
            config = Auth0Config.from_settings()

            # Assert
            assert config.domain == "test.auth0.com"
            assert "https://" not in config.domain

    def test_auth0_config_missing_domain_raises_error(self):
        """Test that missing AUTH0_DOMAIN raises ValueError."""
        # Arrange
        with patch.object(settings, "AUTH0_DOMAIN", None):
            # Act & Assert
            with pytest.raises(ValueError, match="AUTH0_DOMAIN"):
                Auth0Config.from_settings()

    def test_auth0_config_missing_audience_raises_error(self):
        """Test that missing AUTH0_API_AUDIENCE raises ValueError."""
        # Arrange
        with patch.object(settings, "AUTH0_API_AUDIENCE", None):
            # Act & Assert
            with pytest.raises(ValueError, match="AUTH0_API_AUDIENCE"):
                Auth0Config.from_settings()

    def test_get_auth0_config_is_cached(self):
        """Test that get_auth0_config returns cached instance."""
        # Act
        config1 = get_auth0_config()
        config2 = get_auth0_config()

        # Assert
        assert config1 is config2  # Same instance (cached)


class TestJWKSFetching:
    """Test JWKS key fetching from Auth0."""

    @pytest.mark.asyncio
    @patch("app.core.auth.httpx.AsyncClient")
    async def test_fetch_jwks_success(self, mock_client_class):
        """Test successful JWKS fetch from Auth0."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-id",
                    "use": "sig",
                    "n": "test-n-value",
                    "e": "AQAB",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act
        jwks = await fetch_jwks()

        # Assert
        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "test-key-id"

    @pytest.mark.asyncio
    @patch("app.core.auth.httpx.AsyncClient")
    async def test_fetch_jwks_network_error_raises_unauthorized(self, mock_client_class):
        """Test that network error when fetching JWKS raises UnauthorizedException."""
        # Arrange
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act & Assert
        with pytest.raises(UnauthorizedException, match="Cannot fetch Auth0 public keys"):
            await fetch_jwks()

    @pytest.mark.asyncio
    @patch("app.core.auth.httpx.AsyncClient")
    async def test_fetch_jwks_http_error_raises_unauthorized(self, mock_client_class):
        """Test that HTTP error when fetching JWKS raises UnauthorizedException."""
        # Arrange
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Act & Assert
        with pytest.raises(UnauthorizedException):
            await fetch_jwks()


class TestSigningKeyExtraction:
    """Test JWT signing key extraction from JWKS."""

    @pytest.mark.asyncio
    @patch("app.core.auth.fetch_jwks")
    async def test_get_signing_key_success(self, mock_fetch_jwks):
        """Test successful signing key extraction from JWKS."""
        # Arrange
        mock_fetch_jwks.return_value = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "test-key-123",
                    "use": "sig",
                    "n": "test-n-value",
                    "e": "AQAB",
                }
            ]
        }

        # Create a test token with kid in header
        token_header = {"kid": "test-key-123", "alg": "RS256"}
        token_payload = {"sub": "test-user", "exp": 9999999999}
        test_token = jwt.encode(token_payload, "secret", algorithm="HS256", headers=token_header)

        # Act
        signing_key = await get_signing_key(test_token)

        # Assert
        assert signing_key is not None
        assert isinstance(signing_key, str)
        assert "BEGIN" in signing_key or "RSA" in signing_key.upper()

    @pytest.mark.asyncio
    async def test_get_signing_key_invalid_header_raises_unauthorized(self):
        """Test that invalid JWT header raises UnauthorizedException."""
        # Arrange
        invalid_token = "not.a.valid.jwt"

        # Act & Assert
        with pytest.raises(UnauthorizedException, match="Invalid token header"):
            await get_signing_key(invalid_token)

    @pytest.mark.asyncio
    async def test_get_signing_key_missing_kid_raises_unauthorized(self):
        """Test that JWT without kid raises UnauthorizedException."""
        # Arrange
        # Create token without kid in header
        token_payload = {"sub": "test-user", "exp": 9999999999}
        test_token = jwt.encode(token_payload, "secret", algorithm="HS256")

        # Act & Assert
        with pytest.raises(UnauthorizedException, match="Token missing key ID"):
            await get_signing_key(test_token)

    @pytest.mark.asyncio
    @patch("app.core.auth.fetch_jwks")
    async def test_get_signing_key_key_not_found_raises_unauthorized(self, mock_fetch_jwks):
        """Test that JWKS without matching kid raises UnauthorizedException."""
        # Arrange
        mock_fetch_jwks.return_value = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "different-key-id",
                    "use": "sig",
                    "n": "test-n-value",
                    "e": "AQAB",
                }
            ]
        }

        # Create token with non-matching kid
        token_header = {"kid": "test-key-123", "alg": "RS256"}
        token_payload = {"sub": "test-user", "exp": 9999999999}
        test_token = jwt.encode(token_payload, "secret", algorithm="HS256", headers=token_header)

        # Act & Assert
        with pytest.raises(UnauthorizedException, match="Unable to find matching public key"):
            await get_signing_key(test_token)


class TestTokenClaims:
    """Test TokenClaims model validation."""

    def test_token_claims_valid_data(self):
        """Test TokenClaims with valid data."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        future = now + 86400  # 24 hours

        # Act
        claims = TokenClaims(
            sub="auth0|123456",
            email="user@example.com",
            roles=["supervisor"],
            iat=now,
            exp=future,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Assert
        assert claims.sub == "auth0|123456"
        assert claims.email == "user@example.com"
        assert claims.roles == ["supervisor"]

    def test_token_claims_expired_token_raises_error(self):
        """Test that expired token raises validation error."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        past = now - 3600  # 1 hour ago

        # Act & Assert
        with pytest.raises(ValueError, match="Token expired"):
            TokenClaims(
                sub="auth0|123456",
                email="user@example.com",
                roles=["admin"],
                iat=now - 7200,
                exp=past,  # Expired!
                aud="https://api.demeter.ai",
                iss="https://demeter.us.auth0.com/",
            )

    def test_token_claims_empty_roles_defaults_to_list(self):
        """Test that missing roles defaults to empty list."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        future = now + 86400

        # Act
        claims = TokenClaims(
            sub="auth0|123456",
            email="user@example.com",
            # roles not provided
            iat=now,
            exp=future,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Assert
        assert claims.roles == []


class TestTokenVerification:
    """Test JWT token verification."""

    @pytest.mark.asyncio
    @patch("app.core.auth.get_signing_key")
    @patch("app.core.auth.jwt.decode")
    async def test_verify_token_success(self, mock_jwt_decode, mock_get_signing_key):
        """Test successful token verification."""
        # Arrange
        mock_get_signing_key.return_value = "test-signing-key"
        now = int(datetime.now(UTC).timestamp())
        future = now + 86400

        mock_jwt_decode.return_value = {
            "sub": "auth0|123456",
            "email": "supervisor@demeter.ai",
            "https://demeter.ai/roles": ["supervisor"],
            "iat": now,
            "exp": future,
            "aud": settings.AUTH0_API_AUDIENCE,
            "iss": f"https://{settings.AUTH0_DOMAIN}/",
        }

        # Act
        claims = await verify_token("test-jwt-token")

        # Assert
        assert isinstance(claims, TokenClaims)
        assert claims.sub == "auth0|123456"
        assert claims.email == "supervisor@demeter.ai"
        assert claims.roles == ["supervisor"]

    @pytest.mark.asyncio
    @patch("app.core.auth.get_signing_key")
    async def test_verify_token_invalid_signature_raises_unauthorized(self, mock_get_signing_key):
        """Test that invalid signature raises UnauthorizedException."""
        # Arrange

        mock_get_signing_key.return_value = "test-signing-key"

        # Create token with wrong signature
        test_token = "invalid.jwt.token"

        # Act & Assert
        with pytest.raises(UnauthorizedException, match="Invalid token"):
            await verify_token(test_token)

    @pytest.mark.asyncio
    @patch("app.core.auth.get_signing_key")
    @patch("app.core.auth.jwt.decode")
    async def test_verify_token_extracts_roles_from_namespace(
        self, mock_jwt_decode, mock_get_signing_key
    ):
        """Test that roles are extracted from custom namespace."""
        # Arrange
        mock_get_signing_key.return_value = "test-signing-key"
        now = int(datetime.now(UTC).timestamp())
        future = now + 86400

        # Auth0 returns roles in custom namespace
        mock_jwt_decode.return_value = {
            "sub": "auth0|123456",
            "email": "admin@demeter.ai",
            "https://demeter.ai/roles": ["admin", "supervisor"],  # Namespace!
            "iat": now,
            "exp": future,
            "aud": settings.AUTH0_API_AUDIENCE,
            "iss": f"https://{settings.AUTH0_DOMAIN}/",
        }

        # Act
        claims = await verify_token("test-jwt-token")

        # Assert
        assert claims.roles == ["admin", "supervisor"]


class TestRoleBasedAccessControl:
    """Test role-based access control functionality."""

    def test_has_role_returns_true_for_matching_role(self):
        """Test has_role returns True when user has the role."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        claims = TokenClaims(
            sub="auth0|123",
            email="user@test.com",
            roles=["supervisor"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Act
        result = has_role(claims, ROLE_SUPERVISOR)

        # Assert
        assert result is True

    def test_has_role_returns_false_for_non_matching_role(self):
        """Test has_role returns False when user lacks the role."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        claims = TokenClaims(
            sub="auth0|123",
            email="user@test.com",
            roles=["worker"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Act
        result = has_role(claims, ROLE_ADMIN)

        # Assert
        assert result is False

    def test_has_any_role_returns_true_when_one_role_matches(self):
        """Test has_any_role returns True when at least one role matches."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        claims = TokenClaims(
            sub="auth0|123",
            email="user@test.com",
            roles=["supervisor"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Act
        result = has_any_role(claims, [ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_WORKER])

        # Assert
        assert result is True

    def test_has_any_role_returns_false_when_no_roles_match(self):
        """Test has_any_role returns False when no roles match."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        claims = TokenClaims(
            sub="auth0|123",
            email="user@test.com",
            roles=["viewer"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        # Act
        result = has_any_role(claims, [ROLE_ADMIN, ROLE_SUPERVISOR])

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_require_role_decorator_allows_access_for_authorized_role(self):
        """Test require_role decorator allows access when user has role."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        user = TokenClaims(
            sub="auth0|123",
            email="supervisor@test.com",
            roles=["supervisor"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        @require_role(["admin", "supervisor"])
        async def protected_endpoint(user: TokenClaims):
            return {"message": "Access granted"}

        # Act
        result = await protected_endpoint(user=user)

        # Assert
        assert result == {"message": "Access granted"}

    @pytest.mark.asyncio
    async def test_require_role_decorator_denies_access_for_unauthorized_role(self):
        """Test require_role decorator raises ForbiddenException for unauthorized role."""
        # Arrange
        now = int(datetime.now(UTC).timestamp())
        user = TokenClaims(
            sub="auth0|123",
            email="worker@test.com",
            roles=["worker"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )

        @require_role(["admin", "supervisor"])
        async def protected_endpoint(user: TokenClaims):
            return {"message": "Access granted"}

        # Act & Assert
        with pytest.raises(ForbiddenException):
            await protected_endpoint(user=user)

    @pytest.mark.asyncio
    async def test_require_role_decorator_raises_error_if_user_not_provided(self):
        """Test require_role decorator raises error if user not in arguments."""

        # Arrange
        @require_role(["admin"])
        async def protected_endpoint():
            return {"message": "Access granted"}

        # Act & Assert
        with pytest.raises(ForbiddenException):
            await protected_endpoint()


class TestGetCurrentUser:
    """Test get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_get_current_user_with_valid_token(self, mock_verify_token):
        """Test get_current_user returns TokenClaims for valid token."""
        # Arrange
        from fastapi.security import HTTPAuthorizationCredentials

        now = int(datetime.now(UTC).timestamp())
        expected_claims = TokenClaims(
            sub="auth0|123456",
            email="user@test.com",
            roles=["supervisor"],
            iat=now,
            exp=now + 86400,
            aud="https://api.demeter.ai",
            iss="https://demeter.us.auth0.com/",
        )
        mock_verify_token.return_value = expected_claims

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-jwt-token")

        # Act
        claims = await get_current_user(credentials)

        # Assert
        assert claims == expected_claims
        mock_verify_token.assert_called_once_with("test-jwt-token")

    @pytest.mark.asyncio
    @patch("app.core.auth.verify_token")
    async def test_get_current_user_with_invalid_token_raises_http_exception(
        self, mock_verify_token
    ):
        """Test get_current_user raises HTTPException for invalid token."""
        # Arrange
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        mock_verify_token.side_effect = UnauthorizedException(reason="Invalid token signature")

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-jwt-token")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "WWW-Authenticate" in exc_info.value.headers
