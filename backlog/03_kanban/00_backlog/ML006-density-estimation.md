# [ML006] Density-Based Estimation Service - Fallback Algorithm

## Metadata

- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (5 story points)
- **Area**: `services/ml_processing`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [ML009]
    - Blocked by: [ML005, DB014]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md
- **Database**: ../../database/database.mmd (estimations table)

## Description

Implement density-based estimation as fallback when band-based fails (insufficient detections for
calibration). Uses global density parameter instead of per-band calibration.

**What**: Service calculates `estimated_count = residual_area * density_factor` where density_factor
is plants per square pixel.

**Why**: Fallback for edge cases (very few detections, unusual layouts).

**Context**: Secondary algorithm. Band-based (ML005) is primary.

## Acceptance Criteria

- [ ] **AC1**: Service class `DensityEstimationService` with method
  `estimate_by_density(residual_area_px, density_factor) -> int`
- [ ] **AC2**: Density factor defaults to 0.000658 plants/px² (empirically derived)
- [ ] **AC3**: Returns single estimation (not per-band like ML005)
- [ ] **AC4**: Integration with DensityParameters table for per-location calibration
- [ ] **AC5**: Falls back to this when ML005 calibration fails (<10 detections)

## Technical Implementation Notes

```python
class DensityEstimationService:
    async def estimate_by_density(
        self,
        residual_mask: np.ndarray,
        density_factor: float = 0.000658
    ) -> dict:
        processed_area = np.sum(residual_mask > 0)
        estimated_count = int(np.ceil(processed_area * density_factor))

        return {
            'estimation_type': 'density_based',
            'residual_area_px': float(processed_area),
            'estimated_count': estimated_count,
            'density_factor': density_factor
        }
```

## Testing Requirements

- Test with known density scenarios
- Verify fallback from ML005 triggers correctly
- Coverage ≥75%

## Handover Briefing

Simpler algorithm than ML005. Use when band-based can't calibrate.

## Definition of Done

- [ ] Code passes tests
- [ ] Integration with ML009 coordinator
- [ ] PR approved

## Time Tracking

- **Estimated**: 5 points
- **Actual**: TBD

---
**Card Created**: 2025-10-09
**Card Owner**: TBD
