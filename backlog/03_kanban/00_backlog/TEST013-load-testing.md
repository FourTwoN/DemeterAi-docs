# [TEST013] Load Testing (Locust/k6)

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-08
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [DEP002]

## Description

Simulate production load: 1000 concurrent users, verify API handles load, identify bottlenecks.

## Acceptance Criteria

- [ ] Load test tool selected (Locust or k6)
- [ ] Simulate 1000 concurrent users
- [ ] Test critical endpoints (login, stock summary, photo upload)
- [ ] Measure p95/p99 latency under load
- [ ] Identify bottlenecks (DB, Celery, API)
- [ ] Target: <200ms p95 latency, <1% error rate

## Implementation

**Option A: Locust (Python)**

```python
# locustfile.py
from locust import HttpUser, task, between

class DemeterAIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login once per user."""
        response = self.client.post("/api/auth/login", json={
            "email": "test@demeterai.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def get_stock_summary(self):
        self.client.get("/api/stock/summary", headers=self.headers)

    @task(1)
    def upload_photo(self):
        with open("test_photo.jpg", "rb") as f:
            self.client.post(
                "/api/stock/photo",
                files={"file": f},
                headers=self.headers
            )
```

**Run Locust:**

```bash
locust -f locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=50
```

**Option B: k6 (JavaScript, more lightweight)**

```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 1000 },  // Ramp up to 1000 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],  // 95% requests <200ms
    http_req_failed: ['rate<0.01'],    // <1% error rate
  },
};

export default function () {
  let response = http.get('http://localhost:8000/api/stock/summary');
  check(response, { 'status is 200': (r) => r.status === 200 });
}
```

## Testing

- Run load test on staging environment
- Monitor metrics (Grafana dashboards)
- Identify bottlenecks (slow queries, connection pool exhausted)
- Optimize and re-test

---
**Card Created**: 2025-10-09
