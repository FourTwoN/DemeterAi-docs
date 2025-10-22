# [ML003] SAHI Detection Service - Tiling Strategy

## Metadata

- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `critical` ⚡⚡⚡ **CRITICAL PATH**
- **Complexity**: L (8 story points)
- **Area**: `services/ml_processing`
- **Assignee**: TBD (assign to senior ML engineer)
- **Dependencies**:
    - Blocks: [ML005-band-estimation, ML009-pipeline-coordinator, CEL006]
    - Blocked by: [ML002-yolo-segmentation, ML001-model-singleton]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md
- **ML Pipeline Flow**:
  ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md (SAHI library)
- **Context**: ../../context/past_chats_summary.md (10x improvement with SAHI)

## Description

Implement the SAHI (Slicing Aided Hyper Inference) detection service that processes large segmentos
using intelligent tiling. This is the **critical innovation** that improved detection from 100
plants to 800+ plants per image.

**What**: Service that:

- Takes cropped segmento images (potentially 3000×1500px)
- Slices them into overlapping 512×512 tiles
- Runs YOLO detection on each tile
- Intelligently merges results with GREEDYNMM algorithm
- Returns detections in original image coordinates

**Why**:

- **Direct YOLO fails on large images**: Downscaling loses small objects
- **Naive tiling creates duplicates**: Plants on tile boundaries detected twice
- **SAHI solves both**: Optimal tile size + intelligent merging
- **10x improvement**: 100 → 800+ plants detected per image

**Context**: This is the **CRITICAL PATH bottleneck**. If this card is delayed, the entire Sprint 02
fails. Most complex card in ML pipeline.

## Acceptance Criteria

- [ ] **AC1**: Service class created in `app/services/ml_processing/detection_service.py`:
  ```python
  from sahi.predict import get_sliced_prediction
  from sahi import AutoDetectionModel
  from app.services.ml_processing.model_cache import ModelCache

  class SAHIDetectionService:
      def __init__(self, worker_id: int = 0):
          self.worker_id = worker_id
          # Model loaded once per worker (singleton pattern)
          self.model = ModelCache.get_detection_model(worker_id)

      async def detect_in_segmento(
          self,
          image_path: str,
          confidence_threshold: float = 0.25
      ) -> list[dict]:
          """
          Detect plants in large segmento using SAHI tiling.

          Returns:
              List of detections with keys:
              - center_x_px, center_y_px (in original image coords)
              - width_px, height_px
              - confidence
              - class_name
          """
          # Configure SAHI wrapper around YOLO model
          detector = AutoDetectionModel.from_pretrained(
              model_type='ultralytics',
              model=self.model,  # Pre-loaded YOLO model
              confidence_threshold=confidence_threshold,
              device=f'cuda:{self.worker_id}' if torch.cuda.is_available() else 'cpu'
          )

          # SAHI prediction with tiling
          result = get_sliced_prediction(
              image_path,
              detector,
              slice_height=512,
              slice_width=512,
              overlap_height_ratio=0.25,  # 25% overlap
              overlap_width_ratio=0.25,
              postprocess_type='GREEDYNMM',  # Intelligent merging
              postprocess_match_threshold=0.5,  # IOS threshold
              auto_skip_black_tiles=True,  # Skip <2% content tiles
              verbose=0
          )

          # Convert SAHI results to our format
          detections = []
          for obj_pred in result.object_prediction_list:
              bbox = obj_pred.bbox
              detections.append({
                  'center_x_px': bbox.minx + (bbox.maxx - bbox.minx) / 2,
                  'center_y_px': bbox.miny + (bbox.maxy - bbox.miny) / 2,
                  'width_px': bbox.maxx - bbox.minx,
                  'height_px': bbox.maxy - bbox.miny,
                  'confidence': obj_pred.score.value,
                  'class_name': obj_pred.category.name
              })

          return detections
  ```

- [ ] **AC2**: Tiling configuration optimized for DemeterAI use case:
    - **Tile size**: 512×512px (balance between context and inference speed)
    - **Overlap**: 25% (128px) to catch boundary plants
    - **Black tile filtering**: Skip tiles with <2% green pixels
    - **Merge algorithm**: GREEDYNMM (better than NMS for overlapping objects)

- [ ] **AC3**: Coordinate mapping verified:
  ```python
  # SAHI already returns coordinates in original image space
  # NO additional offset needed (unlike cajon direct detection)
  assert detections[0]['center_x_px'] < image_width  # Original coords
  ```

- [ ] **AC4**: Black tile optimization working:
  ```python
  # Before: 35 tiles generated
  # After black tile skip: 28 tiles processed (7 skipped)
  # Saves ~20% computation time
  ```

- [ ] **AC5**: GREEDYNMM merging validated:
  ```python
  # Test case: Plant on tile boundary
  # Should be detected in 2 adjacent tiles
  # GREEDYNMM should merge to 1 detection (not 2 duplicates)
  ```

- [ ] **AC6**: Performance benchmarked:
    - **CPU**: 4-6 seconds for 3000×1500px segmento
    - **GPU**: 1-2 seconds for same image
    - **Throughput**: ~150-200 tiles/second on CPU

- [ ] **AC7**: Error handling for edge cases:
    - Empty segmento (no plants) → return empty list (not error)
    - Very small segmento (<512px) → direct detection (no tiling)
    - Corrupted image → raise clear exception with image path

## Technical Implementation Notes

### Architecture

- Layer: Services / ML Processing
- Dependencies: ML001 (Model Singleton), ML002 (Segmentation outputs)
- Design pattern: Service layer, dependency injection

### Code Hints

**SAHI library integration:**

```python
# Install: pip install sahi==0.11.18

from sahi.predict import get_sliced_prediction
from sahi import AutoDetectionModel

# CRITICAL: Wrap pre-loaded YOLO model (don't reload per task)
detector = AutoDetectionModel.from_pretrained(
    model_type='ultralytics',
    model=self.model,  # Already loaded in worker
    confidence_threshold=0.25,
    device='cpu'  # or f'cuda:{worker_id}'
)
```

**Black tile filtering (performance optimization):**

```python
# SAHI built-in feature:
auto_skip_black_tiles=True  # Skips tiles with <2% content

# Custom implementation (if needed):
def is_black_tile(tile_image: np.ndarray) -> bool:
    """Check if tile is mostly background"""
    # Convert to HSV, check for vegetation
    hsv = cv2.cvtColor(tile_image, cv2.COLOR_BGR2HSV)
    green_mask = cv2.inRange(
        hsv,
        (30, 40, 40),   # Lower green bound
        (90, 255, 255)  # Upper green bound
    )
    green_ratio = np.sum(green_mask > 0) / green_mask.size
    return green_ratio < 0.02  # Less than 2% green
```

**GREEDYNMM vs NMS:**

```
NMS (Non-Maximum Suppression):
- Removes overlapping boxes based on IOU
- Can wrongly remove adjacent plants

GREEDYNMM (Greedy Non-Maximum Merging):
- Merges overlapping boxes from different tiles
- Preserves adjacent plants
- Uses IOS (Intersection over Smaller) instead of IOU
- Better for tiling scenarios
```

**Performance optimization tips:**

```python
# 1. Pre-load model (CRITICAL - already done in ML001)
# 2. Use FP16 on GPU (2× faster):
if torch.cuda.is_available():
    model.half()  # FP16

# 3. Batch tile inference (if SAHI supports):
batch_size = 4 if GPU else 1

# 4. Skip black tiles (20% speedup):
auto_skip_black_tiles=True
```

### Testing Requirements

**Unit Tests** (`tests/services/ml_processing/test_sahi_detection.py`):

```python
@pytest.mark.asyncio
async def test_sahi_detection_on_large_segmento():
    """Test SAHI on 3000×1500px segmento"""
    service = SAHIDetectionService(worker_id=0)

    detections = await service.detect_in_segmento(
        'tests/fixtures/large_segmento.jpg',
        confidence_threshold=0.25
    )

    assert len(detections) > 0
    assert all('center_x_px' in d for d in detections)
    assert all(0 <= d['confidence'] <= 1.0 for d in detections)

@pytest.mark.asyncio
async def test_coordinate_mapping_correct():
    """Coordinates should be in original image space"""
    service = SAHIDetectionService()
    detections = await service.detect_in_segmento('tests/fixtures/segmento.jpg')

    # Verify coordinates are within image bounds
    img = cv2.imread('tests/fixtures/segmento.jpg')
    height, width = img.shape[:2]

    for det in detections:
        assert 0 <= det['center_x_px'] < width
        assert 0 <= det['center_y_px'] < height

@pytest.mark.asyncio
async def test_greedynmm_merges_duplicates():
    """Plant on tile boundary should be 1 detection, not 2"""
    service = SAHIDetectionService()

    # Use image with plant exactly on tile boundary
    detections = await service.detect_in_segmento(
        'tests/fixtures/boundary_plant.jpg'
    )

    # Expect 1 detection (merged), not 2 (duplicates)
    # This test requires manual verification of fixture image
    # Ideally: 1 plant → 1 detection (not 2)
    assert len(detections) >= 1
```

**Integration Tests** (`tests/integration/test_full_sahi_pipeline.py`):

```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_sahi_vs_direct_detection_improvement():
    """Verify SAHI detects 5-10× more plants than direct YOLO"""
    from app.services.ml_processing.direct_detection_service import DirectDetectionService

    sahi_service = SAHIDetectionService()
    direct_service = DirectDetectionService()

    test_image = 'tests/fixtures/production_segmento_4000x3000.jpg'

    # Direct YOLO (downscaled)
    direct_detections = await direct_service.detect(test_image)

    # SAHI tiling
    sahi_detections = await sahi_service.detect_in_segmento(test_image)

    # SAHI should detect significantly more
    improvement_ratio = len(sahi_detections) / len(direct_detections)
    assert improvement_ratio >= 5.0  # At least 5× improvement
    assert len(sahi_detections) >= 500  # Typical large segmento

@pytest.mark.asyncio
async def test_performance_benchmark():
    """SAHI should process 3000×1500 image in <10s on CPU"""
    service = SAHIDetectionService()

    start = time.time()
    detections = await service.detect_in_segmento(
        'tests/fixtures/segmento_3000x1500.jpg'
    )
    elapsed = time.time() - start

    assert elapsed < 10.0  # <10s on CPU acceptable
    assert len(detections) > 0
```

**Coverage Target**: ≥85% (critical path)

### Performance Expectations

- **CPU (3000×1500 segmento)**:
    - Total time: 4-6 seconds
    - Tiles generated: ~35
    - Tiles processed: ~28 (7 skipped as black)
    - Detections: 500-800 plants
- **GPU (same image)**:
    - Total time: 1-2 seconds
    - 3-4× speedup vs CPU

## Handover Briefing

**For the next developer:**

**Context**: This is the **CRITICAL PATH** card. Everything depends on this working correctly.
Sprint 02 success = this card completing on time.

**Key decisions made**:

1. **SAHI library chosen**: Proven solution, don't reinvent tiling algorithm
2. **512×512 tiles**: Balance between context (larger) and speed (smaller)
3. **25% overlap**: Catches boundary plants without excessive redundancy
4. **GREEDYNMM**: Better than NMS for tiling (uses IOS, not IOU)
5. **Auto black tile skip**: 20% speedup, no accuracy loss

**Known limitations**:

- SAHI adds overhead (~20% slower than naive tiling)
- Merging algorithm not perfect (may merge truly adjacent plants)
- Memory scales with image size (3000×1500 = ~35 tiles in memory)

**Next steps after this card**:

- ML005: Band-based Estimation (uses SAHI detection results for calibration)
- ML009: Pipeline Coordinator (orchestrates segmentation → SAHI → estimation)
- CEL006: ML Child Tasks (Celery wrapper around this service)

**Questions to validate**:

- Is SAHI model using the pre-loaded singleton? (Should be YES - check ModelCache)
- Are tiles being processed in parallel or serial? (SAHI does serial - acceptable)
- Is GREEDYNMM threshold (0.5 IOS) optimal? (May need tuning based on plant spacing)

**⚠️ CRITICAL PATH ALERT:**

- Assign senior ML engineer
- Pair program if stuck >1 day
- Daily progress check (not just standup)
- Escalate blockers within 1 hour

## Definition of Done Checklist

- [ ] Service code written and follows Service→Singleton pattern
- [ ] SAHI library integrated correctly
- [ ] Tiling configuration optimized (512×512, 25% overlap)
- [ ] GREEDYNMM merging working (no duplicates on boundaries)
- [ ] Black tile filtering active (verified 20% speedup)
- [ ] Coordinate mapping validated (original image space)
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests verify 5× improvement over direct YOLO
- [ ] Performance benchmarked (<6s CPU, <2s GPU for 3000×1500px)
- [ ] Edge cases handled (empty segmento, small segmento, corrupt image)
- [ ] Documentation: SAHI configuration rationale
- [ ] PR reviewed and approved (2+ reviewers + ML lead sign-off)
- [ ] No linting errors

## Time Tracking

- **Estimated**: 8 story points (critical path, complex)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD
- **Blockers encountered**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (**MUST BE SENIOR ML ENGINEER**)
**Critical Path**: ⚡⚡⚡ YES - Highest priority in Sprint 02
