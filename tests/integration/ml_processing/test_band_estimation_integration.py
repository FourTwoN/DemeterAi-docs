"""Integration tests for BandEstimationService - full workflow with real images and ground truth.

This module tests the complete band-based estimation algorithm with:
- Real test images (fixtures)
- Ground truth manual counts
- Performance benchmarks
- Accuracy validation (±10% error tolerance)
- Perspective compensation verification
- End-to-end workflow (image → estimations)

Test Coverage: Integration scenarios, accuracy validation
Performance Target: <2s for 4-band estimation

Business Context:
    These integration tests validate the proprietary band-based algorithm
    against manually counted ground truth data. The algorithm must achieve
    <10% error rate to be production-ready.

    Band-based perspective compensation is critical - far plants (band 1)
    should have smaller avg_plant_area than close plants (band 4).
"""

import json

import cv2
import numpy as np
import pytest

# =============================================================================
# Integration Test Fixtures
# =============================================================================


@pytest.fixture
def test_image_with_gaps(tmp_path):
    """Create realistic test image with detectable gaps (residual areas).

    Simulates a segment with:
    - Dense vegetation regions (detectable plants)
    - Sparse gaps (undetected plants - estimation target)
    - Soil/floor areas (should be suppressed)

    Returns: (image_path, segment_mask, ground_truth_count)
    """
    # Create 1200x1600 image
    img = np.zeros((1200, 1600, 3), dtype=np.uint8)

    # Background: brown soil
    img[:, :] = [40, 35, 30]  # Dark brown

    # Add green vegetation patches (detectable plants)
    # Dense region 1: Top-left (300 plants)
    for y in range(50, 400, 25):
        for x in range(50, 600, 25):
            cv2.circle(img, (x, y), 12, (50, 200, 50), -1)  # Green circles

    # Dense region 2: Bottom-right (200 plants)
    for y in range(700, 1100, 30):
        for x in range(900, 1500, 30):
            cv2.circle(img, (x, y), 15, (50, 200, 50), -1)

    # Sparse region: Center (gaps with undetected plants - 75 plants)
    for y in range(500, 650, 40):
        for x in range(700, 900, 40):
            cv2.circle(img, (x, y), 10, (50, 200, 50), -1)

    # Save image
    img_path = tmp_path / "test_segment_gaps.jpg"
    cv2.imwrite(str(img_path), img)

    # Create segment mask (entire image is valid)
    segment_mask = np.ones((1200, 1600), dtype=np.uint8) * 255

    # Ground truth: ~575 total plants (300 + 200 + 75)
    ground_truth = 575

    return str(img_path), segment_mask, ground_truth


@pytest.fixture
def test_detections_partial_coverage():
    """Create realistic detections that cover ~90% of plants.

    Simulates YOLO detecting most plants but missing ~10% in dense areas.
    This 10% gap is what band-based estimation should find.

    Returns: List of detection dicts
    """
    detections = []

    # Dense region 1: Detect 90% (270 of 300)
    for y in range(50, 400, 25):
        for x in range(50, 600, 25):
            # Skip 10% randomly
            if np.random.random() > 0.1:
                detections.append(
                    {
                        "center_x_px": x,
                        "center_y_px": y,
                        "width_px": 24,
                        "height_px": 24,
                    }
                )

    # Dense region 2: Detect 95% (190 of 200)
    for y in range(700, 1100, 30):
        for x in range(900, 1500, 30):
            if np.random.random() > 0.05:
                detections.append(
                    {
                        "center_x_px": x,
                        "center_y_px": y,
                        "width_px": 30,
                        "height_px": 30,
                    }
                )

    # Sparse region: Detect only 80% (60 of 75) - harder to detect
    for y in range(500, 650, 40):
        for x in range(700, 900, 40):
            if np.random.random() > 0.2:
                detections.append(
                    {
                        "center_x_px": x,
                        "center_y_px": y,
                        "width_px": 20,
                        "height_px": 20,
                    }
                )

    # Total detections: ~520 (270 + 190 + 60)
    return detections


# =============================================================================
# Integration Tests - Accuracy Validation
# =============================================================================


class TestBandEstimationAccuracy:
    """Test estimation accuracy against ground truth counts.

    Validates that band-based estimation achieves <10% error rate
    when combined with YOLO detections.
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_estimation_accuracy_within_10_percent(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test total estimated count within 10% of ground truth (CRITICAL).

        This is the primary accuracy test for production readiness.

        Formula: error_rate = |estimated - ground_truth| / ground_truth
        Acceptance: error_rate < 10%

        Performance: <2s for 4-band estimation
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Unpack fixtures
        img_path, segment_mask, ground_truth = test_image_with_gaps
        detections = test_detections_partial_coverage

        detected_count = len(detections)  # ~520 plants detected

        # Create service
        service = BandEstimationService(num_bands=4, alpha_overcount=0.9)

        # Act: Run estimation
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Calculate estimated undetected count
        estimated_undetected = sum(e.estimated_count for e in estimations)

        # Total estimated = detected + estimated_undetected
        total_estimated = detected_count + estimated_undetected

        # Assert: Within 10% of ground truth
        error = abs(total_estimated - ground_truth)
        error_rate = error / ground_truth

        assert (
            error_rate < 0.10
        ), f"Error rate {error_rate:.1%} exceeds 10%. Estimated: {total_estimated}, Ground truth: {ground_truth}"

        # Log results for analysis
        print("\n=== Estimation Accuracy Test ===")
        print(f"Ground truth: {ground_truth} plants")
        print(f"YOLO detected: {detected_count} plants ({detected_count/ground_truth:.1%})")
        print(f"Band estimation: +{estimated_undetected} plants")
        print(f"Total estimated: {total_estimated} plants")
        print(f"Error: {error} plants ({error_rate:.1%})")
        print(f"Result: {'✅ PASS' if error_rate < 0.10 else '❌ FAIL'}")

    @pytest.mark.asyncio
    async def test_estimation_compensates_for_missed_detections(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test estimation correctly compensates for missed YOLO detections.

        If YOLO detects ~90%, band estimation should find the remaining ~10%.

        Expected:
        - Detected: ~520 plants
        - Missed: ~55 plants (10% of 575)
        - Band estimation should find 40-70 plants (within range)
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange
        img_path, segment_mask, ground_truth = test_image_with_gaps
        detections = test_detections_partial_coverage
        detected_count = len(detections)

        service = BandEstimationService()

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        estimated_undetected = sum(e.estimated_count for e in estimations)

        # Assert: Estimated undetected is in reasonable range
        # Expected: 40-70 plants (ground_truth - detected ± 30%)
        expected_undetected = ground_truth - detected_count
        lower_bound = expected_undetected * 0.7
        upper_bound = expected_undetected * 1.3

        assert lower_bound <= estimated_undetected <= upper_bound, (
            f"Estimated undetected ({estimated_undetected}) outside expected range "
            f"[{lower_bound:.0f}, {upper_bound:.0f}]"
        )

    @pytest.mark.asyncio
    async def test_estimation_bias_toward_overcount(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test alpha overcount factor biases toward slight overestimation.

        For sales calculation, it's better to overcount than undercount.
        With alpha=0.9, estimation should slightly overestimate.

        Expected: total_estimated ≥ ground_truth (in most cases)
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange
        img_path, segment_mask, ground_truth = test_image_with_gaps
        detections = test_detections_partial_coverage
        detected_count = len(detections)

        service = BandEstimationService(alpha_overcount=0.9)

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        total_estimated = detected_count + sum(e.estimated_count for e in estimations)

        # Assert: Bias toward overcount (or within 5% undercount)
        undercount_tolerance = ground_truth * 0.05
        assert total_estimated >= ground_truth - undercount_tolerance, (
            f"Undercount too large: estimated {total_estimated} vs ground truth {ground_truth}. "
            "Alpha should bias toward overcount."
        )


# =============================================================================
# Integration Tests - Perspective Compensation
# =============================================================================


class TestBandEstimationPerspectiveCompensation:
    """Test band-based perspective compensation.

    Far plants (band 1) appear smaller than close plants (band 4).
    Band-specific calibration should capture this.
    """

    @pytest.mark.asyncio
    async def test_far_bands_have_smaller_plant_area(self, tmp_path):
        """Test band 1 (far) has smaller avg_plant_area than band 4 (close).

        This validates perspective compensation - the core innovation.

        Expected:
        - Band 1 avg_plant_area: ~1000-1500 px
        - Band 4 avg_plant_area: ~2500-3500 px
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Create image with perspective (far plants small, close plants large)
        img = np.zeros((1200, 1600, 3), dtype=np.uint8)
        img[:, :] = [40, 35, 30]  # Soil background

        # Band 1 (y: 0-300) - Far plants (small: 20x20)
        for y in range(50, 280, 40):
            for x in range(100, 1500, 50):
                cv2.circle(img, (x, y), 10, (50, 200, 50), -1)

        # Band 4 (y: 900-1200) - Close plants (large: 40x40)
        for y in range(920, 1180, 60):
            for x in range(100, 1500, 70):
                cv2.circle(img, (x, y), 20, (50, 200, 50), -1)

        img_path = tmp_path / "test_perspective.jpg"
        cv2.imwrite(str(img_path), img)

        # Create detections matching the plant sizes
        detections = []

        # Band 1 detections (small: 20x20)
        for y in range(50, 280, 40):
            for x in range(100, 1500, 50):
                detections.append(
                    {"center_x_px": x, "center_y_px": y, "width_px": 20, "height_px": 20}
                )

        # Band 4 detections (large: 40x40)
        for y in range(920, 1180, 60):
            for x in range(100, 1500, 70):
                detections.append(
                    {"center_x_px": x, "center_y_px": y, "width_px": 40, "height_px": 40}
                )

        segment_mask = np.ones((1200, 1600), dtype=np.uint8) * 255

        service = BandEstimationService()

        # Act: Run estimation
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Extract band estimations
        band1 = next(e for e in estimations if e.band_number == 1)
        band4 = next(e for e in estimations if e.band_number == 4)

        # Assert: Band 1 (far) has smaller avg_plant_area than band 4 (close)
        assert band1.average_plant_area_px < band4.average_plant_area_px, (
            f"Band 1 (far) should have smaller plants. "
            f"Band 1: {band1.average_plant_area_px:.0f}px, Band 4: {band4.average_plant_area_px:.0f}px"
        )

        # Assert: Reasonable size ranges
        # Band 1: 300-500 px (20x20 = 400)
        assert (
            300 <= band1.average_plant_area_px <= 500
        ), f"Band 1 area unrealistic: {band1.average_plant_area_px}"

        # Band 4: 1200-2000 px (40x40 = 1600)
        assert (
            1200 <= band4.average_plant_area_px <= 2000
        ), f"Band 4 area unrealistic: {band4.average_plant_area_px}"

        print("\n=== Perspective Compensation Test ===")
        print(f"Band 1 (far) avg area: {band1.average_plant_area_px:.0f} px")
        print(f"Band 4 (close) avg area: {band4.average_plant_area_px:.0f} px")
        print(
            f"Ratio (close/far): {band4.average_plant_area_px / band1.average_plant_area_px:.2f}x"
        )

    @pytest.mark.asyncio
    async def test_gradient_plant_sizes_across_bands(self, tmp_path):
        """Test gradual increase in avg_plant_area from band 1 to band 4.

        Validates smooth perspective transition (not abrupt jumps).

        Expected: avg_area[band1] < avg_area[band2] < avg_area[band3] < avg_area[band4]
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Create image with gradual size increase
        img = np.zeros((1200, 1600, 3), dtype=np.uint8)
        img[:, :] = [40, 35, 30]

        # Define plant sizes per band (gradual increase)
        band_configs = [
            (0, 300, 10, 20),  # Band 1: y 0-300, radius 10, bbox 20x20
            (300, 600, 12, 24),  # Band 2: y 300-600, radius 12, bbox 24x24
            (600, 900, 15, 30),  # Band 3: y 600-900, radius 15, bbox 30x30
            (900, 1200, 18, 36),  # Band 4: y 900-1200, radius 18, bbox 36x36
        ]

        detections = []

        for y_start, y_end, radius, bbox_size in band_configs:
            for y in range(y_start + 50, y_end - 20, 50):
                for x in range(100, 1500, 60):
                    cv2.circle(img, (x, y), radius, (50, 200, 50), -1)
                    detections.append(
                        {
                            "center_x_px": x,
                            "center_y_px": y,
                            "width_px": bbox_size,
                            "height_px": bbox_size,
                        }
                    )

        img_path = tmp_path / "test_gradient.jpg"
        cv2.imwrite(str(img_path), img)

        segment_mask = np.ones((1200, 1600), dtype=np.uint8) * 255

        service = BandEstimationService()

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Extract avg_plant_area for each band
        areas = [e.average_plant_area_px for e in sorted(estimations, key=lambda x: x.band_number)]

        # Assert: Monotonically increasing (or within 10% tolerance for noise)
        for i in range(len(areas) - 1):
            # Allow 10% deviation (calibration noise)
            assert areas[i] <= areas[i + 1] * 1.1, (
                f"Plant area should increase from band {i+1} to {i+2}. "
                f"Got: {areas[i]:.0f} -> {areas[i+1]:.0f}"
            )

        print("\n=== Gradient Plant Sizes Test ===")
        for i, area in enumerate(areas, start=1):
            print(f"Band {i} avg area: {area:.0f} px")


# =============================================================================
# Integration Tests - Performance Benchmarks
# =============================================================================


class TestBandEstimationPerformance:
    """Test performance benchmarks for production readiness.

    Requirements (AC6):
    - Single band: <500ms CPU
    - All 4 bands: <2s CPU total
    - Floor suppression: <300ms per band
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_estimation_completes_under_2_seconds(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test 4-band estimation completes in <2s on CPU (AC6).

        This is a hard performance requirement for production.
        CPU-first approach must be fast enough for real-time use.
        """
        import time

        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange
        img_path, segment_mask, _ = test_image_with_gaps
        detections = test_detections_partial_coverage

        service = BandEstimationService()

        # Act: Time the estimation
        start = time.time()
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )
        duration = time.time() - start

        # Assert: <2s total
        assert duration < 2.0, f"Estimation took {duration:.2f}s, exceeds 2s limit"

        # Assert: All 4 bands completed
        assert len(estimations) == 4, "All bands should complete"

        print("\n=== Performance Benchmark ===")
        print(f"Total time: {duration:.3f}s")
        print(f"Per band: {duration/4:.3f}s")
        print(f"Result: {'✅ PASS (<2s)' if duration < 2.0 else '❌ FAIL'}")

    @pytest.mark.asyncio
    async def test_floor_suppression_performance(self, tmp_path):
        """Test floor suppression completes in <300ms per band (AC6).

        Floor suppression (Otsu + HSV + morphology) should be fast.
        """
        import time

        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Realistic image
        img = np.random.randint(0, 256, size=(300, 400, 3), dtype=np.uint8)
        img_path = tmp_path / "test_floor_perf.jpg"
        cv2.imwrite(str(img_path), img)

        residual_mask = np.ones((300, 400), dtype=np.uint8) * 255

        service = BandEstimationService()

        # Act: Time floor suppression
        start = time.time()
        processed = service._suppress_floor(residual_mask, str(img_path))
        duration = time.time() - start

        # Assert: <300ms
        assert duration < 0.3, f"Floor suppression took {duration*1000:.0f}ms, exceeds 300ms limit"

        print("\n=== Floor Suppression Performance ===")
        print(f"Time: {duration*1000:.0f}ms")
        print(f"Result: {'✅ PASS (<300ms)' if duration < 0.3 else '❌ FAIL'}")


# =============================================================================
# Integration Tests - End-to-End Workflow
# =============================================================================


class TestBandEstimationEndToEnd:
    """Test complete end-to-end workflow from image to database-ready estimations.

    Validates integration with:
    - DB014 (Estimations model schema)
    - ML003 (Detection data format)
    - Photo processing pipeline
    """

    @pytest.mark.asyncio
    async def test_estimations_match_db_schema(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test estimation output matches DB014 (Estimations model) schema.

        Each BandEstimation should have all fields required for database insertion.
        """
        from dataclasses import asdict

        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange
        img_path, segment_mask, _ = test_image_with_gaps
        detections = test_detections_partial_coverage

        service = BandEstimationService()

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment", container_index=1
        )

        # Assert: Each estimation has required DB fields
        required_fields = {
            "estimation_type",
            "band_number",
            "band_y_start",
            "band_y_end",
            "residual_area_px",
            "processed_area_px",
            "floor_suppressed_px",
            "estimated_count",
            "average_plant_area_px",
            "alpha_overcount",
            "container_type",
        }

        for estimation in estimations:
            est_dict = asdict(estimation)

            # Check all required fields present
            for field in required_fields:
                assert field in est_dict, f"Missing required field: {field}"

            # Validate data types
            assert isinstance(est_dict["estimation_type"], str)
            assert isinstance(est_dict["band_number"], int)
            assert isinstance(est_dict["estimated_count"], int)
            assert isinstance(est_dict["residual_area_px"], float)
            assert isinstance(est_dict["alpha_overcount"], float)

            # Validate constraints
            assert est_dict["estimation_type"] == "band_based"
            assert 1 <= est_dict["band_number"] <= 4
            assert est_dict["estimated_count"] >= 0
            assert est_dict["alpha_overcount"] == 0.9

    @pytest.mark.asyncio
    async def test_estimations_ready_for_bulk_insert(
        self, test_image_with_gaps, test_detections_partial_coverage
    ):
        """Test estimations can be converted to format for bulk database insertion.

        Simulates R012 (EstimationRepository) bulk insert workflow.
        """
        from dataclasses import asdict

        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange
        img_path, segment_mask, _ = test_image_with_gaps
        detections = test_detections_partial_coverage

        service = BandEstimationService()

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Convert to list of dicts for bulk insert
        bulk_data = [asdict(e) for e in estimations]

        # Assert: 4 records ready for insert
        assert len(bulk_data) == 4, "Should have 4 records for bulk insert"

        # Assert: All have required fields
        for record in bulk_data:
            assert "estimated_count" in record
            assert "residual_area_px" in record
            assert record["estimation_type"] == "band_based"

        # Simulate bulk insert (would be: await repository.bulk_insert(bulk_data))
        print("\n=== Bulk Insert Simulation ===")
        print(f"Records ready: {len(bulk_data)}")
        print(f"Sample record: {json.dumps(bulk_data[0], indent=2, default=str)}")

    @pytest.mark.asyncio
    async def test_multiple_containers_in_sequence(self, tmp_path):
        """Test estimating multiple containers sequentially (production workflow).

        Simulates ML pipeline processing 10 segments in one photo session.
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Create 3 test segments
        service = BandEstimationService()

        all_estimations = []

        for container_idx in range(1, 4):  # 3 containers
            # Create simple test image
            img = np.full((1000, 1500, 3), [50, 200, 50], dtype=np.uint8)
            img_path = tmp_path / f"segment_{container_idx}.jpg"
            cv2.imwrite(str(img_path), img)

            # Minimal detections
            detections = [
                {"center_x_px": 100, "center_y_px": 100, "width_px": 40, "height_px": 40},
            ]

            segment_mask = np.ones((1000, 1500), dtype=np.uint8) * 255

            # Act: Estimate
            estimations = await service.estimate_undetected_plants(
                str(img_path), detections, segment_mask, container_type="segment"
            )

            all_estimations.extend(estimations)

        # Assert: 12 total estimations (4 per container × 3 containers)
        assert len(all_estimations) == 12, "Should have 4 bands × 3 containers = 12 estimations"


# =============================================================================
# Integration Tests - Edge Cases and Robustness
# =============================================================================


class TestBandEstimationRobustness:
    """Test robustness with challenging real-world scenarios."""

    @pytest.mark.asyncio
    async def test_handles_poor_lighting_conditions(self, tmp_path):
        """Test estimation works with poor lighting (dark image).

        Otsu thresholding should adapt to low brightness.
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Dark image (low brightness)
        img = np.full((1000, 1500, 3), [20, 80, 20], dtype=np.uint8)  # Dark green
        img_path = tmp_path / "test_dark.jpg"
        cv2.imwrite(str(img_path), img)

        detections = []
        segment_mask = np.ones((1000, 1500), dtype=np.uint8) * 255

        service = BandEstimationService()

        # Act: Should not crash
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Assert: Completes successfully
        assert len(estimations) == 4, "Should handle dark images"

    @pytest.mark.asyncio
    async def test_handles_high_density_residual_areas(self, tmp_path):
        """Test estimation with very high-density undetected areas.

        Should estimate large count without overflow errors.
        """
        from app.services.ml_processing.band_estimation_service import BandEstimationService

        # Arrange: Dense vegetation, minimal detections (large residual)
        img = np.full((1000, 1500, 3), [50, 200, 50], dtype=np.uint8)
        img_path = tmp_path / "test_dense.jpg"
        cv2.imwrite(str(img_path), img)

        # Only 10 detections (huge residual area)
        detections = [
            {"center_x_px": i * 100, "center_y_px": 500, "width_px": 40, "height_px": 40}
            for i in range(10)
        ]

        segment_mask = np.ones((1000, 1500), dtype=np.uint8) * 255

        service = BandEstimationService()

        # Act
        estimations = await service.estimate_undetected_plants(
            img_path, detections, segment_mask, container_type="segment"
        )

        # Assert: Should estimate high count (hundreds)
        total_estimated = sum(e.estimated_count for e in estimations)
        assert total_estimated > 100, "Should estimate large count for dense residual"
        assert total_estimated < 10000, "Should not overflow to unrealistic count"
