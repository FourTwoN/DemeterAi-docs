# Photo Upload V3 Test Suite

Complete test suite for the Photo Upload V3 workflow (Main Flowchart).

## Test Structure

```
tests/
├── unit/
│   └── services/
│       ├── test_photo_upload_validation.py          # File validation (type, size)
│       └── test_photo_upload_service_orchestration.py  # Service orchestration logic
├── integration/
│   └── test_photo_upload_workflow_integration.py    # Full workflow with real DB
├── e2e/
│   ├── test_photo_upload_flow_v3.py                 # Original E2E test (mocked)
│   └── test_photo_upload_flow_v3_complete.py        # Complete E2E with API + DB
└── fixtures/
    └── photo_fixtures.py                            # Shared fixtures
```

## Test Coverage

### Unit Tests (Mocked Dependencies)

**test_photo_upload_validation.py** - File validation logic
- File type validation (JPEG, PNG, WEBP only)
- File size validation (max 20MB)
- Boundary testing (0 bytes, exact limit, over limit)
- Edge cases (empty files, unsupported types)
- Coverage: 100% of validation logic

**test_photo_upload_service_orchestration.py** - Service→Service pattern
- Complete workflow orchestration
- GPS location lookup (Service→LocationService)
- S3 upload (Service→S3ImageService)
- Session creation (Service→SessionService)
- Celery task dispatch verification
- Error handling (location not found, S3 failure, etc.)
- Coverage: ≥80% of PhotoUploadService

### Integration Tests (Real Database, Mocked External Dependencies)

**test_photo_upload_workflow_integration.py** - Complete workflow with real DB
- Real PostgreSQL database with PostGIS
- Real service layer (no business logic mocks)
- GPS lookup via PostGIS ST_Contains
- S3Image record creation
- PhotoProcessingSession creation
- Celery task dispatch (mocked)
- Transaction rollback testing
- Coverage: ≥80% of service layer

### E2E Tests (Real API + Real Database)

**test_photo_upload_flow_v3_complete.py** - Complete E2E workflow
- Real FastAPI HTTP client (httpx AsyncClient)
- Real PostgreSQL database
- Real controller layer
- Real service layer
- Mocked S3 SDK (boto3)
- Mocked Celery broker
- HTTP status code validation
- Multipart/form-data validation
- Task status polling
- Coverage: Complete API workflow

## Test Workflow

### 1. Unit Tests - Fast, Isolated

```bash
# Run unit tests only
pytest tests/unit/services/test_photo_upload_validation.py -v
pytest tests/unit/services/test_photo_upload_service_orchestration.py -v

# With coverage
pytest tests/unit/services/ --cov=app.services.photo --cov-report=term-missing
```

**Expected output:**
- All tests PASS
- Coverage ≥80%
- Execution time: <2 seconds

### 2. Integration Tests - Real Database

```bash
# Start test database
docker-compose up db_test -d

# Run integration tests
pytest tests/integration/test_photo_upload_workflow_integration.py -v

# With coverage
pytest tests/integration/ --cov=app.services.photo --cov-report=term-missing
```

**Expected output:**
- All tests PASS
- GPS lookup via PostGIS works correctly
- Database records created and linked
- Execution time: 5-10 seconds

### 3. E2E Tests - Complete API

```bash
# Start test database
docker-compose up db_test -d

# Run E2E tests
pytest tests/e2e/test_photo_upload_flow_v3_complete.py -v

# With coverage
pytest tests/e2e/ --cov=app --cov-report=term-missing
```

**Expected output:**
- All tests PASS
- API returns 202 ACCEPTED
- Celery tasks dispatched
- Execution time: 10-15 seconds

### 4. Run All Tests

```bash
# Run complete test suite with coverage
pytest tests/unit/services/test_photo_upload*.py \
       tests/integration/test_photo_upload*.py \
       tests/e2e/test_photo_upload_flow_v3_complete.py \
       --cov=app.services.photo \
       --cov=app.controllers.stock_controller \
       --cov-report=term-missing \
       --cov-report=html \
       -v

# View HTML coverage report
open htmlcov/index.html
```

## Test Data

### GPS Coordinates (Santiago, Chile)

All tests use GPS coordinates in Santiago, Chile region:
- Warehouse polygon: (-70.75, -33.55) to (-70.55, -33.35)
- Storage area polygon: (-70.70, -33.50) to (-70.60, -33.40)
- Storage location point: (-70.650, -33.450)

### Test Images

**Minimal JPEG** (~200 bytes):
- Use: Fast validation tests
- Fixture: `minimal_jpeg_bytes`

**Minimal PNG** (~50 bytes):
- Use: PNG file type testing
- Fixture: `minimal_png_bytes`

**Large JPEG** (configurable size):
- Use: Size limit testing
- Function: `create_large_jpeg(size_mb)`

## Key Test Scenarios

### Happy Path
- ✅ Valid JPEG upload with GPS match
- ✅ S3 upload successful
- ✅ Session created with PENDING status
- ✅ Celery task dispatched
- ✅ Response 202 ACCEPTED

### Error Scenarios
- ❌ Invalid file type (PDF, GIF) → 400 Bad Request
- ❌ File too large (>20MB) → 400 Bad Request
- ❌ GPS location not found → 404 Not Found
- ❌ S3 upload failure → 500 Internal Server Error
- ❌ Database connection failure → 500 Internal Server Error

### Edge Cases
- 🔍 Empty file (0 bytes) → PASS (no minimum size)
- 🔍 File exactly 20MB → PASS (boundary test)
- 🔍 GPS on boundary → PASS (PostGIS contains)
- 🔍 Multiple concurrent uploads → PASS (transaction isolation)

## Dependencies Mocked

### External Services (Always Mocked)
- **boto3** (S3 SDK): `app.services.photo.s3_image_service.boto3`
- **Celery tasks**: `app.services.photo.photo_upload_service.ml_parent_task`
- **Celery broker**: `app.tasks.ml_tasks.celery_app`

### Internal Services (Mocked in Unit Tests Only)
- **PhotoProcessingSessionService**: `mock_session_service`
- **S3ImageService**: `mock_s3_service`
- **StorageLocationService**: `mock_location_service`

### Never Mocked
- PostgreSQL database (use real test database)
- PostGIS spatial queries
- Business logic in services
- SQLAlchemy ORM operations

## Coverage Goals

| Test Type | Target Coverage | Actual Coverage |
|-----------|----------------|-----------------|
| Unit Tests | ≥80% | TBD |
| Integration Tests | ≥80% | TBD |
| E2E Tests | Complete API flow | TBD |
| **Overall** | **≥80%** | **TBD** |

## Running Coverage Report

```bash
# Generate coverage report
pytest tests/unit/services/test_photo_upload*.py \
       tests/integration/test_photo_upload*.py \
       tests/e2e/test_photo_upload_flow_v3_complete.py \
       --cov=app.services.photo.photo_upload_service \
       --cov-report=term-missing \
       --cov-report=html

# View report
# TOTAL line should show ≥80%

# View detailed HTML report
open htmlcov/index.html
```

## Troubleshooting

### Tests Failing: Database Connection

```bash
# Check if test database is running
docker ps | grep db_test

# Start test database
docker-compose up db_test -d

# Check database logs
docker logs demeterai-db-test
```

### Tests Failing: Import Errors

```bash
# Verify all dependencies installed
pip install -r requirements.txt

# Verify app package structure
python -c "from app.services.photo.photo_upload_service import PhotoUploadService"
```

### Tests Failing: PostGIS Errors

```bash
# Verify PostGIS extension installed
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c "SELECT PostGIS_version();"

# Expected: "3.3 USE_GEOS=1 USE_PROJ=1 ..."
```

### Coverage Too Low

```bash
# Find untested lines
pytest tests/ --cov=app.services.photo --cov-report=term-missing

# Look for lines marked with "Missing"
# Add tests to cover those lines
```

## Next Steps

1. **Run tests**: `pytest tests/unit/services/test_photo_upload*.py -v`
2. **Check coverage**: Add `--cov` flag
3. **Fix failures**: Adjust tests based on actual implementation
4. **Verify E2E**: Run full E2E test with real database
5. **Document results**: Update coverage table above

## Notes

- All tests use **real PostgreSQL database** (no SQLite)
- PostGIS is **required** for GPS lookup tests
- S3 SDK (boto3) is **always mocked** (no real S3 uploads)
- Celery tasks are **mocked** (no real Celery broker)
- Transaction rollback ensures **test isolation**
- Tests are **idempotent** (can run multiple times)
