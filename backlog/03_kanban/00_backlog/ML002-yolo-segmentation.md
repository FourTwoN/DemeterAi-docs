# [ML002] YOLO v11 Segmentation Service

## Metadata
- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical` ⚡
- **Complexity**: L (8 points)
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [ML003, ML009]
  - Blocked by: [ML001]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md
- **Flow**: ../../flows/procesamiento_ml_upload_s3_principal/04_ml_parent_segmentation_detailed.md

## Description

Implement YOLO v11 segmentation service to identify containers (plugs, boxes, segments) in greenhouse photos using Model Singleton pattern.

**What**: Service that loads segmentation model, runs inference, returns polygon masks for each container.

**Why**: Segmentation is first step in ML pipeline - identifies regions before detection. Container types determine processing strategy (SAHI vs direct).

## Acceptance Criteria

- [ ] SegmentationService class created in `app/services/ml_processing/`
- [ ] Uses ModelCache.get_model("segment", worker_id)
- [ ] Detects containers: plugs, boxes, segments (remapped from "claro-cajon")
- [ ] Returns polygon masks + bounding boxes + confidence scores
- [ ] Confidence threshold configurable (default 0.30)
- [ ] Performance: <1s inference time for 4000×3000px image on CPU
- [ ] Unit tests ≥85% coverage

## Technical Notes

**Service structure**:
```python
class SegmentationService:
    def __init__(self):
        self.model = None  # Lazy load via singleton

    async def segment_image(
        self,
        image_path: str,
        worker_id: int = 0,
        conf_threshold: float = 0.30
    ) -> List[SegmentResult]:
        # Get model from singleton
        if not self.model:
            self.model = ModelCache.get_model("segment", worker_id)

        # Run inference
        results = self.model.predict(
            image_path,
            imgsz=1024,  # Higher res for small objects
            conf=conf_threshold,
            iou=0.50
        )

        return self._parse_results(results)
```

---

**Created**: 2025-10-09
