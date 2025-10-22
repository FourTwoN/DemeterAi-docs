# Auth0 JWT Authentication - Usage Guide

## Quick Start

### 1. Configuration

Add to your `.env` file:

```bash
AUTH0_DOMAIN=demeter.us.auth0.com
AUTH0_API_AUDIENCE=https://api.demeter.ai
AUTH0_ALGORITHMS=["RS256"]
```

### 2. Protected Endpoint (Authentication Only)

```python
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user, TokenClaims

router = APIRouter()

@router.get("/profile")
async def get_profile(user: TokenClaims = Depends(get_current_user)):
    """Any authenticated user can access this endpoint."""
    return {
        "user_id": user.sub,
        "email": user.email,
        "roles": user.roles
    }
```

### 3. Role-Protected Endpoint (RBAC)

```python
from app.core.auth import require_role

@router.post("/stock-movements")
@require_role(["admin", "supervisor"])
async def create_movement(
    request: StockMovementCreate,
    user: TokenClaims = Depends(get_current_user)
):
    """Only admin or supervisor can create stock movements."""
    return {"message": "Movement created"}
```

### 4. Multiple Role Requirements

```python
# Admin only
@require_role(["admin"])
async def delete_user(user_id: int, user: TokenClaims = Depends(get_current_user)):
    ...

# Supervisor or admin
@require_role(["admin", "supervisor"])
async def update_stock(stock_id: int, user: TokenClaims = Depends(get_current_user)):
    ...

# Worker, supervisor, or admin
@require_role(["admin", "supervisor", "worker"])
async def view_stock(stock_id: int, user: TokenClaims = Depends(get_current_user)):
    ...
```

### 5. Programmatic Role Checks

```python
from app.core.auth import has_role, has_any_role

async def get_statistics(user: TokenClaims = Depends(get_current_user)):
    if has_role(user, "admin"):
        # Return detailed admin statistics
        return {"type": "admin", "data": get_admin_stats()}

    elif has_any_role(user, ["supervisor", "worker"]):
        # Return limited statistics
        return {"type": "limited", "data": get_basic_stats()}

    else:
        # Viewer role
        return {"type": "public", "data": get_public_stats()}
```

## Role Hierarchy

| Role           | Permissions                                       | Use Case                              |
|----------------|---------------------------------------------------|---------------------------------------|
| **admin**      | Full access (all CRUD operations)                 | System administrators, account owners |
| **supervisor** | Read/write stock operations, warehouse management | Floor supervisors, inventory managers |
| **worker**     | Read-only stock operations                        | Warehouse workers, pickers            |
| **viewer**     | Dashboard and analytics only                      | Stakeholders, reporting users         |

## TokenClaims Model

```python
class TokenClaims:
    sub: str                # Auth0 user ID (e.g., "auth0|123456")
    email: str              # User email address
    roles: List[str]        # User roles ["admin", "supervisor"]
    iat: int                # Issued at (Unix timestamp)
    exp: int                # Expiration (Unix timestamp)
    aud: str | List[str]    # Audience (API identifier)
    iss: str                # Issuer (Auth0 domain)
    azp: Optional[str]      # Authorized party (client ID)
    scope: Optional[str]    # OAuth2 scopes
```

## Error Handling

### 401 Unauthorized

Raised when:

- Token is missing
- Token is malformed
- Token signature is invalid
- Token is expired
- Token issuer doesn't match
- Token audience doesn't match

```python
# Automatic by get_current_user dependency
# Returns: {"detail": "Authentication required. Please log in."}
```

### 403 Forbidden

Raised when:

- User lacks required role
- User authenticated but unauthorized for action

```python
# Automatic by @require_role decorator
# Returns: {"detail": "You do not have permission to access this endpoint"}
```

## Testing

### Unit Tests

```python
import pytest
from app.core.auth import TokenClaims

@pytest.fixture
def admin_user():
    return TokenClaims(
        sub="auth0|admin123",
        email="admin@demeter.ai",
        roles=["admin"],
        iat=1711234567,
        exp=9999999999,
        aud="https://api.demeter.ai",
        iss="https://demeter.us.auth0.com/"
    )

def test_admin_access(admin_user):
    assert has_role(admin_user, "admin")
    assert has_any_role(admin_user, ["admin", "supervisor"])
```

### Integration Tests with Real Tokens

```python
import httpx

async def test_protected_endpoint():
    # Get token from Auth0
    token = await get_auth0_token()

    # Make authenticated request
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
```

## Security Best Practices

1. **Never log tokens**: Tokens contain sensitive information
   ```python
   # ❌ BAD
   logger.info(f"Token: {token}")

   # ✅ GOOD
   logger.info("User authenticated", user_id=user.sub)
   ```

2. **Validate roles in business logic**: Don't trust role checks alone
   ```python
   # ✅ GOOD
   @require_role(["admin"])
   async def delete_user(user_id: int, user: TokenClaims):
       # Double-check in business logic
       if not has_role(user, "admin"):
           raise ForbiddenException(...)

       # Additional validation
       if user_id == user.sub:
           raise ValidationException("Cannot delete yourself")
   ```

3. **Use HTTPS in production**: JWT tokens must be transmitted over HTTPS

4. **Set appropriate token expiration**: Short-lived tokens (1-24 hours)

5. **Implement token refresh**: Use refresh tokens for long sessions

## Common Patterns

### Service Layer with User Context

```python
class StockMovementService:
    async def create_movement(
        self,
        request: StockMovementCreate,
        user: TokenClaims
    ) -> StockMovementResponse:
        # Use user context for audit logging
        movement = await self.repo.create({
            **request.dict(),
            "created_by": user.sub,
            "created_by_email": user.email
        })

        logger.info(
            "Stock movement created",
            movement_id=movement.id,
            user_id=user.sub,
            user_email=user.email
        )

        return StockMovementResponse.from_orm(movement)
```

### Conditional Logic Based on Role

```python
async def get_warehouse_details(
    warehouse_id: int,
    user: TokenClaims = Depends(get_current_user)
):
    warehouse = await warehouse_service.get_by_id(warehouse_id)

    # Admins see everything
    if has_role(user, "admin"):
        return WarehouseDetailResponse.from_orm(warehouse)

    # Supervisors see public + operational data
    elif has_role(user, "supervisor"):
        return WarehouseSupervisorResponse.from_orm(warehouse)

    # Others see public data only
    else:
        return WarehousePublicResponse.from_orm(warehouse)
```

## Troubleshooting

### "Unable to find matching public key"

- Verify AUTH0_DOMAIN is correct
- Check JWKS endpoint is accessible: `https://{AUTH0_DOMAIN}/.well-known/jwks.json`
- Ensure token's `kid` matches a key in JWKS

### "Token expired"

- Check system clock is synchronized
- Verify token expiration time (`exp` claim)
- Implement token refresh if needed

### "Invalid audience"

- Verify AUTH0_API_AUDIENCE matches token's `aud` claim
- Check Auth0 API identifier in dashboard

### "Roles not extracted"

- Verify custom namespace in Auth0: `https://demeter.ai/roles`
- Check Auth0 action/rule adds roles to token
- Verify role claim format: `["admin", "supervisor"]`

## Reference

- **Module**: `app/core/auth.py`
- **Configuration**: `app/core/config.py`
- **Exceptions**: `app/core/exceptions.py`
- **Lines of Code**: 589
- **Dependencies**: `python-jose`, `httpx`, `fastapi`, `pydantic`
