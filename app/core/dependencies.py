"""FastAPI dependency injection for DemeterAI v2.0.

This module provides reusable FastAPI dependencies for:
- Database session management (async)
- User authentication (JWT token validation)
- Role-based authorization (admin, supervisor, worker, viewer)

Key features:
- Async dependency injection using FastAPI's Depends()
- Type-safe with full type hints
- Integrates with Auth0 JWT authentication
- Clean error handling with custom exceptions
- Production-ready with proper session lifecycle management

Architecture:
- Wraps app/db/session.py for database access
- Wraps app/core/auth.py for authentication
- Used by controllers for dependency injection

Usage:
    from fastapi import APIRouter, Depends
    from app.core.dependencies import get_db, get_current_user, get_admin_user

    router = APIRouter()

    @router.get("/products")
    async def list_products(
        db: AsyncSession = Depends(get_db),
        user: TokenClaims = Depends(get_current_user)
    ):
        # db session is automatically managed (commit/rollback/close)
        # user is authenticated and validated
        products = await db.execute(select(Product))
        return products.scalars().all()

    @router.post("/users")
    async def create_user(
        request: CreateUserRequest,
        db: AsyncSession = Depends(get_db),
        admin: TokenClaims = Depends(get_admin_user)  # Admin-only
    ):
        # Only admin users can access this endpoint
        user = User(**request.dict())
        db.add(user)
        await db.commit()
        return user
"""

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TokenClaims
from app.core.auth import get_current_user as auth_get_current_user
from app.core.logging import get_logger
from app.db.session import get_db_session

logger = get_logger(__name__)


# =============================================================================
# Database Dependencies
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: Provide async database session.

    This is a thin wrapper around get_db_session() from app/db/session.py.
    Provides automatic session lifecycle management:
    - Creates new session for each request
    - Commits transaction on successful completion
    - Rolls back on exception
    - Always closes session (even on error)

    Usage:
        @router.get("/warehouses")
        async def get_warehouses(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Warehouse))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session for the request lifecycle

    Note:
        This dependency is designed for FastAPI's Depends() pattern.
        It is a generator that yields a session and handles cleanup.
    """
    async for session in get_db_session():
        yield session


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_user(
    token_claims: TokenClaims = Depends(auth_get_current_user),
) -> TokenClaims:
    """FastAPI dependency: Extract and validate current authenticated user.

    Wraps app/core/auth.py's get_current_user() for convenient use in controllers.

    Validation:
    - JWT token signature (RS256 with Auth0 JWKS)
    - Token expiration
    - Audience and issuer validation
    - Role extraction from custom namespace

    Usage:
        @router.get("/profile")
        async def get_profile(user: TokenClaims = Depends(get_current_user)):
            return {"user_id": user.sub, "email": user.email, "roles": user.roles}

    Args:
        token_claims: Validated JWT claims from auth.get_current_user()

    Returns:
        TokenClaims: Validated user information with roles

    Raises:
        HTTPException: 401 if token is invalid, expired, or missing
    """
    return token_claims


# =============================================================================
# Authorization Dependencies (Role-Based)
# =============================================================================


async def get_admin_user(
    user: TokenClaims = Depends(get_current_user),
) -> TokenClaims:
    """FastAPI dependency: Require admin role.

    Only allows requests from users with "admin" role.

    Role hierarchy:
    - admin: Full system access (user management, config, all operations)
    - supervisor: Team management, validation, reporting
    - worker: Stock operations, photo uploads
    - viewer: Read-only access

    Usage:
        @router.post("/users")
        async def create_user(
            request: CreateUserRequest,
            admin: TokenClaims = Depends(get_admin_user)
        ):
            # Only admins can create users
            ...

    Args:
        user: Authenticated user from get_current_user()

    Returns:
        TokenClaims: Validated admin user

    Raises:
        HTTPException: 403 if user lacks admin role
    """
    if "admin" not in user.roles:
        logger.warning(
            "Admin access denied",
            user_id=user.sub,
            user_roles=user.roles,
            endpoint="admin_required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource",
        )

    logger.debug(
        "Admin access granted",
        user_id=user.sub,
        user_roles=user.roles,
    )

    return user


async def get_supervisor_user(
    user: TokenClaims = Depends(get_current_user),
) -> TokenClaims:
    """FastAPI dependency: Require supervisor or admin role.

    Allows requests from users with "supervisor" or "admin" roles.

    Supervisor permissions:
    - Stock create/read/update (no delete)
    - Warehouse read
    - Analytics read
    - Photo session validation

    Usage:
        @router.post("/stock-movements")
        async def create_movement(
            request: CreateMovementRequest,
            supervisor: TokenClaims = Depends(get_supervisor_user)
        ):
            # Supervisors and admins can create movements
            ...

    Args:
        user: Authenticated user from get_current_user()

    Returns:
        TokenClaims: Validated supervisor or admin user

    Raises:
        HTTPException: 403 if user lacks supervisor/admin role
    """
    allowed_roles = {"supervisor", "admin"}
    user_roles = set(user.roles)

    if not user_roles.intersection(allowed_roles):
        logger.warning(
            "Supervisor access denied",
            user_id=user.sub,
            user_roles=user.roles,
            required_roles=list(allowed_roles),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor or admin privileges required to access this resource",
        )

    logger.debug(
        "Supervisor access granted",
        user_id=user.sub,
        user_roles=user.roles,
    )

    return user


async def get_worker_user(
    user: TokenClaims = Depends(get_current_user),
) -> TokenClaims:
    """FastAPI dependency: Require worker, supervisor, or admin role.

    Allows requests from users with "worker", "supervisor", or "admin" roles.

    Worker permissions:
    - Stock read
    - Warehouse read
    - Photo upload

    Usage:
        @router.get("/stock-batches")
        async def list_batches(
            worker: TokenClaims = Depends(get_worker_user)
        ):
            # Workers, supervisors, and admins can read stock
            ...

    Args:
        user: Authenticated user from get_current_user()

    Returns:
        TokenClaims: Validated worker, supervisor, or admin user

    Raises:
        HTTPException: 403 if user lacks worker/supervisor/admin role
    """
    allowed_roles = {"worker", "supervisor", "admin"}
    user_roles = set(user.roles)

    if not user_roles.intersection(allowed_roles):
        logger.warning(
            "Worker access denied",
            user_id=user.sub,
            user_roles=user.roles,
            required_roles=list(allowed_roles),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker, supervisor, or admin privileges required to access this resource",
        )

    logger.debug(
        "Worker access granted",
        user_id=user.sub,
        user_roles=user.roles,
    )

    return user


def get_authorized_user(
    allowed_roles: list[str],
) -> Callable[[TokenClaims], Coroutine[Any, Any, TokenClaims]]:
    """FastAPI dependency factory: Generic role-based authorization.

    Creates a custom dependency that checks for any of the specified roles.

    Usage:
        # Define custom dependency
        require_stock_access = Depends(
            lambda user=Depends(get_current_user): get_authorized_user(
                user=user,
                allowed_roles=["admin", "supervisor", "worker"]
            )
        )

        @router.post("/stock-movements")
        async def create_movement(
            request: CreateMovementRequest,
            user: TokenClaims = require_stock_access
        ):
            # Only specified roles can access
            ...

    Args:
        allowed_roles: List of roles permitted to access the endpoint

    Returns:
        Dependency function that validates user roles

    Note:
        This is a dependency factory. Use it to create custom role requirements.
        For common role checks, prefer get_admin_user(), get_supervisor_user(), etc.
    """

    async def _check_roles(
        user: TokenClaims = Depends(get_current_user),
    ) -> TokenClaims:
        """Inner dependency that performs the role check."""
        user_roles = set(user.roles)
        allowed_roles_set = set(allowed_roles)

        if not user_roles.intersection(allowed_roles_set):
            logger.warning(
                "Authorization failed",
                user_id=user.sub,
                user_roles=user.roles,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of the following roles required: {', '.join(allowed_roles)}",
            )

        logger.debug(
            "Authorization granted",
            user_id=user.sub,
            user_roles=user.roles,
            required_roles=allowed_roles,
        )

        return user

    return _check_roles


# =============================================================================
# Utility Dependencies
# =============================================================================


async def get_optional_user(
    token_claims: TokenClaims | None = Depends(lambda: None),
) -> TokenClaims | None:
    """FastAPI dependency: Optional authentication.

    Returns authenticated user if token is present, None otherwise.
    Useful for endpoints that have different behavior for authenticated vs anonymous users.

    Usage:
        @router.get("/products")
        async def list_products(
            user: TokenClaims | None = Depends(get_optional_user)
        ):
            if user:
                # Show user-specific data
                return {"message": f"Hello {user.email}"}
            else:
                # Show public data
                return {"message": "Hello guest"}

    Args:
        token_claims: Optional validated JWT claims

    Returns:
        TokenClaims if authenticated, None if not

    Note:
        This dependency does NOT raise exceptions for missing/invalid tokens.
        It silently returns None. Use get_current_user() for required authentication.
    """
    try:
        # Attempt to get current user (may raise HTTPException)
        return await get_current_user()
    except HTTPException:
        # Token missing or invalid - return None (guest user)
        return None
