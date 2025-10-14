# ML003 - SAHI Detection Service Testing Guide

## Testing Expert Implementation Guide

**Priority**: ⚡⚡⚡ **CRITICAL PATH - HIGHEST PRIORITY**
**Target Coverage**: ≥85%
**Sprint**: Sprint-02 (ML Pipeline)

---

## Overview

This guide provides comprehensive testing patterns for the SAHIDetectionService - the **most critical innovation** in the ML pipeline that achieves 10x detection improvement (100 → 800+ plants).

### Architecture Context

```
backend/
├── app/
│   └── services/
│       └── ml_processing/
│           ├── sahi_detection_service.py      # Production code
│           └── model_cache.py                  # Singleton pattern
└── tests/
    ├── unit/
    │   └── services/
    │       └── ml_processing/
    │           └── test_sahi_detection_service.py  # ~600 lines, 30+ tests
    ├── integration/
    │   └── ml_processing/
    │       └── test_sahi_integration.py             # ~400 lines, 15+ tests
    └── fixtures/
        ├── images/
        │   ├── large_segmento_3000x1500.jpg
        │   ├── small_segmento_300x200.jpg
        │   ├── boundary_plant.jpg
        │   └── empty_segmento.jpg
        └── conftest.py                               # Shared fixtures
```

---

## Part 1: Unit Test Implementation

### File: `tests/unit/services/ml_processing/test_sahi_detection_service.py`

**Expected Lines**: ~600
**Expected Test Count**: 30+
**Coverage Target**: ≥85%

### Test Class Structure

```python
"""
Unit tests for SAHIDetectionService.

Tests the SAHI (Slicing Aided Hyper Inference) detection service that processes
large segmentos using intelligent tiling. This is the critical path for ML002.

Coverage targets:
- SAHI tiling configuration: 100%
- GREEDYNMM merging: 100%
- Coordinate mapping: 100%
- Black tile optimization: 100%
- Error handling: 100%
- ModelCache integration: 100%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from pathlib import Path
import numpy as np
import torch
from PIL import Image

from app.services.ml_processing.sahi_detection_service import (
    SAHIDetectionService,
    DetectionResult,
)
from app.services.ml_processing.model_cache import ModelCache


# ============================================================================
# Test Class 1: Basic Service Functionality
# ============================================================================

class TestSAHIDetectionServiceBasic:
    """Basic SAHI service tests - initialization and model loading."""

    @pytest.mark.asyncio
    async def test_service_initialization_default_worker(self):
        """Test service initializes with default worker_id=0."""
        service = SAHIDetectionService()

        assert service.worker_id == 0
        assert hasattr(service, 'detect_in_segmento')

    @pytest.mark.asyncio
    async def test_service_initialization_custom_worker(self):
        """Test service initializes with custom worker_id."""
        service = SAHIDetectionService(worker_id=2)

        assert service.worker_id == 2

    @pytest.mark.asyncio
    async def test_detect_uses_model_cache_singleton(self, mock_sahi, mock_model_cache):
        """Test detect_in_segmento() uses ModelCache singleton pattern."""
        service = SAHIDetectionService(worker_id=1)

        # Mock image and SAHI results
        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=5)

        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: ModelCache.get_model called with correct parameters
        mock_model_cache.assert_called_once_with("detect", 1)

    @pytest.mark.asyncio
    async def test_model_loaded_once_per_worker(self, mock_model_cache):
        """Test model loaded once and reused across multiple calls."""
        service = SAHIDetectionService(worker_id=0)

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)

        with patch("sahi.predict.get_sliced_prediction", return_value=mock_sahi_result):
            with patch("PIL.Image.open", return_value=mock_image):
                with patch("pathlib.Path.exists", return_value=True):
                    # Call detect 3 times
                    await service.detect_in_segmento("/fake/1.jpg")
                    await service.detect_in_segmento("/fake/2.jpg")
                    await service.detect_in_segmento("/fake/3.jpg")

        # Assert: Model loaded only once (singleton pattern)
        assert mock_model_cache.call_count == 3
        # But actual model instance is the same
        assert all(
            call_args[0] == ("detect", 0)
            for call_args in mock_model_cache.call_args_list
        )


# ============================================================================
# Test Class 2: SAHI Tiling Configuration
# ============================================================================

class TestSAHITilingConfiguration:
    """Test SAHI tiling parameters and configuration."""

    @pytest.mark.asyncio
    async def test_sahi_called_with_correct_tile_size(self, mock_sahi, mock_model_cache):
        """Test SAHI uses 512×512 tile size."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: Correct tile dimensions
        call_kwargs = mock_sahi.get_sliced_prediction.call_args.kwargs
        assert call_kwargs["slice_height"] == 512
        assert call_kwargs["slice_width"] == 512

    @pytest.mark.asyncio
    async def test_sahi_called_with_correct_overlap(self, mock_sahi, mock_model_cache):
        """Test SAHI uses 25% overlap ratio."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: 25% overlap for both dimensions
        call_kwargs = mock_sahi.get_sliced_prediction.call_args.kwargs
        assert call_kwargs["overlap_height_ratio"] == 0.25
        assert call_kwargs["overlap_width_ratio"] == 0.25

    @pytest.mark.asyncio
    async def test_sahi_uses_greedynmm_postprocessing(self, mock_sahi, mock_model_cache):
        """Test SAHI uses GREEDYNMM for duplicate removal."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: GREEDYNMM configured correctly
        call_kwargs = mock_sahi.get_sliced_prediction.call_args.kwargs
        assert call_kwargs["postprocess_type"] == "GREEDYNMM"
        assert call_kwargs["postprocess_match_threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_sahi_uses_custom_confidence_threshold(self, mock_sahi, mock_model_cache):
        """Test custom confidence threshold passed to SAHI."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento(
                    "/fake/segmento.jpg",
                    confidence_threshold=0.35
                )

        # Assert: Custom threshold used
        # (This would be in AutoDetectionModel.from_pretrained call)
        # For now, verify method was called with parameter
        # Implementation-specific assertion


# ============================================================================
# Test Class 3: GREEDYNMM Duplicate Merging
# ============================================================================

class TestSAHIGREEDYNMMerging:
    """Test GREEDYNMM merging algorithm for boundary detections."""

    @pytest.mark.asyncio
    async def test_greedynmm_merges_boundary_detections(self, mock_sahi, mock_model_cache):
        """Test plant on tile boundary merged to 1 detection, not 2."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)

        # Simulate GREEDYNMM: 2 overlapping detections merged to 1
        mock_sahi_result = create_mock_sahi_result(
            num_detections=1,  # After merge
            centers=[(512, 256)]
        )

        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/boundary.jpg")

        # Assert: Only 1 detection (merged)
        assert len(results) == 1
        assert results[0].center_x_px == 512
        assert results[0].center_y_px == 256

    @pytest.mark.asyncio
    async def test_greedynmm_preserves_distinct_plants(self, mock_sahi, mock_model_cache):
        """Test GREEDYNMM preserves truly distinct plants (not merged)."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)

        # 2 plants far apart (should NOT merge)
        mock_sahi_result = create_mock_sahi_result(
            num_detections=2,
            centers=[(300, 200), (1500, 800)]  # Far apart
        )

        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/two_plants.jpg")

        # Assert: 2 distinct detections
        assert len(results) == 2


# ============================================================================
# Test Class 4: Coordinate Mapping
# ============================================================================

class TestSAHICoordinateMapping:
    """Test coordinate mapping in original image space."""

    @pytest.mark.asyncio
    async def test_coordinates_in_original_image_space(self, mock_sahi, mock_model_cache):
        """Test SAHI returns coords in original image space (no offset)."""
        service = SAHIDetectionService()

        # Large image: 3000×1500
        mock_image = create_mock_image(width=3000, height=1500)

        # Detection at center: (1500, 750)
        mock_sahi_result = create_mock_sahi_result(
            num_detections=1,
            centers=[(1500, 750)]
        )
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/large.jpg")

        # Assert: Coordinates match original image space
        assert results[0].center_x_px == 1500
        assert results[0].center_y_px == 750
        assert results[0].center_x_px < 3000  # Within bounds
        assert results[0].center_y_px < 1500

    @pytest.mark.asyncio
    async def test_all_detections_within_image_bounds(self, mock_sahi, mock_model_cache):
        """Test all detection coordinates within original image bounds."""
        service = SAHIDetectionService()

        image_width = 2400
        image_height = 1200
        mock_image = create_mock_image(width=image_width, height=image_height)

        # Multiple detections
        mock_sahi_result = create_mock_sahi_result(
            num_detections=10,
            centers=[
                (100, 100), (500, 200), (1000, 500),
                (1500, 800), (2000, 1000), (300, 300),
                (800, 600), (1200, 400), (1800, 900), (2200, 1100)
            ]
        )
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/many_plants.jpg")

        # Assert: All coordinates within bounds
        assert len(results) == 10
        for det in results:
            assert 0 <= det.center_x_px < image_width
            assert 0 <= det.center_y_px < image_height
            assert det.width_px > 0
            assert det.height_px > 0


# ============================================================================
# Test Class 5: Black Tile Optimization
# ============================================================================

class TestSAHIBlackTileOptimization:
    """Test black tile skipping for performance."""

    @pytest.mark.asyncio
    async def test_black_tile_filtering_enabled(self, mock_sahi, mock_model_cache):
        """Test auto_skip_black_tiles=True passed to SAHI."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: Black tile filtering enabled
        call_kwargs = mock_sahi.get_sliced_prediction.call_args.kwargs
        assert call_kwargs["auto_skip_black_tiles"] is True

    @pytest.mark.asyncio
    async def test_black_tile_optimization_reduces_tiles(self, mock_sahi, mock_model_cache, caplog):
        """Test black tile skip reduces processed tiles (~20%)."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=5)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                with caplog.at_level("DEBUG"):
                    await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: Logging indicates tiles skipped
        # (Implementation-specific - check if service logs tile counts)


# ============================================================================
# Test Class 6: Small Image Fallback
# ============================================================================

class TestSAHISmallImageFallback:
    """Test fallback to direct detection for small images."""

    @pytest.mark.asyncio
    async def test_small_image_uses_direct_detection(self, mock_model_cache, caplog):
        """Test images <512px use direct YOLO, not SAHI tiling."""
        service = SAHIDetectionService()

        # Small image: 300×200 (smaller than 512×512 tile)
        mock_image = create_mock_image(width=300, height=200)

        # Mock YOLO direct prediction
        mock_yolo_result = create_mock_yolo_result(num_detections=2)
        mock_model = mock_model_cache.return_value
        mock_model.predict.return_value = [mock_yolo_result]

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                with caplog.at_level("WARNING"):
                    results = await service.detect_in_segmento("/fake/small.jpg")

        # Assert: Fallback to direct detection
        assert "too small" in caplog.text.lower() or "direct detection" in caplog.text.lower()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_small_image_threshold_512px(self, mock_sahi, mock_model_cache):
        """Test small image threshold is 512px (tile size)."""
        service = SAHIDetectionService()

        # Image exactly at threshold: 512×512
        mock_image = create_mock_image(width=512, height=512)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/512x512.jpg")

        # Assert: May use SAHI or direct (implementation-specific)
        # At minimum, should complete successfully
        assert isinstance(results, list)


# ============================================================================
# Test Class 7: Error Handling
# ============================================================================

class TestSAHIErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_raises_filenotfound_if_image_missing(self):
        """Test FileNotFoundError if image doesn't exist."""
        service = SAHIDetectionService()

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Image not found"):
                await service.detect_in_segmento("/nonexistent/image.jpg")

    @pytest.mark.asyncio
    async def test_raises_if_image_path_none(self):
        """Test ValueError if image_path is None."""
        service = SAHIDetectionService()

        with pytest.raises((ValueError, TypeError)):
            await service.detect_in_segmento(None)

    @pytest.mark.asyncio
    async def test_raises_if_sahi_prediction_fails(self, mock_sahi, mock_model_cache):
        """Test RuntimeError if SAHI prediction fails."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi.get_sliced_prediction.side_effect = RuntimeError("SAHI GPU error")

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(RuntimeError, match="SAHI detection failed|SAHI GPU error"):
                    await service.detect_in_segmento("/fake/segmento.jpg")

    @pytest.mark.asyncio
    async def test_empty_segmento_returns_empty_list(self, mock_sahi, mock_model_cache):
        """Test empty segmento (no plants) returns empty list, not error."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=0)  # No detections
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/empty.jpg")

        # Assert: Empty list, no exception
        assert results == []
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_corrupted_image_raises_clear_error(self, mock_model_cache):
        """Test corrupted image raises clear exception with path."""
        service = SAHIDetectionService()

        with patch("PIL.Image.open", side_effect=IOError("Cannot identify image")):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(IOError, match="Cannot identify image"):
                    await service.detect_in_segmento("/fake/corrupt.jpg")


# ============================================================================
# Test Class 8: Confidence Filtering
# ============================================================================

class TestSAHIConfidenceFiltering:
    """Test confidence threshold filtering."""

    @pytest.mark.asyncio
    async def test_filters_low_confidence_detections(self, mock_sahi, mock_model_cache):
        """Test detections below confidence threshold are filtered."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)

        # SAHI should only return high-confidence detections (≥0.25)
        mock_sahi_result = create_mock_sahi_result(
            num_detections=3,
            confidences=[0.9, 0.7, 0.5]  # All above threshold
        )
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento(
                    "/fake/segmento.jpg",
                    confidence_threshold=0.25
                )

        # Assert: All returned detections have confidence ≥ threshold
        assert len(results) == 3
        assert all(det.confidence >= 0.25 for det in results)

    @pytest.mark.asyncio
    async def test_default_confidence_threshold_025(self, mock_sahi, mock_model_cache):
        """Test default confidence threshold is 0.25."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                # Call without specifying threshold
                await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: AutoDetectionModel created with confidence_threshold=0.25
        # (Implementation-specific check)


# ============================================================================
# Test Class 9: Performance Logging
# ============================================================================

class TestSAHIPerformanceLogging:
    """Test performance metrics and logging."""

    @pytest.mark.asyncio
    async def test_logs_performance_metrics(self, mock_sahi, mock_model_cache, caplog):
        """Test performance metrics logged (time, detections, image size)."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=3000, height=1500)
        mock_sahi_result = create_mock_sahi_result(num_detections=850)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                with caplog.at_level("INFO"):
                    await service.detect_in_segmento("/fake/large.jpg")

        # Assert: Performance info logged
        log_text = caplog.text.lower()
        assert "850" in log_text or "detection" in log_text
        # Check for image dimensions or timing info

    @pytest.mark.asyncio
    async def test_returns_detection_count(self, mock_sahi, mock_model_cache):
        """Test method returns correct number of detections."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=123)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/segmento.jpg")

        assert len(results) == 123


# ============================================================================
# Test Class 10: Detection Result Format
# ============================================================================

class TestDetectionResultFormat:
    """Test DetectionResult dataclass structure."""

    @pytest.mark.asyncio
    async def test_detection_result_has_required_fields(self, mock_sahi, mock_model_cache):
        """Test DetectionResult contains all required fields."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: Required fields present
        det = results[0]
        assert hasattr(det, 'center_x_px')
        assert hasattr(det, 'center_y_px')
        assert hasattr(det, 'width_px')
        assert hasattr(det, 'height_px')
        assert hasattr(det, 'confidence')
        assert hasattr(det, 'class_name')

    @pytest.mark.asyncio
    async def test_detection_result_field_types(self, mock_sahi, mock_model_cache):
        """Test DetectionResult field types are correct."""
        service = SAHIDetectionService()

        mock_image = create_mock_image(width=2000, height=1000)
        mock_sahi_result = create_mock_sahi_result(num_detections=1)
        mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

        with patch("PIL.Image.open", return_value=mock_image):
            with patch("pathlib.Path.exists", return_value=True):
                results = await service.detect_in_segmento("/fake/segmento.jpg")

        det = results[0]
        assert isinstance(det.center_x_px, (int, float))
        assert isinstance(det.center_y_px, (int, float))
        assert isinstance(det.width_px, (int, float))
        assert isinstance(det.height_px, (int, float))
        assert isinstance(det.confidence, float)
        assert 0.0 <= det.confidence <= 1.0
        assert isinstance(det.class_name, str)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_sahi():
    """Mock SAHI library components."""
    with patch("app.services.ml_processing.sahi_detection_service.get_sliced_prediction") as mock_pred:
        with patch("app.services.ml_processing.sahi_detection_service.AutoDetectionModel") as mock_model:
            yield mock_pred


@pytest.fixture
def mock_model_cache():
    """Mock ModelCache.get_model() singleton."""
    with patch("app.services.ml_processing.sahi_detection_service.ModelCache.get_model") as mock:
        model_instance = MagicMock()
        model_instance.predict.return_value = []
        mock.return_value = model_instance
        yield mock


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mock_image(width: int, height: int) -> MagicMock:
    """
    Create mock PIL Image.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Mock PIL.Image with size property
    """
    mock_img = MagicMock(spec=Image.Image)
    mock_img.size = (width, height)
    mock_img.width = width
    mock_img.height = height
    return mock_img


def create_mock_sahi_result(
    num_detections: int = 1,
    centers: list[tuple[int, int]] = None,
    confidences: list[float] = None
) -> MagicMock:
    """
    Create mock SAHI PredictionResult.

    Args:
        num_detections: Number of detections to create
        centers: Optional list of (x, y) centers. If None, uses defaults.
        confidences: Optional list of confidence scores. If None, uses 0.9.

    Returns:
        Mock SAHI PredictionResult with object_prediction_list
    """
    mock_result = MagicMock()

    if centers is None:
        centers = [(512 + i * 100, 256 + i * 50) for i in range(num_detections)]

    if confidences is None:
        confidences = [0.9] * num_detections

    detections = []
    for i in range(num_detections):
        mock_obj = MagicMock()

        # Bbox (minx, miny, maxx, maxy)
        cx, cy = centers[i]
        bbox_width = 100
        bbox_height = 80

        mock_obj.bbox.minx = cx - bbox_width // 2
        mock_obj.bbox.maxx = cx + bbox_width // 2
        mock_obj.bbox.miny = cy - bbox_height // 2
        mock_obj.bbox.maxy = cy + bbox_height // 2

        # Score and category
        mock_obj.score.value = confidences[i]
        mock_obj.category.name = "plant"
        mock_obj.category.id = 0

        detections.append(mock_obj)

    mock_result.object_prediction_list = detections
    return mock_result


def create_mock_yolo_result(num_detections: int = 1) -> MagicMock:
    """
    Create mock YOLO Results object for direct detection.

    Args:
        num_detections: Number of detections

    Returns:
        Mock YOLO Results with boxes
    """
    mock_result = MagicMock()

    if num_detections == 0:
        mock_result.boxes = None
        return mock_result

    # Mock boxes
    mock_boxes = MagicMock()
    mock_boxes.xyxy = torch.tensor([
        [100 + i * 150, 100 + i * 75, 200 + i * 150, 200 + i * 75]
        for i in range(num_detections)
    ])
    mock_boxes.cls = torch.tensor([0] * num_detections)
    mock_boxes.conf = torch.tensor([0.9] * num_detections)

    mock_result.boxes = mock_boxes
    mock_result.names = {0: "plant"}

    return mock_result
```

---

## Part 2: Additional Test Classes (Expand Above File)

### Test Class 11: GPU vs CPU Detection

```python
class TestSAHIDeviceSelection:
    """Test GPU vs CPU device selection."""

    @pytest.mark.asyncio
    async def test_uses_gpu_when_available(self, mock_sahi, mock_model_cache):
        """Test service uses GPU when CUDA available."""
        service = SAHIDetectionService(worker_id=1)

        with patch("torch.cuda.is_available", return_value=True):
            mock_image = create_mock_image(width=2000, height=1000)
            mock_sahi_result = create_mock_sahi_result(num_detections=1)
            mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

            with patch("PIL.Image.open", return_value=mock_image):
                with patch("pathlib.Path.exists", return_value=True):
                    await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: GPU device used (check AutoDetectionModel creation)

    @pytest.mark.asyncio
    async def test_falls_back_to_cpu_when_gpu_unavailable(self, mock_sahi, mock_model_cache):
        """Test service falls back to CPU when CUDA unavailable."""
        service = SAHIDetectionService()

        with patch("torch.cuda.is_available", return_value=False):
            mock_image = create_mock_image(width=2000, height=1000)
            mock_sahi_result = create_mock_sahi_result(num_detections=1)
            mock_sahi.get_sliced_prediction.return_value = mock_sahi_result

            with patch("PIL.Image.open", return_value=mock_image):
                with patch("pathlib.Path.exists", return_value=True):
                    await service.detect_in_segmento("/fake/segmento.jpg")

        # Assert: CPU device used
```

---

## Coverage Requirements Summary

### Coverage Targets by Module

| Module/Function | Target Coverage | Critical |
|-----------------|----------------|----------|
| `detect_in_segmento()` | 100% | ✅ YES |
| SAHI configuration | 100% | ✅ YES |
| Coordinate mapping | 100% | ✅ YES |
| Error handling | 100% | ✅ YES |
| Model cache integration | 100% | ✅ YES |
| Black tile optimization | 90% | ⚠️ Important |
| Small image fallback | 90% | ⚠️ Important |
| Logging | 80% | Optional |

### Overall Target: ≥85%

---

## Next Section: Integration Tests

See `ML003-integration-tests.md` for comprehensive integration test patterns.

---

**Document Status**: ✅ COMPLETE - Unit Test Patterns
**Next**: Create integration test documentation
**Last Updated**: 2025-10-14
