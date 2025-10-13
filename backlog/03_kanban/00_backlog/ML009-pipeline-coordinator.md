# [ML009] Pipeline Coordinator Service ⚡⚡

## Metadata
- **Epic**: epic-007
- **Sprint**: Sprint-02
- **Priority**: `critical` ⚡⚡ **CRITICAL PATH**
- **Complexity**: L (8 points)
- **Dependencies**: Blocks [CEL005], Blocked by [ML002, ML003, ML004, ML005]

## Description
Orchestrate complete ML pipeline: Segmentation → Detection (SAHI/Direct) → Estimation → Aggregation. This is the CRITICAL PATH coordinator.

## Acceptance Criteria
- [ ] Method `process_complete_pipeline(session_id, image_path)` orchestrates all steps
- [ ] Calls ML002 (segmentation) → ML003/ML004 (detection) → ML005/ML006 (estimation)
- [ ] Updates DB012 (PhotoProcessingSession) progress at each stage
- [ ] Bulk inserts detections/estimations via repositories
- [ ] Error handling with warning states (not hard failures)
- [ ] Returns complete results dict

## Implementation
```python
class MLPipelineCoordinator:
    def __init__(self, segmentation_svc, sahi_svc, direct_svc, band_est_svc, ...):
        self.segmentation = segmentation_svc
        self.sahi = sahi_svc
        self.direct = direct_svc
        self.band_estimation = band_est_svc

    async def process_complete_pipeline(self, session_id, image_path):
        # 1. Segmentation (20% progress)
        segments = await self.segmentation.segment_image(image_path)
        await self.update_progress(session_id, 0.2)

        # 2. Detection (50% progress)
        all_detections = []
        for seg in segments:
            if seg['class'] == 'segmento':
                dets = await self.sahi.detect_in_segmento(image_path, seg)
            else:  # cajon
                dets = await self.direct.detect_in_cajon(image_path, seg['bbox'])
            all_detections.extend(dets)
        await self.update_progress(session_id, 0.5)

        # 3. Estimation (80% progress)
        estimations = await self.band_estimation.estimate_undetected_plants(...)
        await self.update_progress(session_id, 0.8)

        # 4. Persist (100% progress)
        await self.detection_repo.bulk_insert(all_detections)
        await self.estimation_repo.bulk_insert(estimations)
        await self.update_session_complete(session_id, all_detections, estimations)

        return {'detections': len(all_detections), 'estimations': sum(e['estimated_count'] for e in estimations)}
```

## Testing
- Integration test with full pipeline
- Verify progress updates
- Test error recovery
- Coverage ≥85%

## Handover
**CRITICAL**: This orchestrates everything. Most complex service in ML pipeline. Assign to tech lead.

---
**Card Created**: 2025-10-09
**Critical Path**: ⚡⚡ HIGHEST PRIORITY COORDINATOR
