# Epic 009: Authentication & Authorization

**Status**: Ready
**Sprint**: Sprint-04 (Week 9-10)
**Priority**: high (security foundation)
**Total Story Points**: 30
**Total Cards**: 6 (AUTH001-AUTH006)

---

## Goal

Implement JWT-based authentication with role-based access control (RBAC), secure password hashing, and token refresh mechanism for API security.

---

## Success Criteria

- [ ] JWT authentication working (access + refresh tokens)
- [ ] Password hashing with bcrypt (work factor 12)
- [ ] Role-based access control (admin, supervisor, worker, viewer)
- [ ] Token expiration enforced (15min access, 7 days refresh)
- [ ] Secure password reset flow
- [ ] All auth endpoints tested with security best practices

---

## Cards List (6 cards, 30 points)

### Core Auth (15 points)
- **AUTH001**: JWT token generation & validation (5pts)
- **AUTH002**: Password hashing (bcrypt) (3pts)
- **AUTH003**: Login endpoint (5pts)
- **AUTH004**: Token refresh endpoint (2pts)

### User Management (10 points)
- **AUTH005**: User CRUD (admin only) (5pts)
- **AUTH006**: Password reset flow (5pts)

### Authorization (5 points)
- **AUTH007**: Role-based permissions (RBAC) (3pts)
- **AUTH008**: Dependency guards (@require_role) (2pts)

---

## Dependencies

**Blocked By**: DB021 (User model), F005 (Exceptions)
**Blocks**: C001-C026 (protected endpoints)

---

## Technical Approach

**JWT Pattern**:
```python
from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Dependency guard
async def require_auth(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise UnauthorizedException()

# Role guard
def require_role(*roles: str):
    async def guard(user: dict = Depends(require_auth)):
        if user['role'] not in roles:
            raise ForbiddenException()
        return user
    return guard
```

**Usage**:
```python
@router.post("/stock/manual")
async def manual_init(
    request: ManualStockInitRequest,
    user: dict = Depends(require_role("admin", "supervisor"))
):
    # Only admin/supervisor can manually initialize stock
    pass
```

---

**Epic Owner**: Security Lead
**Created**: 2025-10-09
