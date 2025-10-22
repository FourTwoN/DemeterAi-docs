# Mini-Plan C: Auth0 Integration with JWT Validation

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: MEDIUM (security important but not blocking deployment)
**Complexity**: 8 points (Medium)

---

## Task Overview

Integrate Auth0 for JWT token-based authentication with role-based access control (RBAC). Use Auth0
free tier for testing, implement JWT validation middleware, and create protected endpoints.

---

## Current State Analysis

**Existing Auth**:

- User model exists (DB028 in database/database.mmd)
- Passlib + bcrypt already in requirements.txt
- python-jose in requirements.txt (JWT library)
- No authentication middleware currently

**Missing**:

- Auth0 account setup
- JWT validation middleware
- Protected route decorator
- Login/logout endpoints
- Role-based access control
- Auth0 configuration in settings

---

## Architecture

**Layer**: Infrastructure (Security Layer)
**Pattern**: Auth0 (Identity Provider) → JWT → FastAPI Middleware → Protected Routes

**Dependencies**:

- Existing packages: python-jose[cryptography], passlib, bcrypt
- New packages: python-multipart (for form data)
- Auth0 account (free tier)
- Environment variables: AUTH0_DOMAIN, AUTH0_API_AUDIENCE, AUTH0_CLIENT_ID

**Files to Create/Modify**:

- [ ] `app/core/auth.py` (create - JWT validation, Auth0 integration)
- [ ] `app/core/security.py` (create - password hashing, token utils)
- [ ] `app/core/dependencies.py` (create - dependency injection for auth)
- [ ] `app/controllers/auth_controller.py` (create - login/logout endpoints)
- [ ] `app/schemas/auth.py` (create - Token, UserLogin schemas)
- [ ] `app/core/config.py` (modify - add Auth0 settings)
- [ ] `.env.example` (modify - add Auth0 variables)
- [ ] `tests/integration/test_auth.py` (create - test auth endpoints)

---

## Implementation Strategy

### Phase 1: Auth0 Account Setup

**Steps**:

1. Create Auth0 account (free tier): https://auth0.com/signup
2. Create new API in Auth0 dashboard
3. Get credentials:
    - AUTH0_DOMAIN (e.g., demeterai.us.auth0.com)
    - AUTH0_API_AUDIENCE (e.g., https://api.demeterai.com)
    - AUTH0_CLIENT_ID
4. Configure RBAC in Auth0:
    - Roles: admin, supervisor, worker, viewer
    - Permissions: stock:read, stock:write, analytics:read, etc.

### Phase 2: Update app/core/config.py

**Add Auth0 configuration**:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Authentication (Auth0)
    AUTH0_DOMAIN: str = ""  # e.g., demeterai.us.auth0.com
    AUTH0_API_AUDIENCE: str = ""  # e.g., https://api.demeterai.com
    AUTH0_ALGORITHMS: list[str] = ["RS256"]
    AUTH0_ISSUER: str = ""  # e.g., https://demeterai.us.auth0.com/

    # JWT configuration
    JWT_SECRET_KEY: str = ""  # For local JWT signing (fallback)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

### Phase 3: Create app/core/auth.py

**Responsibilities**:

- Verify JWT tokens from Auth0
- Decode and validate JWT
- Extract user claims (sub, roles, permissions)
- JWKS (JSON Web Key Set) fetching

**Key Functions**:

```python
from jose import jwt, jwk
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class Auth0Verifier:
    """Verify JWT tokens issued by Auth0."""

    def __init__(self, domain: str, audience: str, algorithms: list[str]):
        self.domain = domain
        self.audience = audience
        self.algorithms = algorithms
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._jwks_cache: dict[str, Any] = {}

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify JWT token and return decoded claims."""
        # 1. Decode header to get key ID (kid)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # 2. Fetch JWKS (cache for performance)
        if not self._jwks_cache:
            self._jwks_cache = await self._fetch_jwks()

        # 3. Get signing key
        signing_key = self._jwks_cache.get(kid)
        if not signing_key:
            raise HTTPException(status_code=401, detail="Invalid token key")

        # 4. Verify and decode token
        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTClaimsError:
            raise HTTPException(status_code=401, detail="Invalid claims")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JSON Web Key Set from Auth0."""
        # Use httpx to fetch JWKS
        # Cache keys for 24 hours
        pass

# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict[str, Any]:
    """Dependency to get current authenticated user from JWT."""
    token = credentials.credentials
    verifier = Auth0Verifier(
        domain=settings.AUTH0_DOMAIN,
        audience=settings.AUTH0_API_AUDIENCE,
        algorithms=settings.AUTH0_ALGORITHMS
    )
    return await verifier.verify_token(token)
```

### Phase 4: Create app/core/security.py

**Password hashing utilities** (for local users if needed):

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

### Phase 5: Create app/controllers/auth_controller.py

**Authentication endpoints**:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.schemas.auth import Token, UserLogin

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login endpoint - redirect to Auth0 or validate credentials.

    Note: In production, use Auth0 Universal Login.
    This is a placeholder for testing.
    """
    # For Auth0, this typically redirects to Auth0 login page
    # Returns: {"access_token": "...", "token_type": "Bearer"}
    pass

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information from JWT claims."""
    return {
        "user_id": current_user.get("sub"),
        "email": current_user.get("email"),
        "roles": current_user.get("roles", []),
        "permissions": current_user.get("permissions", [])
    }

@router.post("/logout")
async def logout():
    """Logout endpoint - invalidate session."""
    # For Auth0, this typically clears cookies/session
    return {"message": "Logged out successfully"}
```

### Phase 6: Protect Existing Endpoints

**Example - protect stock endpoints**:

```python
# In app/controllers/stock_controller.py
from app.core.auth import get_current_user

@router.post("/batches", dependencies=[Depends(get_current_user)])
async def create_stock_batch(...):
    """Create stock batch - requires authentication."""
    pass

# For role-based access:
def require_role(role: str):
    """Dependency to require specific role."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if role not in user_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@router.delete("/batches/{id}", dependencies=[Depends(require_role("admin"))])
async def delete_stock_batch(...):
    """Delete stock batch - requires admin role."""
    pass
```

### Phase 7: Update .env.example

```bash
# =============================================================================
# Authentication (Auth0)
# =============================================================================
# Auth0 domain (from Auth0 dashboard)
AUTH0_DOMAIN=demeterai.us.auth0.com

# Auth0 API audience (identifier for your API)
AUTH0_API_AUDIENCE=https://api.demeterai.com

# Auth0 issuer URL
AUTH0_ISSUER=https://demeterai.us.auth0.com/

# JWT algorithms (RS256 for Auth0)
AUTH0_ALGORITHMS=["RS256"]

# Local JWT configuration (fallback for development)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Acceptance Criteria

- [ ] Auth0 account created (free tier)
- [ ] Auth0 API configured with RBAC roles
- [ ] `app/core/auth.py` implements JWT verification
- [ ] `app/core/security.py` implements password hashing
- [ ] `app/controllers/auth_controller.py` created with login/logout/me endpoints
- [ ] JWT tokens validated against Auth0 JWKS
- [ ] Protected endpoints require authentication
- [ ] Role-based access control implemented
- [ ] Integration tests pass
- [ ] Unauthorized requests return 401
- [ ] Forbidden requests (wrong role) return 403

---

## Testing Procedure

```bash
# 1. Configure Auth0 credentials in .env
# AUTH0_DOMAIN=...
# AUTH0_API_AUDIENCE=...

# 2. Start application
uvicorn app.main:app --reload

# 3. Test unauthenticated request (should fail)
curl http://localhost:8000/api/v1/stock/batches
# Expected: 401 Unauthorized

# 4. Get test token from Auth0
# Use Auth0 dashboard or curl to get token
# curl --request POST \
#   --url https://YOUR_DOMAIN/oauth/token \
#   --data '{"client_id":"...","client_secret":"...","audience":"...","grant_type":"client_credentials"}'

# 5. Test authenticated request
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/auth/me
# Expected: User claims (sub, email, roles)

# 6. Test protected endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/stock/batches
# Expected: 200 OK

# 7. Run integration tests
pytest tests/integration/test_auth.py -v
```

---

## Performance Expectations

- JWT validation: <10ms (JWKS cached)
- JWKS refresh: Once per 24 hours
- No database lookup for token validation
- Stateless authentication (JWT self-contained)

---

## Dependencies

**Blocked By**: None (can run in parallel)
**Blocks**: Production deployment (security requirement)

**External Dependency**: Auth0 account and configuration

---

## Notes

- Auth0 free tier limits: 7,000 active users, unlimited logins
- JWKS (JSON Web Key Set) should be cached to avoid excessive Auth0 API calls
- For development, can use Auth0 test tokens
- Consider implementing token refresh mechanism (out of scope for Sprint 5)
- RBAC roles: admin, supervisor, worker, viewer (defined in Auth0)
- Permissions can be checked in JWT claims: `permissions: ["stock:read", "stock:write"]`

---

## Auth0 Setup Guide (For Team)

**Step 1: Create Auth0 Account**

1. Go to https://auth0.com/signup
2. Sign up with email
3. Create tenant (e.g., demeterai)

**Step 2: Create API**

1. Go to Applications → APIs
2. Click "Create API"
3. Name: DemeterAI v2.0
4. Identifier: https://api.demeterai.com
5. Signing Algorithm: RS256
6. Enable RBAC: Yes
7. Add Permissions in Token: Yes

**Step 3: Define Roles & Permissions**

1. Go to User Management → Roles
2. Create roles:
    - admin: All permissions
    - supervisor: stock:*, analytics:read
    - worker: stock:read, stock:write
    - viewer: stock:read, analytics:read

**Step 4: Define Permissions**

1. In API settings → Permissions tab
2. Add permissions:
    - stock:read, stock:write, stock:delete
    - analytics:read
    - config:read, config:write
    - users:manage

**Step 5: Get Credentials**

1. Copy AUTH0_DOMAIN (e.g., demeterai.us.auth0.com)
2. Copy AUTH0_API_AUDIENCE (e.g., https://api.demeterai.com)
3. Add to .env file
