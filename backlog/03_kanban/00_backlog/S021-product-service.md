# S021: ProductService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/catalog`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S027, S036, C020]
  - Blocked by: [R021, S020]

## Description

**What**: Product service with SKU generation, family validation, and price integration.

**Why**: Core product catalog. SKU auto-generation for inventory tracking.

**Context**: Application Layer. Orchestrates product creation with SKU generation.

## Acceptance Criteria

- [ ] **AC1**: Create product with auto-generated SKU (format: FAM-STATE-SIZE-001)
- [ ] **AC2**: Validate parent family via ProductFamilyService
- [ ] **AC3**: Get products by family/category
- [ ] **AC4**: SKU uniqueness validation
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes
- SKU format: ECHEVERIA-PLANTA-M-001
- Auto-increment suffix within family/state/size combination

## Time Tracking
- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
