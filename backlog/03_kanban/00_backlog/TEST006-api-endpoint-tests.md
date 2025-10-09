# [TEST006] API Endpoint Tests

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-03
- **Priority**: `high`
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [TEST001, TEST002]

## Description
Comprehensive tests for all API endpoints: authentication, stock management, photo upload, analytics. Cover happy path and error cases.

## Acceptance Criteria
- [ ] Test all endpoints (GET, POST, PUT, DELETE)
- [ ] Test authentication required (401 without token)
- [ ] Test authorization (403 for insufficient role)
- [ ] Test validation errors (422 for invalid input)
- [ ] Test success responses (200, 201, 204)
- [ ] Test pagination, filtering, sorting
- [ ] Coverage >90% for controllers

## Implementation
```python
class TestAuthEndpoints:
    def test_login_success(self, client):
        response = client.post("/api/auth/login", json={
            "email": "admin@demeterai.com",
            "password": "SecurePass123!"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_invalid_credentials(self, client):
        response = client.post("/api/auth/login", json={
            "email": "admin@demeterai.com",
            "password": "WrongPassword"
        })
        assert response.status_code == 401

class TestStockEndpoints(AuthenticatedTestCase):
    def test_get_stock_summary(self):
        response = self.get("/api/stock/summary")
        self.assert_status(response, 200)
        assert "total_plants" in response.json()

    def test_create_manual_stock_init(self):
        response = self.post("/api/stock/manual", json={
            "location_id": 1,
            "product_id": 10,
            "packaging_id": 5,
            "quantity": 100
        })
        self.assert_status(response, 201)
```

## Testing
- Run: `pytest tests/api/`
- Verify all endpoints covered
- Verify error cases handled
- Check coverage report

---
**Card Created**: 2025-10-09
