# R024: Classification Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R022, R023, S021]
  - Blocked by: [F006, F007, DB026, R008, R010, R014]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L290-L302)

## Description

**What**: Implement repository class for `classifications` table with CRUD operations and multi-model confidence tracking.

**Why**: Classifications store ML classification results (product + size + packaging) with confidence scores per model. Repository provides classification lookup and confidence-based filtering for quality control.

**Context**: Links detections/estimations to product catalog. Each classification has 3 confidence scores (product_conf, packaging_conf, product_size_conf) for quality filtering. model_version tracks ML model for reproducibility.

## Acceptance Criteria

- [ ] **AC1**: `ClassificationRepository` class inherits from `AsyncRepository[Classification]`
- [ ] **AC2**: Implements `get_by_product_id(product_id: int)` for species filtering
- [ ] **AC3**: Implements `get_high_confidence_classifications(min_confidence: float)` for quality control
- [ ] **AC4**: Implements `get_by_model_version(model_version: str)` for ML reproducibility
- [ ] **AC5**: Includes eager loading for product, product_size, packaging_catalog
- [ ] **AC6**: Query performance: <20ms for most queries

## Technical Implementation Notes

**Code hints**: get_high_confidence_classifications (filter by min confidence across all 3 models), get_by_model_version (for A/B testing), get_classification_summary (GROUP BY product_id for analytics).

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Confidence filtering tested
- [ ] Model version tracking tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
