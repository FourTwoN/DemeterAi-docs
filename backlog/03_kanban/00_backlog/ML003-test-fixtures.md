# ML003 - Test Fixtures and Configuration

## Comprehensive Test Fixtures for SAHI Detection Service

**Priority**: ⚡⚡⚡ **CRITICAL PATH**
**Purpose**: Shared test fixtures, mocks, and configuration

---

## Overview

This document provides complete `conftest.py` files and fixture patterns for both unit and
integration tests.

---

## Part 1: Unit Test Fixtures

### File: `tests/unit/conftest.py`

```python
"""
Shared fixtures for unit tests.

Provides common mocks, test data, and configuration for unit testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import torch
import numpy as np
from PIL import Image


# ============================================================================
# Session-scoped Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent.parent / "fixtures"


# ============================================================================
# Function-scoped Fixtures (Reset per test)
# ============================================================================

@pytest.fixture
def mock_model_cache():
    """
    Mock ModelCache.get_model() singleton.

    Returns a mock YOLO model that can be configured per test.
    """
    with patch("app.services.ml_processing.model_cache.ModelCache.get_model") as mock:
        model_instance = MagicMock()

        # Default: empty predictions
        model_instance.predict.return_value = [create_mock_yolo_result(num_detections=0)]

        # Allow test to configure model behavior
        mock.return_value = model_instance
        yield mock


@pytest.fixture
def mock_sahi_library():
    """
    Mock SAHI library components.

    Mocks both get_sliced_prediction and AutoDetectionModel.
    """
    with patch("app.services.ml_processing.sahi_detection_service.get_sliced_prediction") as mock_pred:
        with patch("app.services.ml_processing.sahi_detection_service.AutoDetectionModel") as mock_model:
            # Default: return empty result
            mock_result = create_mock_sahi_result(num_detections=0)
            mock_pred.return_value = mock_result

            yield mock_pred


@pytest.fixture
def mock_image_open():
    """Mock PIL.Image.open()."""
    def _create_image(width=2000, height=1000):
        mock_img = MagicMock(spec=Image.Image)
        mock_img.size = (width, height)
        mock_img.width = width
        mock_img.height = height
        return mock_img

    with patch("PIL.Image.open") as mock_open:
        mock_open.return_value = _create_image()
        mock_open.side_effect = lambda path: _create_image()
        yield mock_open


@pytest.fixture
def mock_path_exists():
    """Mock pathlib.Path.exists() to always return True."""
    with patch("pathlib.Path.exists", return_value=True):
        yield


@pytest.fixture
def mock_cuda_available(request):
    """
    Mock torch.cuda.is_available().

    Use with parameter: @pytest.mark.parametrize("mock_cuda_available", [True, False], indirect=True)
    """
    cuda_available = request.param if hasattr(request, 'param') else False

    with patch("torch.cuda.is_available", return_value=cuda_available):
        yield cuda_available


# ============================================================================
# Helper Fixtures for Test Data Creation
# ============================================================================

@pytest.fixture
def sample_detection_result():
    """Sample DetectionResult for testing."""
    from app.services.ml_processing.sahi_detection_service import DetectionResult

    return DetectionResult(
        center_x_px=500.0,
        center_y_px=300.0,
        width_px=100.0,
        height_px=80.0,
        confidence=0.95,
        class_name="plant"
    )


@pytest.fixture
def sample_detection_list():
    """List of sample DetectionResults."""
    from app.services.ml_processing.sahi_detection_service import DetectionResult

    return [
        DetectionResult(
            center_x_px=100 + i * 150,
            center_y_px=100 + i * 75,
            width_px=100,
            height_px=80,
            confidence=0.9 - i * 0.05,
            class_name="plant"
        )
        for i in range(5)
    ]


# ============================================================================
# Mock Factory Fixtures
# ============================================================================

@pytest.fixture
def create_mock_image():
    """
    Factory fixture for creating mock PIL Images.

    Usage:
        mock_img = create_mock_image(width=3000, height=1500)
    """
    def _create(width: int = 2000, height: int = 1000) -> MagicMock:
        mock_img = MagicMock(spec=Image.Image)
        mock_img.size = (width, height)
        mock_img.width = width
        mock_img.height = height

        # Mock image array
        mock_img.__array__ = lambda: np.random.randint(
            0, 255,
            (height, width, 3),
            dtype=np.uint8
        )

        return mock_img

    return _create


@pytest.fixture
def create_mock_sahi_result():
    """
    Factory fixture for creating mock SAHI results.

    Usage:
        result = create_mock_sahi_result(num_detections=10, centers=[(x, y), ...])
    """
    def _create(
        num_detections: int = 1,
        centers: list[tuple[int, int]] = None,
        confidences: list[float] = None,
        class_names: list[str] = None
    ) -> MagicMock:
        mock_result = MagicMock()

        if centers is None:
            centers = [(512 + i * 100, 256 + i * 50) for i in range(num_detections)]

        if confidences is None:
            confidences = [0.9] * num_detections

        if class_names is None:
            class_names = ["plant"] * num_detections

        detections = []
        for i in range(num_detections):
            mock_obj = MagicMock()

            # Bbox
            cx, cy = centers[i]
            bbox_width = 100
            bbox_height = 80

            mock_obj.bbox.minx = cx - bbox_width // 2
            mock_obj.bbox.maxx = cx + bbox_width // 2
            mock_obj.bbox.miny = cy - bbox_height // 2
            mock_obj.bbox.maxy = cy + bbox_height // 2

            # Score and category
            mock_obj.score.value = confidences[i]
            mock_obj.category.name = class_names[i]
            mock_obj.category.id = 0

            detections.append(mock_obj)

        mock_result.object_prediction_list = detections
        return mock_result

    return _create


@pytest.fixture
def create_mock_yolo_result():
    """
    Factory fixture for creating mock YOLO Results.

    Usage:
        result = create_mock_yolo_result(num_detections=5)
    """
    def _create(num_detections: int = 1, confidences: list[float] = None) -> MagicMock:
        mock_result = MagicMock()

        if num_detections == 0:
            mock_result.boxes = None
            return mock_result

        if confidences is None:
            confidences = [0.9] * num_detections

        # Mock boxes
        mock_boxes = MagicMock()
        mock_boxes.xyxy = torch.tensor([
            [100 + i * 150, 100 + i * 75, 200 + i * 150, 200 + i * 75]
            for i in range(num_detections)
        ], dtype=torch.float32)
        mock_boxes.cls = torch.tensor([0] * num_detections, dtype=torch.int64)
        mock_boxes.conf = torch.tensor(confidences, dtype=torch.float32)

        mock_result.boxes = mock_boxes
        mock_result.names = {0: "plant"}

        return mock_result

    return _create


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sahi_config():
    """Default SAHI configuration for testing."""
    return {
        "slice_height": 512,
        "slice_width": 512,
        "overlap_height_ratio": 0.25,
        "overlap_width_ratio": 0.25,
        "postprocess_type": "GREEDYNMM",
        "postprocess_match_threshold": 0.5,
        "auto_skip_black_tiles": True,
        "verbose": 0
    }


@pytest.fixture
def detection_config():
    """Default detection configuration."""
    return {
        "confidence_threshold": 0.25,
        "iou_threshold": 0.45,
        "max_detections": 3000,
        "device": "cpu"
    }


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_model_cache():
    """
    Auto-use fixture to reset ModelCache between tests.

    Prevents test pollution via singleton state.
    """
    from app.services.ml_processing.model_cache import ModelCache

    # Clear cache before test
    if hasattr(ModelCache, '_cache'):
        ModelCache._cache.clear()

    yield

    # Clear cache after test
    if hasattr(ModelCache, '_cache'):
        ModelCache._cache.clear()


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def caplog_debug(caplog):
    """Capture logs at DEBUG level."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def caplog_info(caplog):
    """Capture logs at INFO level."""
    import logging
    caplog.set_level(logging.INFO)
    return caplog
```

---

## Part 2: Integration Test Fixtures

### File: `tests/integration/conftest.py`

```python
"""
Shared fixtures for integration tests.

Provides real test images, model loading, and cleanup for integration testing.
"""

import pytest
from pathlib import Path
import torch
from PIL import Image
import tempfile
import shutil


# ============================================================================
# Session-scoped Fixtures (Expensive to create)
# ============================================================================

@pytest.fixture(scope="session")
def test_images_dir():
    """Directory containing test images."""
    images_dir = Path(__file__).parent.parent / "fixtures" / "images"

    if not images_dir.exists():
        pytest.fail(f"Test images directory not found: {images_dir}")

    return images_dir


@pytest.fixture(scope="session")
def yolo_detection_model():
    """
    Load real YOLO detection model (session-scoped for performance).

    WARNING: This fixture loads the actual model checkpoint.
    Only use in integration tests.
    """
    from app.services.ml_processing.model_cache import ModelCache

    try:
        model = ModelCache.get_model("detect", worker_id=0)
        yield model
    except Exception as e:
        pytest.skip(f"Could not load YOLO model: {e}")


@pytest.fixture(scope="session")
def temp_output_dir():
    """
    Temporary directory for test outputs.

    Automatically cleaned up after session.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="sahi_test_"))
    yield temp_dir

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# ============================================================================
# Test Image Fixtures
# ============================================================================

@pytest.fixture
def sample_segmento_image(test_images_dir):
    """Path to standard test segmento image (2000×1000)."""
    image_path = test_images_dir / "segmento_2000x1000.jpg"

    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")

    return str(image_path)


@pytest.fixture
def large_segmento_3000x1500(test_images_dir):
    """Path to large segmento (3000×1500) for performance tests."""
    image_path = test_images_dir / "large_segmento_3000x1500.jpg"

    if not image_path.exists():
        # Try to create it
        try:
            create_large_segmento_3000x1500(image_path)
        except Exception:
            pytest.skip(f"Large test image not available: {image_path}")

    return str(image_path)


@pytest.fixture
def very_large_segmento_5000x3000(test_images_dir):
    """Path to very large segmento (5000×3000) for stress tests."""
    image_path = test_images_dir / "very_large_segmento_5000x3000.jpg"

    if not image_path.exists():
        pytest.skip(f"Very large test image not found: {image_path}")

    return str(image_path)


@pytest.fixture
def small_segmento_300x200(test_images_dir):
    """Path to small segmento (<512px) for fallback tests."""
    image_path = test_images_dir / "small_segmento_300x200.jpg"

    if not image_path.exists():
        try:
            create_small_segmento_300x200(image_path)
        except Exception:
            pytest.skip(f"Small test image not available: {image_path}")

    return str(image_path)


@pytest.fixture
def empty_segmento_image(test_images_dir):
    """Path to empty segmento (no plants)."""
    image_path = test_images_dir / "empty_segmento.jpg"

    if not image_path.exists():
        try:
            create_empty_segmento(image_path)
        except Exception:
            pytest.skip(f"Empty test image not available: {image_path}")

    return str(image_path)


@pytest.fixture
def high_density_segmento(test_images_dir):
    """Path to high-density segmento (1000+ plants)."""
    image_path = test_images_dir / "high_density_segmento.jpg"

    if not image_path.exists():
        pytest.skip(f"High-density test image not found: {image_path}")

    return str(image_path)


@pytest.fixture
def low_quality_segmento(test_images_dir):
    """Path to low-quality/blurry segmento."""
    image_path = test_images_dir / "low_quality_segmento.jpg"

    if not image_path.exists():
        pytest.skip(f"Low-quality test image not found: {image_path}")

    return str(image_path)


@pytest.fixture
def segmento_with_small_plants(test_images_dir):
    """Path to segmento with many small plants."""
    image_path = test_images_dir / "small_plants_segmento.jpg"

    if not image_path.exists():
        pytest.skip(f"Small plants test image not found: {image_path}")

    return str(image_path)


# ============================================================================
# Annotated Test Data Fixtures
# ============================================================================

@pytest.fixture
def annotated_segmento_with_ground_truth(test_images_dir):
    """
    Annotated segmento with ground truth plant locations.

    Returns:
        Dict with "image_path" and "annotations"
    """
    image_path = test_images_dir / "annotated_segmento.jpg"
    annotation_path = test_images_dir.parent / "annotations" / "annotated_segmento.json"

    if not image_path.exists() or not annotation_path.exists():
        pytest.skip(f"Annotated test data not found")

    import json
    with open(annotation_path) as f:
        annotations = json.load(f)

    return {
        "image_path": str(image_path),
        "annotations": annotations["plants"]
    }


# ============================================================================
# Performance Fixture
# ============================================================================

@pytest.fixture
def performance_tracker():
    """
    Track performance metrics across tests.

    Usage:
        def test_foo(performance_tracker):
            with performance_tracker.measure("operation"):
                # ... code ...

            assert performance_tracker.get("operation") < 5.0
    """
    import time

    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}

        def measure(self, name: str):
            return self._MeasureContext(self, name)

        def get(self, name: str) -> float:
            return self.metrics.get(name, 0.0)

        def get_all(self) -> dict:
            return self.metrics.copy()

        class _MeasureContext:
            def __init__(self, tracker, name):
                self.tracker = tracker
                self.name = name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, *args):
                elapsed = time.time() - self.start_time
                self.tracker.metrics[self.name] = elapsed

    return PerformanceTracker()


# ============================================================================
# GPU Fixture
# ============================================================================

@pytest.fixture
def gpu_available():
    """Check if GPU is available for tests."""
    return torch.cuda.is_available()


@pytest.fixture
def skip_if_no_gpu():
    """Skip test if GPU not available."""
    if not torch.cuda.is_available():
        pytest.skip("GPU not available")


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Auto-cleanup temporary files created during tests."""
    temp_files = []

    yield temp_files

    # Cleanup
    for temp_file in temp_files:
        try:
            Path(temp_file).unlink(missing_ok=True)
        except Exception:
            pass


# ============================================================================
# Helper Functions (Used by fixtures)
# ============================================================================

def create_large_segmento_3000x1500(output_path: Path):
    """Create realistic 3000×1500 segmento with ~800 plants."""
    from PIL import ImageDraw
    import random

    img = Image.new("RGB", (3000, 1500), color=(40, 70, 35))
    draw = ImageDraw.ImageDraw(img)

    # Grid of plants
    for row in range(20):
        for col in range(40):
            x = 50 + col * 75 + random.randint(-20, 20)
            y = 50 + row * 75 + random.randint(-20, 20)
            radius = random.randint(15, 30)

            color = (
                random.randint(70, 110),
                random.randint(140, 180),
                random.randint(70, 110)
            )

            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=color
            )

    img.save(output_path, quality=90)


def create_empty_segmento(output_path: Path):
    """Create empty segmento (no plants)."""
    img = Image.new("RGB", (2000, 1000), color=(50, 80, 40))
    img.save(output_path, quality=90)


def create_small_segmento_300x200(output_path: Path):
    """Create small segmento for fallback tests."""
    from PIL import ImageDraw
    import random

    img = Image.new("RGB", (300, 200), color=(50, 80, 40))
    draw = ImageDraw.ImageDraw(img)

    for _ in range(5):
        x = random.randint(30, 270)
        y = random.randint(30, 170)
        radius = random.randint(10, 20)
        color = (
            random.randint(80, 120),
            random.randint(150, 200),
            random.randint(80, 120)
        )
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=color
        )

    img.save(output_path, quality=90)
```

---

## Part 3: ML Processing Fixtures

### File: `tests/unit/services/ml_processing/conftest.py`

```python
"""
Fixtures specific to ML processing service tests.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sahi():
    """
    Mock SAHI library for ML processing tests.

    Provides both get_sliced_prediction and AutoDetectionModel.
    """
    with patch("app.services.ml_processing.sahi_detection_service.get_sliced_prediction") as mock_pred:
        with patch("app.services.ml_processing.sahi_detection_service.AutoDetectionModel") as mock_model:
            # Setup default mock model
            mock_detection_model = MagicMock()
            mock_model.from_pretrained.return_value = mock_detection_model

            yield mock_pred


@pytest.fixture
def mock_model_cache():
    """Mock ModelCache.get_model() for ML service tests."""
    with patch("app.services.ml_processing.sahi_detection_service.ModelCache.get_model") as mock:
        model_instance = MagicMock()
        model_instance.predict.return_value = []
        mock.return_value = model_instance
        yield mock


@pytest.fixture
def sahi_service_instance(mock_model_cache):
    """
    Create SAHIDetectionService instance with mocked dependencies.

    Usage:
        def test_foo(sahi_service_instance):
            service = sahi_service_instance
            # ... test service ...
    """
    from app.services.ml_processing.sahi_detection_service import SAHIDetectionService

    return SAHIDetectionService(worker_id=0)
```

---

## Part 4: Pytest Configuration

### File: `pytest.ini`

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, mocked dependencies)
    integration: Integration tests (real models, images)
    benchmark: Performance benchmark tests
    slow: Slow-running tests (>5s)
    gpu: Tests requiring GPU
    cpu_only: Tests that only run on CPU

# Coverage
addopts =
    --strict-markers
    --tb=short
    --verbose
    -ra

# Asyncio
asyncio_mode = auto

# Timeout (prevent hanging tests)
timeout = 300

# Log settings
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)8s] %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Warnings
filterwarnings =
    error
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## Part 5: Test Data Structure

### Directory Structure

```
tests/
├── fixtures/
│   ├── images/
│   │   ├── segmento_2000x1000.jpg
│   │   ├── large_segmento_3000x1500.jpg
│   │   ├── very_large_segmento_5000x3000.jpg
│   │   ├── small_segmento_300x200.jpg
│   │   ├── empty_segmento.jpg
│   │   ├── high_density_segmento.jpg
│   │   ├── low_quality_segmento.jpg
│   │   ├── small_plants_segmento.jpg
│   │   └── annotated_segmento.jpg
│   │
│   ├── annotations/
│   │   └── annotated_segmento.json
│   │
│   └── models/
│       └── yolo11m.pt  (if needed for testing)
│
├── unit/
│   ├── conftest.py
│   └── services/
│       └── ml_processing/
│           ├── conftest.py
│           └── test_sahi_detection_service.py
│
└── integration/
    ├── conftest.py
    └── ml_processing/
        └── test_sahi_integration.py
```

### Annotation File Format

**`tests/fixtures/annotations/annotated_segmento.json`**:

```json
{
  "image": "annotated_segmento.jpg",
  "width": 2000,
  "height": 1000,
  "plants": [
    {
      "id": 1,
      "center_x": 150,
      "center_y": 200,
      "width": 100,
      "height": 80,
      "class": "plant"
    },
    {
      "id": 2,
      "center_x": 450,
      "center_y": 350,
      "width": 110,
      "height": 85,
      "class": "plant"
    }
  ]
}
```

---

## Part 6: CI/CD Integration

### GitHub Actions Workflow

**`.github/workflows/test-ml003.yml`**:

```yaml
name: ML003 SAHI Tests

on:
  pull_request:
    paths:
      - 'app/services/ml_processing/sahi_detection_service.py'
      - 'tests/unit/services/ml_processing/test_sahi_detection_service.py'
      - 'tests/integration/ml_processing/test_sahi_integration.py'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-timeout

      - name: Run unit tests
        run: |
          pytest tests/unit/services/ml_processing/test_sahi_detection_service.py \
            --cov=app.services.ml_processing.sahi_detection_service \
            --cov-report=xml \
            --cov-report=term \
            -v

      - name: Check coverage
        run: |
          coverage report --fail-under=85

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Create test images
        run: |
          python tests/fixtures/create_test_images.py

      - name: Run integration tests (CPU only)
        run: |
          pytest tests/integration/ml_processing/test_sahi_integration.py \
            -m "integration and not gpu" \
            -v

  coverage-report:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Generate coverage badge
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

---

## Success Criteria

### Fixture Checklist

- [ ] ✅ Unit test conftest.py created
- [ ] ✅ Integration test conftest.py created
- [ ] ✅ ML processing-specific conftest.py created
- [ ] ✅ Mock factories implemented
- [ ] ✅ Test image fixtures defined
- [ ] ✅ Performance tracking fixture created
- [ ] ✅ pytest.ini configured
- [ ] ✅ CI/CD workflow defined
- [ ] ✅ Test data structure documented
- [ ] ✅ Annotation format specified

---

**Document Status**: ✅ COMPLETE - Test Fixtures & Configuration
**Next**: Create testing best practices guide
**Last Updated**: 2025-10-14
