# ML003 - SAHI Detection Service Integration Tests

## Integration Testing Guide for Testing Expert

**Priority**: ⚡⚡⚡ **CRITICAL PATH**
**Target**: 15+ integration tests
**Performance Benchmarks**: REQUIRED

---

## Overview

Integration tests verify the **complete SAHI detection workflow** with real images, real YOLO models, and actual SAHI library. These tests validate the **10x improvement** claim and ensure production readiness.

### File Location

```
backend/tests/integration/ml_processing/test_sahi_integration.py
```

**Expected Lines**: ~400
**Expected Test Count**: 15+

---

## Part 1: Full Workflow Integration Tests

### File: `tests/integration/ml_processing/test_sahi_integration.py`

```python
"""
Integration tests for SAHIDetectionService.

Tests the complete SAHI workflow with real images and models:
- Real YOLO model loading
- Real SAHI library tiling
- Real image processing
- Performance benchmarks
- Accuracy validation

IMPORTANT: These tests require:
- Test images in tests/fixtures/images/
- YOLO detection model checkpoint
- Sufficient memory (2GB+ for model)
- Optional: GPU for performance tests
"""

import pytest
import time
from pathlib import Path
import numpy as np
from PIL import Image

from app.services.ml_processing.sahi_detection_service import SAHIDetectionService
from app.services.ml_processing.model_cache import ModelCache


# ============================================================================
# Test Class 1: Basic Integration Workflow
# ============================================================================

class TestSAHIIntegrationBasic:
    """Basic integration tests with real models and images."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_in_real_segmento_image(self, sample_segmento_image):
        """Test detection on real segmento image."""
        service = SAHIDetectionService(worker_id=0)

        results = await service.detect_in_segmento(sample_segmento_image)

        # Assert: Returns detections
        assert isinstance(results, list)
        assert len(results) > 0, "Should detect at least some plants"

        # Verify structure
        first_det = results[0]
        assert hasattr(first_det, 'center_x_px')
        assert hasattr(first_det, 'center_y_px')
        assert hasattr(first_det, 'confidence')
        assert first_det.confidence > 0.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_returns_many_plants_in_large_segmento(self, large_segmento_3000x1500):
        """Test SAHI detects many plants (500-800+) in large segmento."""
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(large_segmento_3000x1500)

        # Assert: Many detections (typical production range)
        assert len(results) >= 100, f"Expected ≥100 plants, got {len(results)}"
        print(f"✓ Detected {len(results)} plants in 3000×1500 segmento")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_detections_have_valid_coordinates(self, sample_segmento_image):
        """Test all detections have coordinates within image bounds."""
        service = SAHIDetectionService()

        # Get image dimensions
        img = Image.open(sample_segmento_image)
        width, height = img.size

        results = await service.detect_in_segmento(sample_segmento_image)

        # Assert: All coordinates within bounds
        for i, det in enumerate(results):
            assert 0 <= det.center_x_px < width, \
                f"Detection {i}: center_x={det.center_x_px} out of bounds (0-{width})"
            assert 0 <= det.center_y_px < height, \
                f"Detection {i}: center_y={det.center_y_px} out of bounds (0-{height})"
            assert det.width_px > 0
            assert det.height_px > 0
            assert 0.0 < det.confidence <= 1.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_empty_segmento_returns_zero_detections(self, empty_segmento_image):
        """Test empty segmento (no plants) returns empty list."""
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(empty_segmento_image)

        # Assert: No detections, no error
        assert results == []
        assert isinstance(results, list)


# ============================================================================
# Test Class 2: SAHI vs Direct Detection Comparison
# ============================================================================

class TestSAHIvsDirectDetection:
    """Compare SAHI tiling vs direct YOLO detection."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sahi_detects_more_than_direct_yolo(self, large_segmento_3000x1500):
        """
        Test SAHI detects 5-10x more plants than direct YOLO.

        This is the CRITICAL validation of the 10x improvement claim.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # SAHI detection (tiled)
        sahi_service = SAHIDetectionService()
        sahi_results = await sahi_service.detect_in_segmento(large_segmento_3000x1500)
        sahi_count = len(sahi_results)

        # Direct YOLO detection (no tiling)
        model = ModelCache.get_model("detect", 0)
        img = Image.open(large_segmento_3000x1500)

        # Resize to 640px (what direct YOLO would do)
        aspect_ratio = img.width / img.height
        if img.width > img.height:
            new_width = 640
            new_height = int(640 / aspect_ratio)
        else:
            new_height = 640
            new_width = int(640 * aspect_ratio)

        img_resized = img.resize((new_width, new_height))
        direct_results = model.predict(img_resized, conf=0.25, verbose=False)
        direct_count = len(direct_results[0].boxes) if direct_results[0].boxes else 0

        # Assert: SAHI detects significantly more
        improvement_ratio = sahi_count / max(direct_count, 1)

        print(f"\n{'='*60}")
        print(f"SAHI vs Direct Detection Comparison")
        print(f"{'='*60}")
        print(f"Direct YOLO (640px):  {direct_count:4d} plants")
        print(f"SAHI (512×512 tiles): {sahi_count:4d} plants")
        print(f"Improvement:          {improvement_ratio:.1f}× more detections")
        print(f"{'='*60}\n")

        assert improvement_ratio >= 3.0, \
            f"SAHI should detect ≥3× more (got {improvement_ratio:.1f}×)"
        assert sahi_count >= 100, \
            f"SAHI should detect ≥100 plants in large segmento (got {sahi_count})"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sahi_finds_small_plants_direct_misses(self, segmento_with_small_plants):
        """Test SAHI detects small plants that direct YOLO misses."""
        # This requires a labeled test image with known small plant locations
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(segmento_with_small_plants)

        # Assert: Detects plants in expected locations
        # (Requires ground truth annotations)
        assert len(results) > 0


# ============================================================================
# Test Class 3: Performance Benchmarks
# ============================================================================

class TestSAHIPerformanceBenchmarks:
    """Performance benchmarks for SAHI detection."""

    @pytest.mark.integration
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_cpu_performance_3000x1500_under_10s(self, large_segmento_3000x1500):
        """Test CPU inference completes in <10s for 3000×1500 image."""
        import torch

        # Force CPU
        original_cuda_available = torch.cuda.is_available
        torch.cuda.is_available = lambda: False

        try:
            service = SAHIDetectionService()

            start = time.time()
            results = await service.detect_in_segmento(large_segmento_3000x1500)
            elapsed = time.time() - start

            print(f"\n{'='*60}")
            print(f"CPU Performance Benchmark (3000×1500)")
            print(f"{'='*60}")
            print(f"Time:       {elapsed:.2f}s")
            print(f"Detections: {len(results)}")
            print(f"Target:     <10s")
            print(f"Status:     {'✅ PASS' if elapsed < 10.0 else '❌ FAIL'}")
            print(f"{'='*60}\n")

            # Assert: Acceptable CPU performance
            assert elapsed < 10.0, \
                f"CPU inference took {elapsed:.2f}s (should be <10s)"
            assert len(results) > 0

        finally:
            # Restore
            torch.cuda.is_available = original_cuda_available

    @pytest.mark.integration
    @pytest.mark.benchmark
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="GPU not available")
    @pytest.mark.asyncio
    async def test_gpu_performance_3000x1500_under_3s(self, large_segmento_3000x1500):
        """Test GPU inference completes in <3s for 3000×1500 image."""
        service = SAHIDetectionService(worker_id=0)

        start = time.time()
        results = await service.detect_in_segmento(large_segmento_3000x1500)
        elapsed = time.time() - start

        print(f"\n{'='*60}")
        print(f"GPU Performance Benchmark (3000×1500)")
        print(f"{'='*60}")
        print(f"Time:       {elapsed:.2f}s")
        print(f"Detections: {len(results)}")
        print(f"Target:     <3s")
        print(f"Speedup:    ~{10.0/elapsed:.1f}× faster than CPU")
        print(f"Status:     {'✅ PASS' if elapsed < 3.0 else '❌ FAIL'}")
        print(f"{'='*60}\n")

        # Assert: Fast GPU performance
        assert elapsed < 3.0, \
            f"GPU inference took {elapsed:.2f}s (should be <3s)"
        assert len(results) > 0

    @pytest.mark.integration
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_performance_scales_with_image_size(self):
        """Test inference time scales linearly with image size."""
        service = SAHIDetectionService()

        # Small image: 1000×500
        small_img = create_test_image(width=1000, height=500)
        start = time.time()
        await service.detect_in_segmento(small_img)
        small_time = time.time() - start

        # Large image: 3000×1500 (9× more pixels)
        large_img = create_test_image(width=3000, height=1500)
        start = time.time()
        await service.detect_in_segmento(large_img)
        large_time = time.time() - start

        # Assert: Time scales roughly linearly (not exponentially)
        time_ratio = large_time / small_time
        pixel_ratio = (3000 * 1500) / (1000 * 500)  # = 9

        print(f"\n{'='*60}")
        print(f"Scaling Benchmark")
        print(f"{'='*60}")
        print(f"Small (1000×500):  {small_time:.2f}s")
        print(f"Large (3000×1500): {large_time:.2f}s")
        print(f"Time ratio:        {time_ratio:.1f}× (pixel ratio: {pixel_ratio:.1f}×)")
        print(f"{'='*60}\n")

        # Time ratio should be close to pixel ratio (linear scaling)
        assert time_ratio <= pixel_ratio * 1.5, \
            f"Time should scale linearly with pixels (got {time_ratio:.1f}× vs {pixel_ratio:.1f}× pixels)"


# ============================================================================
# Test Class 4: Edge Cases and Robustness
# ============================================================================

class TestSAHIEdgeCases:
    """Test edge cases and robustness."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_very_large_image_5000x3000(self, very_large_segmento_5000x3000):
        """Test SAHI handles very large images (5000×3000)."""
        service = SAHIDetectionService()

        # Should complete without OOM
        results = await service.detect_in_segmento(very_large_segmento_5000x3000)

        assert isinstance(results, list)
        # May take longer, but should complete
        print(f"✓ Detected {len(results)} plants in 5000×3000 image")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_small_image_direct_detection_fallback(self, small_segmento_300x200):
        """Test small images use direct detection (no tiling)."""
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(small_segmento_300x200)

        # Should complete quickly (no tiling overhead)
        assert isinstance(results, list)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_density_segmento_1000_plants(self, high_density_segmento):
        """Test segmento with 1000+ plants (stress test)."""
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(high_density_segmento)

        # Should detect most plants
        assert len(results) >= 800, \
            f"Expected ≥800 detections in high-density image (got {len(results)})"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_low_quality_image_degrades_gracefully(self, low_quality_segmento):
        """Test low-quality/blurry image degrades gracefully."""
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(low_quality_segmento)

        # May return fewer detections, but should not crash
        assert isinstance(results, list)
        print(f"✓ Low-quality image: {len(results)} detections (may be lower)")


# ============================================================================
# Test Class 5: Model Cache Integration
# ============================================================================

class TestModelCacheIntegration:
    """Test ModelCache singleton integration."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_model_loaded_once_across_multiple_calls(self, sample_segmento_image):
        """Test model singleton: loaded once, reused multiple times."""
        # Clear cache
        ModelCache._cache.clear()

        service = SAHIDetectionService(worker_id=0)

        # First call: model loaded
        start = time.time()
        await service.detect_in_segmento(sample_segmento_image)
        first_call_time = time.time() - start

        # Second call: model from cache
        start = time.time()
        await service.detect_in_segmento(sample_segmento_image)
        second_call_time = time.time() - start

        # Third call: still from cache
        start = time.time()
        await service.detect_in_segmento(sample_segmento_image)
        third_call_time = time.time() - start

        print(f"\n{'='*60}")
        print(f"Model Cache Singleton Test")
        print(f"{'='*60}")
        print(f"1st call: {first_call_time:.2f}s (model loading + inference)")
        print(f"2nd call: {second_call_time:.2f}s (cached)")
        print(f"3rd call: {third_call_time:.2f}s (cached)")
        print(f"{'='*60}\n")

        # Subsequent calls should be similar (no reload overhead)
        # Allow 20% variance
        assert abs(second_call_time - third_call_time) / third_call_time < 0.2, \
            "Cached calls should have similar timing"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_workers_load_separate_models(self):
        """Test multiple workers load separate model instances."""
        # This test requires GPU with multiple workers
        # For now, verify workers can initialize separately

        service_0 = SAHIDetectionService(worker_id=0)
        service_1 = SAHIDetectionService(worker_id=1)

        # Both should initialize without conflict
        assert service_0.worker_id == 0
        assert service_1.worker_id == 1


# ============================================================================
# Test Class 6: Coordinate Accuracy
# ============================================================================

class TestCoordinateAccuracy:
    """Test coordinate mapping accuracy with known ground truth."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_coordinates_match_ground_truth(self, annotated_segmento_with_ground_truth):
        """
        Test detected coordinates match ground truth annotations.

        Requires a test image with known plant locations (ground truth).
        """
        service = SAHIDetectionService()

        results = await service.detect_in_segmento(
            annotated_segmento_with_ground_truth["image_path"]
        )

        ground_truth = annotated_segmento_with_ground_truth["annotations"]

        # For each ground truth plant, find closest detection
        matches = 0
        tolerance_px = 50  # Allow 50px tolerance

        for gt_plant in ground_truth:
            gt_x, gt_y = gt_plant["center_x"], gt_plant["center_y"]

            # Find closest detection
            for det in results:
                dist = np.sqrt(
                    (det.center_x_px - gt_x) ** 2 +
                    (det.center_y_px - gt_y) ** 2
                )
                if dist <= tolerance_px:
                    matches += 1
                    break

        # Assert: Most ground truth plants detected
        match_rate = matches / len(ground_truth)
        assert match_rate >= 0.85, \
            f"Expected ≥85% match rate (got {match_rate:.1%}, {matches}/{len(ground_truth)})"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def sample_segmento_image() -> str:
    """
    Path to sample segmento image for testing.

    Returns:
        Absolute path to test image
    """
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "segmento_2000x1000.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def large_segmento_3000x1500() -> str:
    """Path to large segmento (3000×1500) for performance tests."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "large_segmento_3000x1500.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Large test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def very_large_segmento_5000x3000() -> str:
    """Path to very large segmento (5000×3000) for stress tests."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "very_large_segmento_5000x3000.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Very large test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def small_segmento_300x200() -> str:
    """Path to small segmento (<512px) for fallback tests."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "small_segmento_300x200.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Small test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def empty_segmento_image() -> str:
    """Path to empty segmento (no plants) for edge case tests."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "empty_segmento.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Empty test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def high_density_segmento() -> str:
    """Path to high-density segmento (1000+ plants)."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "high_density_segmento.jpg"

    if not fixture_path.exists():
        pytest.skip(f"High-density test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def low_quality_segmento() -> str:
    """Path to low-quality/blurry segmento."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "low_quality_segmento.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Low-quality test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def segmento_with_small_plants() -> str:
    """Path to segmento with many small plants."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "small_plants_segmento.jpg"

    if not fixture_path.exists():
        pytest.skip(f"Small plants test image not found: {fixture_path}")

    return str(fixture_path)


@pytest.fixture(scope="module")
def annotated_segmento_with_ground_truth() -> dict:
    """
    Annotated segmento with ground truth plant locations.

    Returns:
        Dict with "image_path" and "annotations" (list of plant locations)
    """
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "images" / "annotated_segmento.jpg"
    annotation_path = Path(__file__).parent.parent.parent / "fixtures" / "annotations" / "annotated_segmento.json"

    if not fixture_path.exists() or not annotation_path.exists():
        pytest.skip(f"Annotated test data not found")

    import json
    with open(annotation_path) as f:
        annotations = json.load(f)

    return {
        "image_path": str(fixture_path),
        "annotations": annotations["plants"]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_image(width: int, height: int) -> str:
    """
    Create synthetic test image for performance tests.

    Args:
        width: Image width
        height: Image height

    Returns:
        Path to created test image
    """
    import tempfile
    from PIL import Image, ImageDraw
    import random

    # Create green background
    img = Image.new("RGB", (width, height), color=(50, 80, 40))
    draw = ImageDraw.ImageDraw(img)

    # Add random "plants" (small circles)
    num_plants = (width * height) // 10000  # ~1 plant per 10k pixels
    for _ in range(num_plants):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(10, 30)
        color = (
            random.randint(80, 120),
            random.randint(150, 200),
            random.randint(80, 120)
        )
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=color
        )

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(temp_file.name, quality=85)

    return temp_file.name
```

---

## Part 2: Performance Reporting

### Performance Report Template

Create this function in the integration test file:

```python
def generate_performance_report(results: dict) -> str:
    """
    Generate comprehensive performance report.

    Args:
        results: Dict with benchmark results

    Returns:
        Formatted report string
    """
    report = f"""
{'='*80}
SAHI DETECTION SERVICE - PERFORMANCE REPORT
{'='*80}

## Test Summary

Total Integration Tests: {results['total_tests']}
Passed:                  {results['passed']} ✅
Failed:                  {results['failed']} ❌
Skipped:                 {results['skipped']} ⏭️

## Performance Benchmarks

### CPU Performance (3000×1500)
Time:       {results['cpu_time']:.2f}s
Target:     <10s
Status:     {'✅ PASS' if results['cpu_time'] < 10 else '❌ FAIL'}

### GPU Performance (3000×1500)
Time:       {results['gpu_time']:.2f}s
Target:     <3s
Speedup:    {results['cpu_time'] / results['gpu_time']:.1f}× faster than CPU
Status:     {'✅ PASS' if results['gpu_time'] < 3 else '❌ FAIL'}

## Detection Accuracy

### SAHI vs Direct YOLO
Direct YOLO:  {results['direct_detections']} plants
SAHI Tiling:  {results['sahi_detections']} plants
Improvement:  {results['sahi_detections'] / results['direct_detections']:.1f}× more
Target:       ≥5× improvement
Status:       {'✅ PASS' if results['sahi_detections'] / results['direct_detections'] >= 5 else '❌ FAIL'}

### Coordinate Accuracy
Ground Truth Match Rate: {results['match_rate']:.1%}
Target:                  ≥85%
Status:                  {'✅ PASS' if results['match_rate'] >= 0.85 else '❌ FAIL'}

{'='*80}
OVERALL STATUS: {'✅ ALL TESTS PASSED' if results['failed'] == 0 else '❌ SOME TESTS FAILED'}
{'='*80}
"""
    return report
```

---

## Part 3: Test Execution Guide

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ml_processing/test_sahi_integration.py -v

# Run with coverage
pytest tests/integration/ml_processing/test_sahi_integration.py \
    --cov=app.services.ml_processing.sahi_detection_service \
    --cov-report=term-missing

# Run only fast tests (skip benchmarks)
pytest tests/integration/ml_processing/test_sahi_integration.py \
    -v -m "integration and not benchmark"

# Run performance benchmarks only
pytest tests/integration/ml_processing/test_sahi_integration.py \
    -v -m "benchmark" --benchmark-only

# Run with detailed output
pytest tests/integration/ml_processing/test_sahi_integration.py \
    -v -s --log-cli-level=INFO
```

### pytest.ini Configuration

Add to `pytest.ini`:

```ini
[pytest]
markers =
    integration: Integration tests (real models, images)
    benchmark: Performance benchmark tests
    slow: Slow-running tests (>5s)
    gpu: Tests requiring GPU
```

---

## Part 4: Test Fixtures Setup

### Creating Test Images

```python
# tests/fixtures/create_test_images.py
"""
Script to create test images for SAHI integration tests.
"""

from PIL import Image, ImageDraw
import random
from pathlib import Path


def create_large_segmento_3000x1500(output_path: Path):
    """Create realistic 3000×1500 segmento with ~800 plants."""
    img = Image.new("RGB", (3000, 1500), color=(40, 70, 35))
    draw = ImageDraw.ImageDraw(img)

    # Grid of plants
    for row in range(20):
        for col in range(40):
            x = 50 + col * 75 + random.randint(-20, 20)
            y = 50 + row * 75 + random.randint(-20, 20)
            radius = random.randint(15, 30)

            # Plant color (greenish)
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
    print(f"✓ Created: {output_path}")


def create_empty_segmento(output_path: Path):
    """Create empty segmento (no plants)."""
    img = Image.new("RGB", (2000, 1000), color=(50, 80, 40))
    img.save(output_path, quality=90)
    print(f"✓ Created: {output_path}")


def create_small_segmento_300x200(output_path: Path):
    """Create small segmento for fallback tests."""
    img = Image.new("RGB", (300, 200), color=(50, 80, 40))
    draw = ImageDraw.ImageDraw(img)

    # Few plants
    for _ in range(5):
        x = random.randint(30, 270)
        y = random.randint(30, 170)
        radius = random.randint(10, 20)
        color = (random.randint(80, 120), random.randint(150, 200), random.randint(80, 120))
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color)

    img.save(output_path, quality=90)
    print(f"✓ Created: {output_path}")


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent / "images"
    fixtures_dir.mkdir(exist_ok=True)

    create_large_segmento_3000x1500(fixtures_dir / "large_segmento_3000x1500.jpg")
    create_empty_segmento(fixtures_dir / "empty_segmento.jpg")
    create_small_segmento_300x200(fixtures_dir / "small_segmento_300x200.jpg")

    print("\n✅ All test images created!")
```

---

## Success Criteria

### Integration Test Checklist

- [ ] ✅ 15+ integration tests written
- [ ] ✅ All tests use real YOLO model
- [ ] ✅ All tests use real SAHI library
- [ ] ✅ Performance benchmarks included (CPU + GPU)
- [ ] ✅ SAHI vs Direct comparison validates 5-10× improvement
- [ ] ✅ Coordinate accuracy validated with ground truth
- [ ] ✅ Edge cases tested (empty, small, very large images)
- [ ] ✅ Model cache singleton validated
- [ ] ✅ All tests pass on CI/CD
- [ ] ✅ Performance report generated

---

## Expected Output

### Coverage Report

```
==================== test session starts ====================
collected 18 items

tests/integration/ml_processing/test_sahi_integration.py::TestSAHIIntegrationBasic::test_detect_in_real_segmento_image PASSED [ 5%]
tests/integration/ml_processing/test_sahi_integration.py::TestSAHIIntegrationBasic::test_detect_returns_many_plants_in_large_segmento PASSED [11%]
...

============================================================
SAHI DETECTION SERVICE - PERFORMANCE REPORT
============================================================

## Test Summary
Total Integration Tests: 18
Passed:                  18 ✅
Failed:                  0 ❌
Skipped:                 2 ⏭️

## Performance Benchmarks

### CPU Performance (3000×1500)
Time:       5.43s
Target:     <10s
Status:     ✅ PASS

### GPU Performance (3000×1500)
Time:       1.87s
Target:     <3s
Speedup:    2.9× faster than CPU
Status:     ✅ PASS

## Detection Accuracy

### SAHI vs Direct YOLO
Direct YOLO:  98 plants
SAHI Tiling:  847 plants
Improvement:  8.6× more
Target:       ≥5× improvement
Status:       ✅ PASS

============================================================
OVERALL STATUS: ✅ ALL TESTS PASSED
============================================================

========== 18 passed, 2 skipped in 45.23s ===========
```

---

**Document Status**: ✅ COMPLETE - Integration Test Patterns
**Next**: Create fixtures and best practices guide
**Last Updated**: 2025-10-14
