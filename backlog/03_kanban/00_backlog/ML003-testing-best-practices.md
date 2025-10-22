# ML003 - Testing Best Practices for SAHI Detection Service

## Testing Expert Best Practices & Patterns

**Priority**: ⚡⚡⚡ **CRITICAL PATH**
**Purpose**: Guidelines for writing high-quality, maintainable tests

---

## Overview

This guide provides proven patterns, anti-patterns, and best practices for testing the SAHI
Detection Service effectively.

---

## Part 1: Testing Philosophy

### Critical Path Testing Mindset

```
┌─────────────────────────────────────────────────────────┐
│ CRITICAL PATH TESTING PRINCIPLES                        │
├─────────────────────────────────────────────────────────┤
│ 1. Test BEHAVIOR, not implementation                    │
│ 2. Mock EXTERNAL dependencies, use REAL logic           │
│ 3. Test EDGE CASES first (they find bugs)              │
│ 4. Performance benchmarks are REQUIRED                  │
│ 5. Coverage ≥85% is NON-NEGOTIABLE                     │
│ 6. Tests must be FAST (<2min total)                    │
│ 7. Tests must be RELIABLE (no flakiness)               │
└─────────────────────────────────────────────────────────┘
```

### Test Pyramid for ML003

```
         Integration Tests (15 tests, 30% coverage)
         ┌─────────────────────────┐
         │ • Real models           │
         │ • Real SAHI library     │
         │ • Real images           │
         │ • Performance benchmarks│
         └─────────────────────────┘
                   ▲
                   │
                   │
    ┌──────────────┴──────────────┐
    │                             │
Unit Tests (30+ tests, 70% coverage)
┌────────────────────────────────────┐
│ • Mocked dependencies              │
│ • Fast execution (<100ms per test) │
│ • Isolated logic                   │
│ • Edge cases                       │
└────────────────────────────────────┘
```

**Why this ratio?**

- **Unit tests**: Fast feedback, easy debugging, high coverage
- **Integration tests**: Validate real-world behavior, catch integration issues

---

## Part 2: Unit Testing Best Practices

### ✅ DO: Test Behavior, Not Implementation

```python
# ✅ GOOD: Test behavior
@pytest.mark.asyncio
async def test_sahi_detects_plants_in_large_image(mock_sahi, mock_model_cache):
    """Test SAHI successfully detects plants in large segmento."""
    service = SAHIDetectionService()

    # Setup: Large image with plants
    mock_image = create_mock_image(width=3000, height=1500)
    mock_sahi_result = create_mock_sahi_result(num_detections=850)

    # Execute
    results = await service.detect_in_segmento("/fake/large.jpg")

    # Assert: Behavior
    assert len(results) == 850
    assert all(isinstance(r, DetectionResult) for r in results)
    assert all(0.0 < r.confidence <= 1.0 for r in results)


# ❌ BAD: Test implementation details
@pytest.mark.asyncio
async def test_sahi_calls_get_sliced_prediction_internally():
    """DON'T test internal method calls (implementation detail)."""
    # This is brittle - if we refactor, test breaks
    ...
```

### ✅ DO: Mock External Dependencies Only

```python
# ✅ GOOD: Mock SAHI library (external dependency)
@pytest.fixture
def mock_sahi():
    with patch("app.services.ml_processing.sahi_detection_service.get_sliced_prediction") as mock:
        yield mock


# ✅ GOOD: Mock ModelCache (external singleton)
@pytest.fixture
def mock_model_cache():
    with patch("app.services.ml_processing.sahi_detection_service.ModelCache.get_model") as mock:
        yield mock


# ❌ BAD: Mock internal service methods
@pytest.mark.asyncio
async def test_bad_mocking():
    service = SAHIDetectionService()

    # DON'T mock internal methods of the class you're testing
    with patch.object(service, '_validate_image_path'):
        ...
```

### ✅ DO: Test One Thing Per Test

```python
# ✅ GOOD: Focused test
@pytest.mark.asyncio
async def test_empty_segmento_returns_empty_list():
    """Test empty segmento (no plants) returns empty list."""
    service = SAHIDetectionService()

    results = await service.detect_in_segmento("/fake/empty.jpg")

    assert results == []


# ❌ BAD: Testing multiple things
@pytest.mark.asyncio
async def test_everything_at_once():
    """DON'T test multiple behaviors in one test."""
    service = SAHIDetectionService()

    # Testing empty, small, and large images
    assert await service.detect_in_segmento("/empty.jpg") == []
    assert len(await service.detect_in_segmento("/small.jpg")) > 0
    assert len(await service.detect_in_segmento("/large.jpg")) > 100
    # Now debugging is hard - which assertion failed?
```

### ✅ DO: Use Descriptive Test Names

```python
# ✅ GOOD: Clear intent
@pytest.mark.asyncio
async def test_greedynmm_merges_boundary_detections():
    """Test plant on tile boundary merged to 1 detection, not 2."""
    ...


@pytest.mark.asyncio
async def test_raises_filenotfound_if_image_missing():
    """Test FileNotFoundError if image doesn't exist."""
    ...


# ❌ BAD: Vague names
@pytest.mark.asyncio
async def test_detection():
    """What does this test? No idea."""
    ...


@pytest.mark.asyncio
async def test_case_1():
    """What is case 1? Who knows."""
    ...
```

### ✅ DO: Arrange-Act-Assert Pattern

```python
# ✅ GOOD: Clear AAA structure
@pytest.mark.asyncio
async def test_sahi_uses_greedynmm_postprocessing(mock_sahi, mock_model_cache):
    """Test SAHI uses GREEDYNMM for duplicate removal."""
    # ARRANGE
    service = SAHIDetectionService()
    mock_image = create_mock_image(width=2000, height=1000)
    mock_sahi_result = create_mock_sahi_result(num_detections=1)
    mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

    # ACT
    with patch("PIL.Image.open", return_value=mock_image):
        with patch("pathlib.Path.exists", return_value=True):
            await service.detect_in_segmento("/fake/segmento.jpg")

    # ASSERT
    call_kwargs = mock_sahi.get_sliced_prediction.call_args.kwargs
    assert call_kwargs["postprocess_type"] == "GREEDYNMM"
    assert call_kwargs["postprocess_match_threshold"] == 0.5


# ❌ BAD: Mixed structure
@pytest.mark.asyncio
async def test_confusing_structure():
    service = SAHIDetectionService()
    results = await service.detect_in_segmento("/fake.jpg")  # Act before Arrange?
    mock_image = create_mock_image(width=2000, height=1000)  # Arrange after Act?
    assert len(results) > 0  # Assert in the middle?
    # Confusing!
```

---

## Part 3: Integration Testing Best Practices

### ✅ DO: Use Real Dependencies

```python
# ✅ GOOD: Real model, real SAHI
@pytest.mark.integration
@pytest.mark.asyncio
async def test_sahi_detects_many_plants(large_segmento_3000x1500):
    """Test SAHI detects 500-800+ plants in real large segmento."""
    service = SAHIDetectionService()  # No mocks!

    results = await service.detect_in_segmento(large_segmento_3000x1500)

    assert len(results) >= 100
```

### ✅ DO: Measure Performance

```python
# ✅ GOOD: Performance benchmark
@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cpu_performance_3000x1500_under_10s(large_segmento_3000x1500):
    """Test CPU inference completes in <10s for 3000×1500 image."""
    service = SAHIDetectionService()

    start = time.time()
    results = await service.detect_in_segmento(large_segmento_3000x1500)
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"CPU Performance: {elapsed:.2f}s (target: <10s)")
    print(f"Detections: {len(results)}")
    print(f"{'='*60}\n")

    assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s"
    assert len(results) > 0
```

### ✅ DO: Use Skip When Resources Unavailable

```python
# ✅ GOOD: Skip gracefully
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_real_image(sample_segmento_image):
    """Test detection on real image."""
    # Fixture automatically skips if image not found
    service = SAHIDetectionService()
    results = await service.detect_in_segmento(sample_segmento_image)
    assert len(results) >= 0


# Fixture:
@pytest.fixture
def sample_segmento_image(test_images_dir):
    image_path = test_images_dir / "segmento.jpg"
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    return str(image_path)
```

---

## Part 4: Async Testing Patterns

### ✅ DO: Use pytest-asyncio

```python
# ✅ GOOD: Proper async test
@pytest.mark.asyncio
async def test_async_detection(mock_sahi, mock_model_cache):
    """Test async detection method."""
    service = SAHIDetectionService()

    # Async method call
    results = await service.detect_in_segmento("/fake/segmento.jpg")

    assert isinstance(results, list)


# ❌ BAD: Forgetting @pytest.mark.asyncio
async def test_async_without_marker():
    """This test will NOT run (missing marker)."""
    service = SAHIDetectionService()
    results = await service.detect_in_segmento("/fake.jpg")
    # Never executed!
```

### ✅ DO: Use AsyncMock for Async Dependencies

```python
# ✅ GOOD: AsyncMock for async methods
@pytest.fixture
def mock_async_service():
    with patch("app.services.ml_processing.some_async_service") as mock:
        mock_instance = AsyncMock()
        mock_instance.async_method.return_value = "result"
        mock.return_value = mock_instance
        yield mock


# ❌ BAD: Regular Mock for async (will fail)
@pytest.fixture
def mock_async_service_bad():
    with patch("app.services.ml_processing.some_async_service") as mock:
        mock_instance = MagicMock()  # Should be AsyncMock!
        mock_instance.async_method.return_value = "result"
        mock.return_value = mock_instance
        yield mock
```

---

## Part 5: Mocking Patterns

### Pattern 1: Mock External Libraries

```python
# ✅ GOOD: Mock SAHI library at import level
@pytest.fixture
def mock_sahi():
    with patch("app.services.ml_processing.sahi_detection_service.get_sliced_prediction") as mock:
        yield mock


# ❌ BAD: Mock at wrong level
@pytest.fixture
def mock_sahi_bad():
    with patch("sahi.predict.get_sliced_prediction") as mock:
        # This might work, but is less explicit
        yield mock
```

### Pattern 2: Mock Singleton Pattern

```python
# ✅ GOOD: Mock singleton getter
@pytest.fixture
def mock_model_cache():
    with patch("app.services.ml_processing.sahi_detection_service.ModelCache.get_model") as mock:
        model_instance = MagicMock()
        mock.return_value = model_instance
        yield mock


# ✅ GOOD: Reset singleton state
@pytest.fixture(autouse=True)
def reset_model_cache():
    from app.services.ml_processing.model_cache import ModelCache

    if hasattr(ModelCache, '_cache'):
        ModelCache._cache.clear()

    yield

    if hasattr(ModelCache, '_cache'):
        ModelCache._cache.clear()
```

### Pattern 3: Factory Fixtures

```python
# ✅ GOOD: Factory fixture for flexible test data
@pytest.fixture
def create_mock_sahi_result():
    def _create(num_detections: int = 1, centers: list = None, confidences: list = None):
        mock_result = MagicMock()
        # ... create mock result ...
        return mock_result

    return _create


# Usage:
def test_with_custom_detections(create_mock_sahi_result):
    result = create_mock_sahi_result(
        num_detections=10,
        centers=[(100, 100), (200, 200), ...],
        confidences=[0.9, 0.85, ...]
    )
    # ... test with customized result ...
```

---

## Part 6: Coverage Best Practices

### ✅ DO: Aim for ≥85% Coverage

```bash
# Check coverage
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py \
    --cov=app.services.ml_processing.sahi_detection_service \
    --cov-report=term-missing \
    --cov-report=html

# Output:
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# app/services/sahi_detection_service.py    120     12    90%   78-82, 91-95
# ---------------------------------------------------------------------
```

### ✅ DO: Focus on Critical Paths

**Priority coverage targets:**

1. **100%**: Core detection logic (`detect_in_segmento`)
2. **100%**: Error handling (all exception paths)
3. **100%**: Coordinate mapping logic
4. **90%**: Configuration and initialization
5. **80%**: Logging and debug code

### ❌ DON'T: Chase 100% at Expense of Quality

```python
# ❌ BAD: Useless test for coverage
def test_logging_statement():
    """Test that logger.info is called (useless!)."""
    with patch("logging.info") as mock_log:
        service.detect_in_segmento("/fake.jpg")
        assert mock_log.called
    # This adds coverage but no value


# ✅ GOOD: Meaningful test
def test_logs_performance_metrics(caplog):
    """Test performance metrics are logged for debugging."""
    with caplog.at_level("INFO"):
        await service.detect_in_segmento("/fake.jpg")

    # Assert meaningful content
    assert "detections" in caplog.text.lower()
    assert "took" in caplog.text.lower() or "ms" in caplog.text.lower()
```

---

## Part 7: Error Testing Patterns

### ✅ DO: Test All Exception Paths

```python
# ✅ GOOD: Test specific exceptions
@pytest.mark.asyncio
async def test_raises_filenotfound_if_image_missing():
    """Test FileNotFoundError if image doesn't exist."""
    service = SAHIDetectionService()

    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Image not found"):
            await service.detect_in_segmento("/nonexistent.jpg")


# ✅ GOOD: Test error message content
@pytest.mark.asyncio
async def test_error_message_includes_file_path():
    """Test error message includes problematic file path."""
    service = SAHIDetectionService()

    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError) as exc_info:
            await service.detect_in_segmento("/path/to/missing.jpg")

        assert "/path/to/missing.jpg" in str(exc_info.value)
```

### ✅ DO: Test Graceful Degradation

```python
# ✅ GOOD: Test graceful handling of edge cases
@pytest.mark.asyncio
async def test_empty_segmento_returns_empty_list_not_error():
    """Test empty segmento returns [] instead of raising error."""
    service = SAHIDetectionService()

    # Should NOT raise exception
    results = await service.detect_in_segmento("/fake/empty.jpg")

    assert results == []
    assert isinstance(results, list)
```

---

## Part 8: Performance Testing Patterns

### ✅ DO: Measure Time Consistently

```python
# ✅ GOOD: Consistent timing
import time

@pytest.mark.asyncio
async def test_performance_benchmark():
    service = SAHIDetectionService()

    start = time.time()
    await service.detect_in_segmento("/fake/large.jpg")
    elapsed = time.time() - start

    assert elapsed < 10.0


# ❌ BAD: Inconsistent timing
@pytest.mark.asyncio
async def test_performance_bad():
    import datetime
    start = datetime.datetime.now()
    await service.detect_in_segmento("/fake/large.jpg")
    elapsed = (datetime.datetime.now() - start).total_seconds()
    # Mixing time.time() and datetime is confusing
```

### ✅ DO: Print Performance Reports

```python
# ✅ GOOD: Informative output
@pytest.mark.asyncio
async def test_performance_with_report():
    service = SAHIDetectionService()

    start = time.time()
    results = await service.detect_in_segmento("/fake/large.jpg")
    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"Performance Benchmark")
    print(f"{'='*60}")
    print(f"Time:       {elapsed:.2f}s")
    print(f"Detections: {len(results)}")
    print(f"Target:     <10s")
    print(f"Status:     {'✅ PASS' if elapsed < 10.0 else '❌ FAIL'}")
    print(f"{'='*60}\n")

    assert elapsed < 10.0
```

---

## Part 9: Test Organization

### Directory Structure

```
tests/
├── unit/
│   ├── conftest.py                    # Shared unit test fixtures
│   └── services/
│       └── ml_processing/
│           ├── conftest.py            # ML-specific fixtures
│           └── test_sahi_detection_service.py  # Main test file
│
├── integration/
│   ├── conftest.py                    # Shared integration fixtures
│   └── ml_processing/
│       └── test_sahi_integration.py   # Integration tests
│
└── fixtures/
    ├── images/                        # Test images
    ├── annotations/                   # Ground truth data
    └── create_test_images.py          # Script to generate test data
```

### Test Class Organization

```python
# ✅ GOOD: Organized by feature
class TestSAHIDetectionServiceBasic:
    """Basic service functionality."""
    # test_service_initialization()
    # test_detect_uses_model_cache()


class TestSAHITilingConfiguration:
    """SAHI tiling parameters."""
    # test_sahi_called_with_correct_tile_size()
    # test_sahi_uses_greedynmm()


class TestSAHICoordinateMapping:
    """Coordinate mapping logic."""
    # test_coordinates_in_original_image_space()
    # test_all_detections_within_bounds()
```

---

## Part 10: Common Anti-Patterns

### ❌ ANTI-PATTERN 1: Testing Implementation Details

```python
# ❌ BAD
def test_sahi_calls_autodetectionmodel():
    """DON'T test that specific internal methods are called."""
    service = SAHIDetectionService()

    with patch("sahi.AutoDetectionModel.from_pretrained") as mock:
        await service.detect_in_segmento("/fake.jpg")
        assert mock.called  # Brittle!
```

### ❌ ANTI-PATTERN 2: Flaky Tests

```python
# ❌ BAD: Timing-dependent test
@pytest.mark.asyncio
async def test_performance_exactly_5s():
    """DON'T test exact timing (flaky on CI)."""
    start = time.time()
    await service.detect_in_segmento("/fake.jpg")
    elapsed = time.time() - start

    assert elapsed == 5.0  # Will fail randomly!


# ✅ GOOD: Use ranges
assert 4.5 <= elapsed <= 5.5  # More robust
```

### ❌ ANTI-PATTERN 3: Test Interdependence

```python
# ❌ BAD: Tests depend on each other
class TestBadPattern:
    detection_results = None  # Shared state!

    def test_1_detect(self):
        self.detection_results = service.detect_in_segmento("/fake.jpg")

    def test_2_validate(self):
        # Depends on test_1 running first!
        assert len(self.detection_results) > 0
```

### ❌ ANTI-PATTERN 4: Mocking Too Much

```python
# ❌ BAD: Over-mocking
@pytest.mark.asyncio
async def test_with_too_many_mocks():
    """DON'T mock everything (you're not testing anything!)."""
    with patch("PIL.Image.open"):
        with patch("pathlib.Path.exists"):
            with patch("app.services.sahi_detection_service.SAHIDetectionService.detect_in_segmento"):
                # You just mocked the method you're testing!
                results = await service.detect_in_segmento("/fake.jpg")
                # This proves nothing
```

---

## Part 11: Debugging Test Failures

### Strategy 1: Use -v and -s Flags

```bash
# Verbose + capture output
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py -v -s

# Show local variables on failure
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py -v -l

# Drop into debugger on failure
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py -v --pdb
```

### Strategy 2: Print Debugging

```python
# ✅ GOOD: Informative debug prints
@pytest.mark.asyncio
async def test_with_debug_info():
    service = SAHIDetectionService()

    results = await service.detect_in_segmento("/fake.jpg")

    print(f"\n=== DEBUG INFO ===")
    print(f"Results count: {len(results)}")
    print(f"First result: {results[0] if results else 'N/A'}")
    print(f"==================\n")

    assert len(results) > 0
```

### Strategy 3: Isolate Failing Test

```bash
# Run single test
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py::TestSAHIBasic::test_specific_test -v

# Run with increased verbosity
pytest tests/unit/services/ml_processing/test_sahi_detection_service.py::TestSAHIBasic::test_specific_test -vv
```

---

## Part 12: Code Review Checklist

### Before Submitting PR

- [ ] ✅ All tests pass locally
- [ ] ✅ Coverage ≥85%
- [ ] ✅ No skipped tests (unless documented)
- [ ] ✅ No flaky tests (run 3× to verify)
- [ ] ✅ Performance benchmarks included
- [ ] ✅ Test names are descriptive
- [ ] ✅ Docstrings explain WHAT and WHY
- [ ] ✅ Fixtures are documented
- [ ] ✅ No hardcoded paths (use fixtures)
- [ ] ✅ No print() statements (use logging/caplog)
- [ ] ✅ Error messages are helpful

---

## Summary: Golden Rules

```
┌─────────────────────────────────────────────────────────┐
│ TESTING GOLDEN RULES FOR ML003                          │
├─────────────────────────────────────────────────────────┤
│ 1. Test BEHAVIOR, not implementation                    │
│ 2. Unit tests FAST (<100ms), integration SLOW (<30s)   │
│ 3. Mock EXTERNAL deps, use REAL internal logic         │
│ 4. Coverage ≥85% REQUIRED                              │
│ 5. One test = One assertion category                    │
│ 6. Descriptive names (test_what_when_expected)         │
│ 7. AAA pattern: Arrange-Act-Assert                     │
│ 8. Test edge cases FIRST (they find bugs)              │
│ 9. Performance benchmarks REQUIRED                      │
│ 10. No flaky tests (deterministic results)             │
└─────────────────────────────────────────────────────────┘
```

---

**Document Status**: ✅ COMPLETE - Testing Best Practices
**Next**: Final validation and summary report
**Last Updated**: 2025-10-14
