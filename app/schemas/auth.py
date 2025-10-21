"""Authentication Pydantic schemas for DemeterAI v2.0.

This module provides Pydantic v2 models for authentication-related
request/response payloads. All schemas include field validation,
type hints, and comprehensive documentation.

Schemas:
    - LoginRequest: Email/password authentication request
    - LoginResponse: JWT access token response
    - UserResponse: Current user information
    - TokenClaims: JWT token claims (mirrors app.core.auth.TokenClaims)
    - RefreshTokenRequest: Refresh token request
    - LogoutResponse: Logout confirmation
    - PublicKeyResponse: Auth0 public key information

Architecture:
    Layer: Schema Layer (Data Transfer Objects)
    Usage: Request/response validation for auth_controller endpoints
    Pattern: Pydantic v2 models with field validators
"""

import re

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Authentication Request Schemas
# =============================================================================


class LoginRequest(BaseModel):
    """Login request with email and password.

    Attributes:
        email: User email address (validated format)
        password: User password (minimum 8 characters)
    """

    email: str = Field(
        ...,
        description="User email address",
        examples=["supervisor@demeter.ai"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password (minimum 8 characters)",
        examples=["SecurePassword123!"],
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate email format using regex.

        Args:
            v: Email string

        Returns:
            Email if valid

        Raises:
            ValueError: If email format is invalid
        """
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum requirements.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit

        Args:
            v: Password string

        Returns:
            Password if valid

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "supervisor@demeter.ai",
                "password": "SecurePassword123!",
            }
        }
    }


class RefreshTokenRequest(BaseModel):
    """Refresh token request for obtaining new access token.

    Attributes:
        refresh_token: JWT refresh token obtained during login
    """

    refresh_token: str = Field(
        ...,
        min_length=20,
        description="JWT refresh token",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh..."],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token_payload...",
            }
        }
    }


# =============================================================================
# Authentication Response Schemas
# =============================================================================


class LoginResponse(BaseModel):
    """Login response with access token.

    Attributes:
        access_token: JWT access token for API authentication
        token_type: Token type (always "bearer")
        expires_in: Token expiration time in seconds (default: 86400 = 24 hours)
        refresh_token: Optional refresh token for obtaining new access tokens
    """

    access_token: str = Field(
        ...,
        description="JWT access token",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (OAuth2 standard)",
        examples=["bearer"],
    )
    expires_in: int = Field(
        default=86400,
        description="Token expiration in seconds (86400 = 24 hours)",
        examples=[86400],
    )
    refresh_token: str | None = Field(
        None,
        description="Optional refresh token for renewing access tokens",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh..."],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh...",
            }
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

    sub: str = Field(
        ...,
        description="Auth0 user ID (subject claim)",
        examples=["auth0|507f1f77bcf86cd799439011"],
    )
    email: str = Field(
        ...,
        description="User email address",
        examples=["supervisor@demeter.ai"],
    )
    roles: list[str] = Field(
        default_factory=list,
        description="User roles (admin, supervisor, worker, viewer)",
        examples=[["supervisor"]],
    )
    iat: int | None = Field(
        None,
        description="Token issued at (Unix timestamp)",
        examples=[1711234567],
    )
    exp: int | None = Field(
        None,
        description="Token expires at (Unix timestamp)",
        examples=[1711320967],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "sub": "auth0|507f1f77bcf86cd799439011",
                "email": "supervisor@demeter.ai",
                "roles": ["supervisor"],
                "iat": 1711234567,
                "exp": 1711320967,
            }
        }
    }


class TokenClaims(BaseModel):
    """JWT token claims (mirrors app.core.auth.TokenClaims).

    This schema is used for serialization/validation of token claims
    in API responses. The authoritative validation happens in app.core.auth.

    Attributes:
        sub: Subject (user ID from Auth0)
        email: User email address
        roles: List of assigned roles
        iat: Issued at timestamp (Unix epoch)
        exp: Expiration timestamp (Unix epoch)
        aud: Audience (API identifier)
        iss: Issuer (Auth0 domain)
        azp: Authorized party (client ID)
        scope: OAuth2 scopes
    """

    sub: str = Field(
        ...,
        description="Auth0 user ID (e.g., 'auth0|123456')",
        examples=["auth0|507f1f77bcf86cd799439011"],
    )
    email: str = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    roles: list[str] = Field(
        default_factory=list,
        description="User roles from Auth0 (namespace: https://demeter.ai/roles)",
        examples=[["admin", "supervisor"]],
    )
    iat: int = Field(
        ...,
        description="Issued at (Unix timestamp)",
        examples=[1711234567],
    )
    exp: int = Field(
        ...,
        description="Expiration (Unix timestamp)",
        examples=[1711320967],
    )
    aud: str | list[str] = Field(
        ...,
        description="Audience (API identifier)",
        examples=["https://api.demeter.ai"],
    )
    iss: str = Field(
        ...,
        description="Issuer (Auth0 domain)",
        examples=["https://demeter.us.auth0.com/"],
    )
    azp: str | None = Field(
        None,
        description="Authorized party (client ID)",
        examples=["client_abc123"],
    )
    scope: str | None = Field(
        None,
        description="OAuth2 scopes",
        examples=["openid profile email"],
    )

    model_config = {
        "json_schema_extra": {
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
    }


class LogoutResponse(BaseModel):
    """Logout response.

    Attributes:
        message: Success message
    """

    message: str = Field(
        ...,
        description="Logout confirmation message",
        examples=["Logged out successfully"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Logged out successfully",
            }
        }
    }


class PublicKeyResponse(BaseModel):
    """Auth0 public key information response.

    Attributes:
        jwks_uri: URL to fetch Auth0 JWKS (JSON Web Key Set)
        domain: Auth0 tenant domain
        algorithms: Allowed JWT algorithms (e.g., ["RS256"])
    """

    jwks_uri: str = Field(
        ...,
        description="JWKS endpoint URL",
        examples=["https://demeter.us.auth0.com/.well-known/jwks.json"],
    )
    domain: str = Field(
        ...,
        description="Auth0 tenant domain",
        examples=["demeter.us.auth0.com"],
    )
    algorithms: list[str] = Field(
        ...,
        description="Allowed JWT algorithms",
        examples=[["RS256"]],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "jwks_uri": "https://demeter.us.auth0.com/.well-known/jwks.json",
                "domain": "demeter.us.auth0.com",
                "algorithms": ["RS256"],
            }
        }
    }
