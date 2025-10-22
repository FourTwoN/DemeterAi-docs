"""Authentication API Controllers.

This module provides HTTP endpoints for authentication and user management:
- User login (Auth0 integration)
- Current user information
- Logout
- Public key endpoint for JWT verification

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Auth0 for authentication, core.auth for token verification
    Pattern: Thin controllers - delegate to Auth0 and auth utilities

Endpoints:
    GET /api/v1/auth/me - Get current user info (requires auth)
    POST /api/v1/auth/login - Login with username/password or token
    POST /api/v1/auth/logout - Logout (invalidate session)
    GET /api/v1/auth/public-key - Get Auth0 public key for JWT verification

Authentication Flow:
    1. Client sends credentials to /login
    2. For now, returns demo token (Auth0 integration pending)
    3. Client includes token in Authorization: Bearer <token>
    4. Protected endpoints verify token via get_current_user dependency
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import TokenClaims, get_auth0_config, get_current_user
from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# =============================================================================
# Pydantic Schemas (Auth-specific)
# =============================================================================


class LoginRequest(BaseModel):
    """Login request with email and password.

    Attributes:
        email: User email address
        password: User password (will be sent to Auth0 for verification)
    """

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "email": "supervisor@demeter.ai",
                "password": "SecurePassword123!",
            }
        }


class LoginResponse(BaseModel):
    """Login response with access token.

    Attributes:
        access_token: JWT access token for API authentication
        token_type: Token type (always "bearer")
        expires_in: Token expiration time in seconds (24 hours)
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=86400, description="Token expiration (seconds)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }


class UserResponse(BaseModel):
    """Current user information response.

    Attributes:
        sub: User ID from Auth0 (e.g., 'auth0|123456')
        email: User email address
        roles: List of assigned roles (admin, supervisor, worker, viewer)
        iat: Token issued at timestamp (Unix epoch)
        exp: Token expiration timestamp (Unix epoch)
    """

    sub: str = Field(..., description="Auth0 user ID")
    email: str = Field(..., description="User email address")
    roles: list[str] = Field(default_factory=list, description="User roles")
    iat: int | None = Field(None, description="Token issued at (Unix timestamp)")
    exp: int | None = Field(None, description="Token expires at (Unix timestamp)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "sub": "auth0|507f1f77bcf86cd799439011",
                "email": "supervisor@demeter.ai",
                "roles": ["supervisor"],
                "iat": 1711234567,
                "exp": 1711320967,
            }
        }


class LogoutResponse(BaseModel):
    """Logout response.

    Attributes:
        message: Success message
    """

    message: str = Field(..., description="Logout confirmation message")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {"example": {"message": "Logged out successfully"}}


class PublicKeyResponse(BaseModel):
    """Auth0 public key information response.

    Attributes:
        jwks_uri: URL to fetch Auth0 JWKS (JSON Web Key Set)
        domain: Auth0 tenant domain
        algorithms: Allowed JWT algorithms (e.g., ["RS256"])
    """

    jwks_uri: str = Field(..., description="JWKS endpoint URL")
    domain: str = Field(..., description="Auth0 tenant domain")
    algorithms: list[str] = Field(..., description="Allowed JWT algorithms")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "jwks_uri": "https://demeter.us.auth0.com/.well-known/jwks.json",
                "domain": "demeter.us.auth0.com",
                "algorithms": ["RS256"],
            }
        }


# =============================================================================
# API Endpoints - Authentication
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
)
async def get_current_user_info(
    user: TokenClaims = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information.

    This endpoint requires a valid JWT token in the Authorization header.
    Returns user details extracted from the verified token.

    Args:
        user: Current user claims from JWT token (injected by dependency)

    Returns:
        UserResponse with user ID, email, roles, and token timestamps

    Raises:
        HTTPException: 401 if token is invalid or missing

    Example:
        ```bash
        curl -H "Authorization: Bearer <token>" \\
             http://localhost:8000/api/v1/auth/me
        ```
    """
    try:
        logger.info("Current user info requested", extra={"user_id": user.sub, "email": user.email})

        return UserResponse(
            sub=user.sub,
            email=user.email,
            roles=user.roles,
            iat=user.iat,
            exp=user.exp,
        )

    except Exception as e:
        logger.error("Failed to get current user info", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information.",
        ) from e


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
async def login(
    request: LoginRequest,
) -> LoginResponse:
    """Authenticate user with email and password.

    **IMPORTANT**: This is a placeholder implementation for development.
    In production, this endpoint will delegate authentication to Auth0's
    OAuth2 token endpoint.

    Current behavior (development):
    - Accepts any email/password combination
    - Returns a demo token message
    - Real Auth0 integration pending

    Production flow (to be implemented):
    1. Validate email/password with Auth0 OAuth2 endpoint
    2. Receive access_token, refresh_token from Auth0
    3. Return tokens to client
    4. Client uses access_token for subsequent API requests

    Args:
        request: LoginRequest with email and password

    Returns:
        LoginResponse with access_token and metadata

    Raises:
        HTTPException: 401 if credentials are invalid (Auth0 integration)
        HTTPException: 500 if Auth0 service is unavailable

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/auth/login \\
             -H "Content-Type: application/json" \\
             -d '{"email": "user@example.com", "password": "password123"}'
        ```
    """
    try:
        logger.info("Login attempt", extra={"email": request.email})

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Auth0 integration not configured. "
                "Please configure AUTH0_DOMAIN, AUTH0_CLIENT_ID, and AUTH0_CLIENT_SECRET "
                "in your environment variables, then implement Auth0 OAuth2 token flow. "
                "See app/core/AUTH_USAGE_GUIDE.md for integration instructions."
            ),
        )

    except UnauthorizedException as e:
        # This will be raised when Auth0 rejects credentials
        logger.warning("Login failed - invalid credentials", extra={"email": request.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    except Exception as e:
        logger.error(
            "Login failed unexpectedly",
            extra={"email": request.email, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable.",
        ) from e


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout current user",
)
async def logout(
    user: TokenClaims = Depends(get_current_user),
) -> LogoutResponse:
    """Logout current authenticated user.

    **Note**: JWT tokens are stateless, so logout is client-side only.
    The token remains valid until expiration. For true logout in production:
    1. Client discards the token
    2. Optionally: Call Auth0 logout endpoint to clear Auth0 session
    3. Optionally: Implement token blacklist (requires Redis/database)

    Args:
        user: Current user claims from JWT token (injected by dependency)

    Returns:
        LogoutResponse with confirmation message

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/auth/logout \\
             -H "Authorization: Bearer <token>"
        ```
    """
    try:
        logger.info("User logged out", extra={"user_id": user.sub, "email": user.email})

        # NOTE: Token blacklist implementation is optional (Auth0 handles session expiration server-side)
        # NOTE: Auth0 logout endpoint call is optional (token expiration is sufficient for most use cases)

        return LogoutResponse(message="Logged out successfully")

    except Exception as e:
        logger.error("Logout failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed.",
        ) from e


@router.get(
    "/public-key",
    response_model=PublicKeyResponse,
    summary="Get Auth0 public key information",
)
async def get_public_key() -> PublicKeyResponse:
    """Get Auth0 public key endpoint information.

    Returns the JWKS (JSON Web Key Set) endpoint URL and configuration
    for clients that need to verify JWT signatures independently.

    This endpoint does NOT require authentication - it's public by design
    so clients can fetch keys to verify tokens.

    Returns:
        PublicKeyResponse with JWKS URI, domain, and algorithms

    Raises:
        HTTPException: 500 if Auth0 configuration is invalid

    Example:
        ```bash
        curl http://localhost:8000/api/v1/auth/public-key
        ```

    Use case:
        - Frontend apps verifying tokens client-side
        - Microservices that need to verify DemeterAI tokens
        - Third-party integrations
    """
    try:
        logger.info("Public key info requested")

        # Get Auth0 configuration
        auth0_config = get_auth0_config()

        return PublicKeyResponse(
            jwks_uri=auth0_config.jwks_uri,
            domain=auth0_config.domain,
            algorithms=auth0_config.algorithms,
        )

    except ValueError as e:
        # Auth0 configuration missing or invalid
        logger.error("Auth0 configuration invalid", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not configured. Please contact system administrator.",
        ) from e

    except Exception as e:
        logger.error("Failed to get public key info", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve public key information.",
        ) from e
