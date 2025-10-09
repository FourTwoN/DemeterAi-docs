# [TEST002] Pytest Fixtures (Reusable Test Components)

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-02
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [TEST001]

## Description
Create comprehensive pytest fixtures: authenticated client, test users, mock services, sample data.

## Acceptance Criteria
- [ ] `client` fixture (TestClient with FastAPI app)
- [ ] `auth_token` fixture (valid JWT for tests)
- [ ] `test_user` fixture (admin user in DB)
- [ ] `mock_s3_client` fixture (mocked boto3)
- [ ] `mock_redis_client` fixture (fakeredis)
- [ ] Fixtures composable (can depend on each other)

## Implementation
```python
@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)

@pytest.fixture
async def test_user(db_session):
    from app.models.user import User
    user = User(
        email="test@demeterai.com",
        hashed_password="$2b$12$...",
        role="admin",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
def auth_token(test_user):
    from app.services.auth.jwt_service import JWTService
    jwt_service = JWTService()
    return jwt_service.encode_access_token(
        user_id=test_user.id,
        role=test_user.role,
        email=test_user.email
    )

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def mock_s3_client(monkeypatch):
    class MockS3:
        def upload_file(self, *args, **kwargs):
            return {"ETag": "mock"}

    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: MockS3())
```

## Testing
- Test fixtures can be composed
- Test fixtures clean up properly
- Test fixtures isolated per test

---
**Card Created**: 2025-10-09
