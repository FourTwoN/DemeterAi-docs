# R021: Product Sample Image Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S018]
  - Blocked by: [F006, F007, DB246, R020, R008]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L246-L260)

## Description

**What**: Implement repository class for `product_sample_images` table with CRUD operations, product_id filtering, and primary image management.

**Why**: Product sample images link products to reference photos (growth stages, quality checks, catalog images). Repository provides image gallery management and primary image selection.

**Context**: Links products to s3_images. is_primary flag designates catalog hero image. display_order for gallery sorting.

## Acceptance Criteria

- [ ] **AC1**: `ProductSampleImageRepository` class inherits from `AsyncRepository[ProductSampleImage]`
- [ ] **AC2**: Implements `get_by_product_id(product_id: int)` ordered by display_order
- [ ] **AC3**: Implements `get_primary_image(product_id: int)` for catalog display
- [ ] **AC4**: Implements `set_primary_image(image_id: int)` updating is_primary flags
- [ ] **AC5**: Includes eager loading for s3_image, product, product_state, product_size
- [ ] **AC6**: Query performance: <20ms for product galleries

## Technical Implementation Notes

**Code hints**: get_by_product_id (ordered by display_order), get_primary_image (is_primary=true), set_primary_image (transaction: set all false, then set one true), get_by_sample_type (reference/growth_stage/quality_check).

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Primary image management tested (transactional)
- [ ] Display order sorting tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 2 story points (~4 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
