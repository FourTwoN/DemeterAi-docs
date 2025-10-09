# [TEST015] End-to-End Tests (Full Workflow)

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-08
- **Priority**: `medium`
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [TEST005, TEST006]

## Description
Complete end-to-end tests simulating real user workflows: photo upload → ML processing → stock movement → analytics.

## Acceptance Criteria
- [ ] **E2E Test 1: Photo-based initialization**
  - Upload photo → ML processing → Stock created
  - Verify detections, estimations, batches
  - Verify stock summary updated

- [ ] **E2E Test 2: Manual initialization**
  - Manual count entry → Stock created
  - Verify movements, batches
  - Verify stock summary updated

- [ ] **E2E Test 3: Monthly reconciliation**
  - Month start photo → Movements → Month end photo
  - Verify sales calculated correctly
  - Verify analytics data

- [ ] **E2E Test 4: Multi-location workflow**
  - Multiple locations → Aggregate stock
  - Verify geospatial queries work
  - Verify analytics by location

- [ ] Tests run against full Docker stack

## Implementation
**tests/e2e/test_photo_workflow.py:**
```python
@pytest.mark.e2e
async def test_complete_photo_workflow(client, auth_headers, test_photo):
    """Test complete photo-based stock initialization."""

    # 1. Upload photo
    with open(test_photo, "rb") as f:
        response = client.post(
            "/api/stock/photo",
            files={"file": f},
            headers=auth_headers,
            data={"location_id": 1}
        )
    assert response.status_code == 201
    photo_session_id = response.json()["photo_session_id"]

    # 2. Wait for ML processing (poll status)
    for _ in range(60):  # Max 60 seconds
        response = client.get(
            f"/api/stock/photo/{photo_session_id}/status",
            headers=auth_headers
        )
        status = response.json()["status"]
        if status == "completed":
            break
        time.sleep(1)
    assert status == "completed"

    # 3. Verify stock created
    response = client.get(
        f"/api/stock/location/1/summary",
        headers=auth_headers
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_plants"] > 0

    # 4. Verify detections created
    response = client.get(
        f"/api/ml/detections/{photo_session_id}",
        headers=auth_headers
    )
    assert len(response.json()["detections"]) > 0

    # 5. Verify estimations created
    response = client.get(
        f"/api/ml/estimations/{photo_session_id}",
        headers=auth_headers
    )
    assert len(response.json()["estimations"]) > 0

    # 6. Verify stock movement created
    response = client.get(
        f"/api/stock/movements?photo_session_id={photo_session_id}",
        headers=auth_headers
    )
    movements = response.json()["movements"]
    assert len(movements) > 0
    assert movements[0]["movement_type"] == "foto"
```

**Run E2E tests:**
```bash
# Start full Docker stack first
docker-compose up -d

# Run E2E tests
pytest -m e2e --host=http://localhost:8000
```

## Testing
- Run against full Docker Compose stack
- Test with real ML models (CPU)
- Verify complete workflows work
- Long-running tests (10-30 min)

---
**Card Created**: 2025-10-09
