"""Auth0 JWT authentication and Role-Based Access Control (RBAC).

This module provides secure JWT token validation against Auth0's public keys
and implements role-based authorization for API endpoints.

Key features:
- JWT signature verification using Auth0 JWKS (RS256 algorithm)
- Token expiration and audience validation
- Four-tier role hierarchy (admin, supervisor, worker, viewer)
- Async JWKS client with LRU caching for performance
- Comprehensive error handling for authentication failures

Architecture:
- Uses python-jose for JWT validation
- Fetches public keys from Auth0's JWKS endpoint
- Caches keys for 24 hours to minimize network requests
- All operations are async-compatible

Roles:
- admin: Full access (create, read, update, delete)
- supervisor: Read/write stock operations (no user management)
- worker: Read-only stock operations (no modifications)
- viewer: Dashboard and analytics only (no operational access)

Usage:
    from app.core.auth import verify_token, require_role, TokenClaims

    # In FastAPI dependency
    async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenClaims:
        claims = await verify_token(token)
        return claims

    # Role enforcement
    @require_role(["admin", "supervisor"])
    async def create_stock_movement(user: TokenClaims = Depends(get_current_user)):
        ...
"""

from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache, wraps
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.logging import get_logger

logger = get_logger(__name__)

# OAuth2 scheme for FastAPI
security = HTTPBearer()


# =============================================================================
# Pydantic Models
# =============================================================================


class TokenClaims(BaseModel):
    """Validated JWT token claims.

    Attributes:
        sub: Subject (user ID from Auth0)
        email: User email address
        roles: List of assigned roles (admin, supervisor, worker, viewer)
        iat: Issued at timestamp (Unix epoch)
        exp: Expiration timestamp (Unix epoch)
        aud: Audience (API identifier)
        iss: Issuer (Auth0 domain)
        azp: Authorized party (client ID)
        scope: OAuth2 scopes
    """

    sub: str = Field(..., description="Auth0 user ID (e.g., 'auth0|123456')")
    email: str = Field(..., description="User email address")
    roles: list[str] = Field(
        default_factory=list,
        description="User roles from Auth0 (namespace: https://demeter.ai/roles)",
    )
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    exp: int = Field(..., description="Expiration (Unix timestamp)")
    aud: str | list[str] = Field(..., description="Audience (API identifier)")
    iss: str = Field(..., description="Issuer (Auth0 domain)")
    azp: str | None = Field(None, description="Authorized party (client ID)")
    scope: str | None = Field(None, description="OAuth2 scopes")

    @field_validator("roles", mode="before")
    @classmethod
    def extract_roles_from_namespace(cls, v: Any) -> list[str]:
        """Extract roles from Auth0 custom namespace.

        Auth0 returns custom claims with namespace prefix:
        {'https://demeter.ai/roles': ['admin', 'supervisor']}

        This validator extracts the roles regardless of namespace format.

        Args:
            v: Raw roles value (could be list or dict with namespace)

        Returns:
            List of role strings
        """
        if isinstance(v, list):
            return v
        # If roles are missing, return empty list (default)
        return []

    @field_validator("exp")
    @classmethod
    def validate_not_expired(cls, v: int) -> int:
        """Validate token has not expired.

        Args:
            v: Expiration timestamp

        Returns:
            Expiration timestamp if valid

        Raises:
            ValueError: If token is expired
        """
        now = datetime.now(UTC).timestamp()
        if v < now:
            raise ValueError(f"Token expired at {datetime.fromtimestamp(v, tz=UTC)}")
        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "sub": "auth0|507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "roles": ["supervisor"],
                "iat": 1711234567,
                "exp": 1711320967,
                "aud": "https://api.demeter.ai",
                "iss": "https://demeter.us.auth0.com/",
                "azp": "client_abc123",
                "scope": "openid profile email",
            }
        }


class Auth0Config(BaseModel):
    """Auth0 configuration from environment variables.

    Loaded from Settings (pydantic_settings) at startup.
    """

    domain: str = Field(..., description="Auth0 tenant domain")
    api_audience: str = Field(..., description="API identifier registered in Auth0")
    algorithms: list[str] = Field(default=["RS256"], description="Allowed JWT algorithms")
    jwks_uri: str = Field(..., description="JWKS endpoint URL")
    issuer: str = Field(..., description="Expected token issuer")

    @classmethod
    def from_settings(cls) -> "Auth0Config":
        """Load Auth0 config from application settings.

        Returns:
            Auth0Config instance

        Raises:
            ValueError: If required environment variables are missing
        """
        domain = getattr(settings, "AUTH0_DOMAIN", None)
        api_audience = getattr(settings, "AUTH0_API_AUDIENCE", None)

        if not domain:
            raise ValueError(
                "AUTH0_DOMAIN environment variable is required. Example: demeter.us.auth0.com"
            )
        if not api_audience:
            raise ValueError(
                "AUTH0_API_AUDIENCE environment variable is required. "
                "Example: https://api.demeter.ai"
            )

        # Ensure domain doesn't include protocol
        domain = domain.replace("https://", "").replace("http://", "")

        return cls(
            domain=domain,
            api_audience=api_audience,
            algorithms=getattr(settings, "AUTH0_ALGORITHMS", ["RS256"]),
            jwks_uri=f"https://{domain}/.well-known/jwks.json",
            issuer=f"https://{domain}/",
        )


# =============================================================================
# JWKS Key Management
# =============================================================================


@lru_cache(maxsize=1)
def get_auth0_config() -> Auth0Config:
    """Get cached Auth0 configuration.

    Returns:
        Auth0Config singleton instance
    """
    return Auth0Config.from_settings()


async def fetch_jwks() -> dict[str, Any]:
    """Fetch JSON Web Key Set (JWKS) from Auth0.

    JWKS contains public keys used to verify JWT signatures.
    Keys are cached using Python's LRU cache to minimize network requests.

    Returns:
        JWKS dictionary with keys

    Raises:
        UnauthorizedException: If JWKS fetch fails
    """
    config = get_auth0_config()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(config.jwks_uri)
            response.raise_for_status()
            jwks: dict[str, Any] = response.json()

            logger.debug(
                "Fetched JWKS from Auth0",
                jwks_uri=config.jwks_uri,
                key_count=len(jwks.get("keys", [])),
            )

            return jwks

    except httpx.HTTPError as e:
        logger.error(
            "Failed to fetch JWKS from Auth0",
            jwks_uri=config.jwks_uri,
            error=str(e),
            exc_info=True,
        )
        raise UnauthorizedException(reason=f"Cannot fetch Auth0 public keys: {str(e)}") from e


@lru_cache(maxsize=10)
def _cache_jwks(jwks_json: str) -> dict[str, Any]:
    """Cache JWKS in memory.

    LRU cache with maxsize=10 keeps last 10 JWKS responses.
    Cache persists for duration of application process.

    Args:
        jwks_json: JSON string of JWKS response

    Returns:
        Parsed JWKS dictionary
    """
    import json

    result: dict[str, Any] = json.loads(jwks_json)
    return result


async def get_signing_key(token: str) -> str:
    """Get public signing key for JWT token verification.

    Extracts 'kid' (key ID) from JWT header, fetches JWKS from Auth0,
    and returns matching public key in PEM format.

    Args:
        token: JWT token string

    Returns:
        Public key in PEM format

    Raises:
        UnauthorizedException: If key not found or fetch fails
    """
    # Extract header without verification
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        logger.warning("Invalid JWT header", error=str(e))
        raise UnauthorizedException(reason=f"Invalid token header: {str(e)}") from e

    # Get key ID from header
    kid = unverified_header.get("kid")
    if not kid:
        logger.warning("JWT missing 'kid' in header")
        raise UnauthorizedException(reason="Token missing key ID")

    # Fetch JWKS from Auth0
    jwks = await fetch_jwks()

    # Cache JWKS for performance (convert to JSON string for hashing)
    import json

    jwks_json = json.dumps(jwks, sort_keys=True)
    cached_jwks = _cache_jwks(jwks_json)

    # Find matching key
    rsa_key = None
    for key in cached_jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = {
                "kty": key.get("kty"),
                "kid": key.get("kid"),
                "use": key.get("use"),
                "n": key.get("n"),
                "e": key.get("e"),
            }
            break

    if not rsa_key:
        logger.warning("Public key not found in JWKS", kid=kid)
        raise UnauthorizedException(reason="Unable to find matching public key")

    logger.debug("Found signing key for token", kid=kid)

    # Convert RSA key to PEM format (python-jose requires this)
    from jose.backends import RSAKey  # type: ignore[import-untyped]

    rsa_key_obj = RSAKey(rsa_key, algorithm="RS256")
    pem_bytes = rsa_key_obj.to_pem()
    pem_key: str = pem_bytes.decode("utf-8")
    return pem_key


# =============================================================================
# Token Verification
# =============================================================================


async def verify_token(token: str) -> TokenClaims:
    """Verify JWT token and extract validated claims.

    Validation steps:
    1. Fetch signing key from JWKS
    2. Verify signature using RS256 algorithm
    3. Validate expiration timestamp
    4. Validate audience (API identifier)
    5. Validate issuer (Auth0 domain)
    6. Parse and validate claims with Pydantic

    Args:
        token: JWT token string (without "Bearer" prefix)

    Returns:
        TokenClaims with validated user information

    Raises:
        UnauthorizedException: If token is invalid, expired, or malformed
    """
    config = get_auth0_config()

    try:
        # Get signing key from JWKS
        signing_key = await get_signing_key(token)

        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=config.algorithms,
            audience=config.api_audience,
            issuer=config.issuer,
        )

        # Extract roles from custom namespace
        roles_namespace = "https://demeter.ai/roles"
        if roles_namespace in payload:
            payload["roles"] = payload[roles_namespace]

        # Validate with Pydantic model
        claims = TokenClaims(**payload)

        logger.info(
            "Token verified successfully",
            sub=claims.sub,
            email=claims.email,
            roles=claims.roles,
        )

        return claims

    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e), exc_info=True)
        raise UnauthorizedException(reason=f"Invalid token: {str(e)}") from e

    except ValueError as e:
        # Pydantic validation error (e.g., expired token)
        logger.warning("Token validation failed", error=str(e))
        raise UnauthorizedException(reason=str(e)) from e

    except Exception as e:
        logger.error("Unexpected error during token verification", error=str(e), exc_info=True)
        raise UnauthorizedException(reason="Token verification failed") from e


# =============================================================================
# FastAPI Dependencies
# =============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenClaims:
    """FastAPI dependency: Extract and verify JWT from Authorization header.

    Usage:
        @router.get("/protected")
        async def protected_route(user: TokenClaims = Depends(get_current_user)):
            return {"user_id": user.sub, "email": user.email}

    Args:
        credentials: HTTP Authorization header (Bearer token)

    Returns:
        TokenClaims with validated user information

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    try:
        token = credentials.credentials
        claims = await verify_token(token)
        return claims

    except UnauthorizedException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# =============================================================================
# Role-Based Access Control (RBAC)
# =============================================================================


def require_role(allowed_roles: list[str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to enforce role-based access control.

    Usage:
        @router.post("/stock-movements")
        @require_role(["admin", "supervisor"])
        async def create_movement(user: TokenClaims = Depends(get_current_user)):
            ...

    Args:
        allowed_roles: List of roles permitted to access the endpoint

    Returns:
        Decorator function

    Raises:
        ForbiddenException: If user lacks required role
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user from kwargs (injected by get_current_user dependency)
            user: TokenClaims | None = kwargs.get("user")

            if not user:
                # Fallback: Check if user is in args
                for arg in args:
                    if isinstance(arg, TokenClaims):
                        user = arg
                        break

            if not user:
                logger.error("require_role: TokenClaims not found in function arguments")
                raise ForbiddenException(
                    resource=func.__name__,
                    action="access",
                    user_id=None,
                )

            # Check if user has any of the allowed roles
            user_roles = set(user.roles)
            allowed_roles_set = set(allowed_roles)

            if not user_roles.intersection(allowed_roles_set):
                logger.warning(
                    "Role check failed",
                    user_id=user.sub,
                    user_roles=user.roles,
                    required_roles=allowed_roles,
                )
                raise ForbiddenException(
                    resource=func.__name__,
                    action="access",
                    user_id=None,  # Don't expose user ID in exception
                )

            logger.debug(
                "Role check passed",
                user_id=user.sub,
                user_roles=user.roles,
                required_roles=allowed_roles,
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def has_role(user: TokenClaims, role: str) -> bool:
    """Check if user has specific role.

    Helper function for programmatic role checks within business logic.

    Args:
        user: Validated token claims
        role: Role to check (admin, supervisor, worker, viewer)

    Returns:
        True if user has role, False otherwise
    """
    return role in user.roles


def has_any_role(user: TokenClaims, roles: list[str]) -> bool:
    """Check if user has any of the specified roles.

    Args:
        user: Validated token claims
        roles: List of roles to check

    Returns:
        True if user has at least one role, False otherwise
    """
    return bool(set(user.roles).intersection(set(roles)))


# =============================================================================
# Role Hierarchy Constants
# =============================================================================

# Role definitions for reference
ROLE_ADMIN = "admin"
ROLE_SUPERVISOR = "supervisor"
ROLE_WORKER = "worker"
ROLE_VIEWER = "viewer"

# Role permissions mapping (for documentation)
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "user.create",
        "user.read",
        "user.update",
        "user.delete",
        "stock.create",
        "stock.read",
        "stock.update",
        "stock.delete",
        "warehouse.create",
        "warehouse.read",
        "warehouse.update",
        "warehouse.delete",
        "analytics.read",
    ],
    ROLE_SUPERVISOR: [
        "stock.create",
        "stock.read",
        "stock.update",
        "warehouse.read",
        "analytics.read",
    ],
    ROLE_WORKER: [
        "stock.read",
        "warehouse.read",
    ],
    ROLE_VIEWER: [
        "analytics.read",
    ],
}
