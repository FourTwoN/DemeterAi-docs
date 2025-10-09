# [ML005] Band-Based Estimation Service

## Metadata
- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `critical` ⚡⚡ **CRITICAL PATH**
- **Complexity**: L (8 story points)
- **Area**: `services/ml_processing`
- **Assignee**: TBD (assign to senior ML engineer)
- **Dependencies**:
  - Blocks: [ML009-pipeline-coordinator, R012-estimation-repository]
  - Blocked by**: [ML003-sahi-detection, DB014-estimations-model]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md
- **ML Pipeline Flow**: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md
- **Context**: ../../context/past_chats_summary.md (Band-based estimation innovation)
- **Database**: ../../database/database.mmd (estimations table)

## Description

Implement the **proprietary band-based estimation algorithm** that estimates undetected plants in residual areas. This is DemeterAI's competitive advantage - handles perspective distortion that competitors miss.

**What**: Service that:
- Divides image into 4 horizontal bands (handles perspective)
- For each band: analyzes residual area not covered by detections
- Applies floor/soil suppression (HSV + Otsu thresholding)
- Auto-calibrates plant size from band-specific detections
- Estimates undetected plant count using calibrated area

**Why**:
- **Completeness**: YOLO misses 5-10% of plants in dense areas
- **Perspective handling**: Far plants appear smaller (bands compensate)
- **Innovation**: Proprietary algorithm competitors don't have
- **Accuracy**: +5-10% total count improvement

**Context**: This is the **secret sauce** - the algorithm that makes DemeterAI more accurate than competition. Band-based approach is novel (see past_chats).

## Acceptance Criteria

- [ ] **AC1**: Service class created in `app/services/ml_processing/estimation_service.py`:
  ```python
  class BandEstimationService:
      def __init__(self):
          self.num_bands = 4  # Configurable, but 4 is optimal
          self.alpha_overcount = 0.9  # Bias toward overestimation

      async def estimate_undetected_plants(
          self,
          image_path: str,
          detections: list[dict],
          segment_mask: np.ndarray,
          container_type: str = 'segmento'
      ) -> list[dict]:
          """
          Estimate plants in residual areas using band-based algorithm.

          Returns list of Estimation dicts (one per band).
          """
          # 1. Create union detection mask
          detection_mask = self._create_detection_mask(detections, image_shape)

          # 2. Calculate residual mask
          residual_mask = segment_mask & ~detection_mask

          # 3. Divide into 4 bands
          bands = self._divide_into_bands(residual_mask, num_bands=4)

          # 4. Process each band
          estimations = []
          for band_num, band_mask in enumerate(bands, start=1):
              # Apply floor suppression
              processed_mask = self._suppress_floor(band_mask, image_path)

              # Auto-calibrate plant size from detections in this band
              avg_plant_area = self._calibrate_plant_size(
                  detections,
                  band_num,
                  image_height
              )

              # Estimate count
              processed_area = np.sum(processed_mask > 0)
              estimated_count = int(
                  np.ceil(processed_area / (avg_plant_area * self.alpha_overcount))
              )

              estimations.append({
                  'estimation_type': 'band_based',
                  'band_number': band_num,
                  'band_y_start': (band_num - 1) * (image_height // 4),
                  'band_y_end': band_num * (image_height // 4),
                  'residual_area_px': float(np.sum(band_mask > 0)),
                  'processed_area_px': float(processed_area),
                  'floor_suppressed_px': float(np.sum(band_mask > 0) - processed_area),
                  'estimated_count': estimated_count,
                  'average_plant_area_px': float(avg_plant_area),
                  'alpha_overcount': self.alpha_overcount,
                  'container_type': container_type
              })

          return estimations
  ```

- [ ] **AC2**: Floor suppression algorithm implemented:
  ```python
  def _suppress_floor(self, residual_mask: np.ndarray, image_path: str) -> np.ndarray:
      """Remove soil/floor using HSV + Otsu filtering"""
      # Load image region
      img = cv2.imread(image_path)
      img_masked = cv2.bitwise_and(img, img, mask=residual_mask)

      # Convert to LAB for brightness-based Otsu
      lab = cv2.cvtColor(img_masked, cv2.COLOR_BGR2LAB)
      l_channel = lab[:, :, 0]

      # Otsu thresholding on brightness
      _, otsu_mask = cv2.threshold(
          l_channel, 0, 255,
          cv2.THRESH_BINARY + cv2.THRESH_OTSU
      )

      # HSV color filtering (remove brown/dark soil)
      hsv = cv2.cvtColor(img_masked, cv2.COLOR_BGR2HSV)
      soil_mask = cv2.inRange(
          hsv,
          (0, 0, 0),      # Lower bound (dark soil)
          (30, 40, 40)    # Upper bound
      )

      # Combine: keep vegetation (NOT soil)
      vegetation_mask = otsu_mask & ~soil_mask

      # Morphological opening (remove noise)
      kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
      vegetation_mask = cv2.morphologyEx(
          vegetation_mask,
          cv2.MORPH_OPEN,
          kernel
      )

      return vegetation_mask & residual_mask
  ```

- [ ] **AC3**: Auto-calibration from detections:
  ```python
  def _calibrate_plant_size(
      self,
      detections: list[dict],
      band_number: int,
      image_height: int
  ) -> float:
      """Auto-calibrate average plant area from detections in this band"""
      band_y_start = (band_number - 1) * (image_height // 4)
      band_y_end = band_number * (image_height // 4)

      # Filter detections in this band
      band_detections = [
          d for d in detections
          if band_y_start <= d['center_y_px'] < band_y_end
      ]

      if len(band_detections) < 10:  # Insufficient samples
          # Fallback to default pot size (5cm × 5cm = ~2500px at typical resolution)
          return 2500.0

      # Calculate average plant area
      areas = [d['width_px'] * d['height_px'] for d in band_detections]

      # Remove outliers (IQR method)
      q1, q3 = np.percentile(areas, [25, 75])
      iqr = q3 - q1
      lower_bound = q1 - 1.5 * iqr
      upper_bound = q3 + 1.5 * iqr
      filtered_areas = [a for a in areas if lower_bound <= a <= upper_bound]

      return np.mean(filtered_areas) if filtered_areas else 2500.0
  ```

- [ ] **AC4**: 4 bands division:
  ```python
  def _divide_into_bands(
      self,
      mask: np.ndarray,
      num_bands: int = 4
  ) -> list[np.ndarray]:
      """Divide mask into N horizontal bands"""
      height = mask.shape[0]
      band_height = height // num_bands

      bands = []
      for i in range(num_bands):
          y_start = i * band_height
          y_end = (i + 1) * band_height if i < num_bands - 1 else height

          band_mask = np.zeros_like(mask)
          band_mask[y_start:y_end, :] = mask[y_start:y_end, :]
          bands.append(band_mask)

      return bands
  ```

- [ ] **AC5**: Alpha overcount factor = 0.9 (bias toward overestimation):
  ```python
  # Formula: estimated_count = ceil(area / (avg_plant_area * 0.9))
  # Alpha < 1.0 = overcount (conservative for sales)
  # Alpha > 1.0 = undercount (aggressive)
  # 0.9 chosen empirically (see past_chats)
  ```

- [ ] **AC6**: Performance benchmarks:
  - Single band processing: <500ms CPU
  - All 4 bands: <2s CPU total
  - Floor suppression: <300ms per band

- [ ] **AC7**: Integration with DB014 (Estimations model):
  - Returns list of dicts matching Estimation table schema
  - Each dict includes all required fields
  - Ready for bulk insert via repository

## Technical Implementation Notes

### Architecture
- Layer: Services / ML Processing
- Dependencies: ML003 (detections for calibration), DB014 (schema)
- Design pattern: Algorithm service, statistical calibration

### Code Hints

**Detection mask creation:**
```python
def _create_detection_mask(
    self,
    detections: list[dict],
    image_shape: tuple
) -> np.ndarray:
    """Create binary mask of all detection areas"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)

    for det in detections:
        x = int(det['center_x_px'])
        y = int(det['center_y_px'])
        w = int(det['width_px'])
        h = int(det['height_px'])

        # Draw filled circle (softer than rectangle)
        radius = int(max(w, h) * 0.85)
        cv2.circle(mask, (x, y), radius, 255, -1)

    # Gaussian blur for soft edges
    mask = cv2.GaussianBlur(mask, (15, 15), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    return mask
```

**Perspective compensation rationale:**
```
Band 1 (top, far):    Small plants, avg_area = 1500px
Band 2 (mid-far):     Medium plants, avg_area = 2000px
Band 3 (mid-close):   Medium plants, avg_area = 2500px
Band 4 (bottom, close): Large plants, avg_area = 3500px

Without bands: Would use single avg (2375px) → underestimate far, overestimate close
With bands: Each band calibrated correctly → accurate across whole image
```

### Testing Requirements

**Unit Tests** (`tests/services/ml_processing/test_band_estimation.py`):
```python
@pytest.mark.asyncio
async def test_band_division():
    """Image divided into 4 equal bands"""
    service = BandEstimationService()
    mask = np.ones((1000, 1500), dtype=np.uint8) * 255

    bands = service._divide_into_bands(mask, num_bands=4)

    assert len(bands) == 4
    # Each band height ~250px
    for band in bands:
        assert band.shape == (1000, 1500)
        assert np.sum(band > 0) > 0  # Has content

@pytest.mark.asyncio
async def test_floor_suppression():
    """Floor/soil removed from residual mask"""
    service = BandEstimationService()

    # Test image with soil + vegetation
    residual_mask = ...  # Load fixture
    processed = service._suppress_floor(residual_mask, 'fixture.jpg')

    # Processed area should be less (floor removed)
    assert np.sum(processed > 0) < np.sum(residual_mask > 0)
    # But not zero (vegetation remains)
    assert np.sum(processed > 0) > 0

@pytest.mark.asyncio
async def test_calibration_from_detections():
    """Auto-calibrate plant size from band detections"""
    service = BandEstimationService()

    # Simulate detections in band 1 (y: 0-250)
    detections = [
        {'center_x_px': 100, 'center_y_px': 50, 'width_px': 40, 'height_px': 40},
        {'center_x_px': 200, 'center_y_px': 100, 'width_px': 45, 'height_px': 38},
        # ... 10+ detections
    ]

    avg_area = service._calibrate_plant_size(detections, band_number=1, image_height=1000)

    # Should be average of width*height
    expected = np.mean([40*40, 45*38, ...])
    assert abs(avg_area - expected) < 50  # Within tolerance

@pytest.mark.asyncio
async def test_full_estimation_pipeline():
    """Complete band-based estimation"""
    service = BandEstimationService()

    # Mock inputs
    image_path = 'tests/fixtures/segmento_with_gaps.jpg'
    detections = [...]  # 500 detections
    segment_mask = ...  # Segmento mask

    estimations = await service.estimate_undetected_plants(
        image_path,
        detections,
        segment_mask
    )

    assert len(estimations) == 4  # One per band
    assert all(e['estimation_type'] == 'band_based' for e in estimations)
    assert sum(e['estimated_count'] for e in estimations) > 0
```

**Integration Tests**:
```python
@pytest.mark.asyncio
async def test_estimation_accuracy():
    """Verify estimation within 10% of ground truth"""
    # Fixture with known plant count
    ground_truth = 575  # Manually counted
    detected = 531  # YOLO detections

    service = BandEstimationService()
    estimations = await service.estimate_undetected_plants(...)

    estimated_undetected = sum(e['estimated_count'] for e in estimations)
    total_estimated = detected + estimated_undetected

    error_rate = abs(total_estimated - ground_truth) / ground_truth
    assert error_rate < 0.10  # Within 10%
```

**Coverage Target**: ≥85% (critical algorithm)

### Performance Expectations
- Band division: <50ms
- Floor suppression per band: <300ms
- Calibration per band: <100ms
- Total (4 bands): <2s CPU

## Handover Briefing

**For the next developer:**

**Context**: This is DemeterAI's **competitive advantage**. The band-based approach handles perspective distortion that competitors miss. This algorithm is proprietary IP.

**Key decisions made**:
1. **4 bands**: Empirically optimal (see past_chats). More bands = overfitting, fewer = underfitting.
2. **Alpha = 0.9**: Bias toward overestimation (better to overcount than undercount for sales)
3. **Auto-calibration**: Uses actual detections from each band (adaptive to image conditions)
4. **Floor suppression**: Combination of Otsu + HSV (more robust than either alone)
5. **IQR outlier removal**: Prevents one huge/tiny plant from skewing calibration

**Known limitations**:
- Requires ≥10 detections per band for good calibration (fallback to 2500px default)
- Assumes ground-level photos (not aerial drone shots)
- 4 bands hardcoded (could be made adaptive to image height)

**Next steps after this card**:
- ML006: Density-based Estimation (fallback when band-based fails)
- ML009: Pipeline Coordinator (orchestrates detection → estimation)
- R012: EstimationRepository (bulk insert of 4 estimations per session)

**Questions to validate**:
- Is alpha_overcount = 0.9 appropriate for all scenarios? (May need per-customer config)
- Are 4 bands sufficient for all greenhouse layouts? (May need 5-6 for very tall photos)
- Is floor suppression aggressive enough? (Check residual/processed area ratio in production)

**⚠️ CRITICAL PATH ALERT:**
- Assign senior ML engineer
- Pair program if stuck >1 day
- This card is CRITICAL - escalate blockers immediately

## Definition of Done Checklist

- [ ] Service code written with all 4 steps (mask, bands, suppression, calibration)
- [ ] Floor suppression algorithm working (HSV + Otsu)
- [ ] Auto-calibration from detections implemented
- [ ] 4 bands division tested
- [ ] Alpha overcount factor = 0.9
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests verify <10% error vs ground truth
- [ ] Performance benchmarks met (<2s for 4 bands)
- [ ] Returns schema matching DB014 (Estimations model)
- [ ] Documentation: Band-based algorithm rationale
- [ ] PR reviewed and approved (2+ reviewers + ML lead)
- [ ] No linting errors

## Time Tracking
- **Estimated**: 8 story points (complex algorithm)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (**MUST BE SENIOR ML ENGINEER**)
**Critical Path**: ⚡⚡ YES - Second highest priority in Sprint 02
