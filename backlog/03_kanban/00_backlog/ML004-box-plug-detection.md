# [ML004] Box/Plug Detection Service - Direct YOLO for Cajones

## Metadata

- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `services/ml_processing`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [ML009-pipeline-coordinator]
    - Blocked by: [ML001-model-singleton, ML002-yolo-segmentation]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md
- **ML Pipeline Flow**:
  ../../flows/procesamiento_ml_upload_s3_principal/06_boxes_plugs_detection_detailed.md
- **Context**: ../../context/past_chats_summary.md (Direct vs SAHI strategy)

## Description

Implement direct YOLO detection service for small cajones (boxes/plugs). Unlike segmentos that need
SAHI tiling, cajones are small enough for direct inference without downscaling issues.

**What**: Service that:

- Takes cropped cajon images (<1000×1000px typically)
- Runs YOLO detection directly (no tiling needed)
- Maps detection coordinates back to original image
- Handles both "cajon" and "plug" container types

**Why**:

- **Efficiency**: Cajones don't need SAHI overhead (small images)
- **Speed**: Direct inference 5-10× faster than tiling
- **Simplicity**: No tile merging, no black tile filtering
- **Accuracy**: Sufficient at native resolution

**Context**: Dual detection strategy - SAHI for large segmentos, direct YOLO for small cajones. This
is the simpler path.

## Acceptance Criteria

- [ ] **AC1**: Service class created in `app/services/ml_processing/detection_service.py`:
  ```python
  class DirectDetectionService:
      def __init__(self, worker_id: int = 0):
          self.worker_id = worker_id
          self.model = ModelCache.get_detection_model(worker_id)

      async def detect_in_cajon(
          self,
          image_path: str,
          cajon_bbox: dict,  # {x1, y1, x2, y2} in original coords
          confidence_threshold: float = 0.25
      ) -> list[dict]:
          """
          Detect plants in small cajon using direct YOLO.

          Returns detections in ORIGINAL image coordinates.
          """
          # Direct YOLO inference
          results = self.model.predict(
              image_path,
              conf=confidence_threshold,
              device='cpu' if not torch.cuda.is_available() else f'cuda:{self.worker_id}',
              verbose=False
          )

          # Map to original coordinates (add cajon offset)
          detections = []
          for box in results[0].boxes:
              x_center = box.xywh[0][0].item() + cajon_bbox['x1']
              y_center = box.xywh[0][1].item() + cajon_bbox['y1']
              width = box.xywh[0][2].item()
              height = box.xywh[0][3].item()

              detections.append({
                  'center_x_px': x_center,
                  'center_y_px': y_center,
                  'width_px': width,
                  'height_px': height,
                  'confidence': box.conf.item(),
                  'class_name': self.model.names[int(box.cls.item())]
              })

          return detections
  ```

- [ ] **AC2**: Coordinate mapping correctly adds cajon offset:
  ```python
  # Cajon cropped from (500, 300) → (900, 700) in original image
  # Detection at (50, 80) in cropped image
  # Should map to (550, 380) in original image
  original_x = detection_x + cajon_bbox['x1']  # 50 + 500 = 550
  original_y = detection_y + cajon_bbox['y1']  # 80 + 300 = 380
  ```

- [ ] **AC3**: Performance benchmarks met:
    - Small cajon (500×500px): <200ms CPU, <50ms GPU
    - Medium cajon (800×800px): <400ms CPU, <100ms GPU
    - Large cajon (1000×1000px): <600ms CPU, <150ms GPU

- [ ] **AC4**: Edge cases handled:
    - Empty cajon (no plants) → return empty list
    - Very small cajon (<200px) → still process (no minimum size)
    - Corrupted crop → raise clear exception

- [ ] **AC5**: Container type differentiation:
  ```python
  # Service can handle both cajones and plugs
  # (same algorithm, different semantic container_type)
  result['container_type'] = 'cajon'  # or 'plug'
  ```

- [ ] **AC6**: Integration with ML002 segmentation outputs:
    - Receives cajon bounding boxes from segmentation
    - Processes each cajon independently
    - Returns combined results for all cajones

## Technical Implementation Notes

### Architecture

- Layer: Services / ML Processing
- Dependencies: ML001 (Model Singleton), ML002 (Segmentation)
- Design pattern: Service layer, direct YOLO inference

### Code Hints

**Direct YOLO inference:**

```python
from ultralytics import YOLO

# Model already loaded in singleton
results = self.model.predict(
    image_path,
    conf=0.25,
    iou=0.45,  # NMS threshold
    max_det=300,  # Max detections per image
    device='cpu',
    verbose=False
)

# Access results
for result in results:
    boxes = result.boxes  # Detections
    for box in boxes:
        x, y, w, h = box.xywh[0].tolist()
        confidence = box.conf.item()
        class_id = int(box.cls.item())
```

**Coordinate offset calculation:**

```python
def map_to_original_coords(
    detection: dict,
    crop_offset: tuple[int, int]
) -> dict:
    """Map detection from crop coords to original image coords"""
    offset_x, offset_y = crop_offset

    return {
        'center_x_px': detection['center_x_px'] + offset_x,
        'center_y_px': detection['center_y_px'] + offset_y,
        'width_px': detection['width_px'],  # Size unchanged
        'height_px': detection['height_px'],
        'confidence': detection['confidence'],
        'class_name': detection['class_name']
    }
```

### Testing Requirements

**Unit Tests** (`tests/services/ml_processing/test_direct_detection.py`):

```python
@pytest.mark.asyncio
async def test_direct_detection_on_small_cajon():
    """Test direct YOLO on 500×500 cajon"""
    service = DirectDetectionService(worker_id=0)

    cajon_bbox = {'x1': 100, 'y1': 200, 'x2': 600, 'y2': 700}

    detections = await service.detect_in_cajon(
        'tests/fixtures/small_cajon.jpg',
        cajon_bbox,
        confidence_threshold=0.25
    )

    assert len(detections) > 0
    # Verify coordinates are in original image space (not crop space)
    for det in detections:
        assert det['center_x_px'] >= cajon_bbox['x1']
        assert det['center_y_px'] >= cajon_bbox['y1']

@pytest.mark.asyncio
async def test_coordinate_mapping_correctness():
    """Verify offset is applied correctly"""
    service = DirectDetectionService()

    # Known test case: cajon at (500, 300), detection at (50, 80) in crop
    cajon_bbox = {'x1': 500, 'y1': 300, 'x2': 900, 'y2': 700}

    detections = await service.detect_in_cajon(
        'tests/fixtures/cajon_known_offset.jpg',
        cajon_bbox
    )

    # First detection should be at (550, 380) in original coords
    # (This requires manual verification of fixture)
    assert detections[0]['center_x_px'] > 500
    assert detections[0]['center_y_px'] > 300

@pytest.mark.asyncio
async def test_performance_benchmark():
    """Direct YOLO should be fast on small cajones"""
    service = DirectDetectionService()
    cajon_bbox = {'x1': 0, 'y1': 0, 'x2': 500, 'y2': 500}

    start = time.time()
    detections = await service.detect_in_cajon(
        'tests/fixtures/cajon_500x500.jpg',
        cajon_bbox
    )
    elapsed = time.time() - start

    assert elapsed < 0.6  # <600ms on CPU for 500×500
```

**Integration Tests**:

```python
@pytest.mark.asyncio
async def test_multiple_cajones_processing():
    """Process all cajones from one image"""
    segmentation_service = YOLOSegmentationService()
    detection_service = DirectDetectionService()

    # Get cajon masks from segmentation
    segments = await segmentation_service.segment_image('test_image.jpg')
    cajones = [s for s in segments if s['class_name'] == 'cajon']

    # Detect in each cajon
    all_detections = []
    for cajon in cajones:
        detections = await detection_service.detect_in_cajon(
            'test_image.jpg',
            cajon['bbox']
        )
        all_detections.extend(detections)

    assert len(all_detections) > 0
    # Verify no overlap (each detection belongs to one cajon)
```

**Coverage Target**: ≥80%

### Performance Expectations

- **500×500 cajon**: 200ms CPU, 50ms GPU
- **800×800 cajon**: 400ms CPU, 100ms GPU
- **Typical image** (3-5 cajones): 1-2s total CPU, 200-400ms GPU

## Handover Briefing

**For the next developer:**

**Context**: This is the "easy path" compared to ML003 (SAHI). Cajones are small, so direct YOLO
works perfectly.

**Key decisions made**:

1. **No tiling needed**: Cajones <1000px don't benefit from SAHI
2. **Coordinate offset**: Must add cajon bbox offset to map back to original
3. **Same model as SAHI**: Uses detection model from ModelCache singleton
4. **Container type flexibility**: Works for both cajones and plugs (same algorithm)

**Known limitations**:

- If cajones become larger (>1500px), may need to switch to SAHI
- Assumes cajones are already cropped by ML002 segmentation

**Next steps after this card**:

- ML009: Pipeline Coordinator (orchestrates ML002 → ML003/ML004 → aggregation)
- ML015: Grouping Service (merges nearby detections from cajones)

**Questions to validate**:

- Are cajon bboxes coming from ML002 in correct format? (Should be {x1, y1, x2, y2})
- Is offset being added correctly? (Test with known fixture)
- Are cajones and plugs treated identically? (Should be YES)

## Definition of Done Checklist

- [ ] Service code written following DirectDetectionService pattern
- [ ] Model singleton integrated correctly (ModelCache)
- [ ] Coordinate offset mapping validated with tests
- [ ] Performance benchmarks met (<600ms CPU for 1000×1000)
- [ ] Edge cases handled (empty cajon, corrupt image)
- [ ] Unit tests pass (≥80% coverage)
- [ ] Integration tests verify multi-cajon workflow
- [ ] Documentation includes coordinate mapping example
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors

## Time Tracking

- **Estimated**: 5 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
