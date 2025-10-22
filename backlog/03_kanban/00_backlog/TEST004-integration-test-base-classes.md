# [TEST004] Integration Test Base Classes

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-03
- **Priority**: `medium`
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [TEST001, TEST002]

## Description

Create base classes for integration tests: TestCase with pre-configured DB session, authenticated
client, common assertions.

## Acceptance Criteria

- [ ] `BaseTestCase` class with DB session
- [ ] `AuthenticatedTestCase` class with auth token
- [ ] Helper methods: `assert_status`, `assert_error`, `assert_json_contains`
- [ ] Automatic cleanup after each test

## Implementation

```python
class BaseTestCase:
    @pytest.fixture(autouse=True)
    def setup(self, db_session, client):
        self.session = db_session
        self.client = client

    def assert_status(self, response, status_code):
        assert response.status_code == status_code, \
            f"Expected {status_code}, got {response.status_code}: {response.text}"

    def assert_json_contains(self, response, key, value=None):
        data = response.json()
        assert key in data
        if value is not None:
            assert data[key] == value

class AuthenticatedTestCase(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_auth(self, auth_headers):
        self.auth_headers = auth_headers

    def get(self, url, **kwargs):
        return self.client.get(url, headers=self.auth_headers, **kwargs)

    def post(self, url, **kwargs):
        return self.client.post(url, headers=self.auth_headers, **kwargs)
```

**Usage:**

```python
class TestStockAPI(AuthenticatedTestCase):
    def test_get_stock_summary(self):
        response = self.get("/api/stock/summary")
        self.assert_status(response, 200)
        self.assert_json_contains(response, "total_plants")
```

## Testing

- Test base classes work correctly
- Test helper methods simplify test code
- Test cleanup runs after each test

---
**Card Created**: 2025-10-09
