# [TEST014] Smoke Tests (Critical Path Only)

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-03
- **Priority**: `high`
- **Complexity**: S (2 points)
- **Dependencies**: Blocked by [TEST006]

## Description

Minimal test suite for post-deployment verification: critical endpoints work, database accessible,
Celery running.

## Acceptance Criteria

- [ ] Smoke tests run in <2 minutes
- [ ] Test only critical paths (health, login, stock summary)
- [ ] Test database connectivity
- [ ] Test Redis connectivity
- [ ] Test Celery workers alive
- [ ] Run after every deployment

## Implementation

**tests/smoke/test_smoke.py:**

```python
@pytest.mark.smoke
def test_health_endpoint(client):
    """Verify API is running."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.smoke
def test_ready_endpoint(client):
    """Verify dependencies accessible."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] is True
    assert data["checks"]["redis"] is True

@pytest.mark.smoke
def test_login_works(client):
    """Verify authentication system works."""
    response = client.post("/api/auth/login", json={
        "email": "admin@demeterai.com",
        "password": os.getenv("ADMIN_PASSWORD")
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.smoke
def test_stock_summary_accessible(client, auth_headers):
    """Verify critical business endpoint works."""
    response = client.get("/api/stock/summary", headers=auth_headers)
    assert response.status_code == 200
```

**Run smoke tests only:**

```bash
pytest -m smoke
```

**CI/CD post-deployment:**

```yaml
- name: Run smoke tests
  run: |
    pytest -m smoke --host=$PRODUCTION_URL
  timeout-minutes: 2
```

## Testing

- Run smoke tests after deploy
- Verify complete in <2 minutes
- If smoke tests fail, rollback deployment

---
**Card Created**: 2025-10-09
