# S020: ProductFamilyService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `services/catalog`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S021, C019]
  - Blocked by: [R020, S019]

## Description

**What**: CRUD service for product_families with parent category validation.

**Why**: Second level of product taxonomy.

**Context**: Application Layer. Validates parent category via S019.

## Acceptance Criteria

- [ ] **AC1**: CRUD with parent category validation (via ProductCategoryService)
- [ ] **AC2**: Get families by category
- [ ] **AC3**: Code uniqueness within category
- [ ] **AC4**: Unit tests ≥80% coverage

## Time Tracking
- **Estimated**: 1 story point (~2 hours)

---
**Card Created**: 2025-10-09
