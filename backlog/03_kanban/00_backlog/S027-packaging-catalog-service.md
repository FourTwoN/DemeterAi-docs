# S027: PackagingCatalogService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/catalog`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S036, C024]
  - Blocked by: [R027, S024, S025, S026]

## Description

**What**: Packaging catalog service with SKU generation (type + material + color + dimensions).

**Why**: Complete packaging catalog with SKU auto-generation for stock tracking.

**Context**: Application Layer. Orchestrates packaging type/material/color services.

## Acceptance Criteria

- [ ] **AC1**: Create packaging with auto-generated SKU (format: TYPE-MATERIAL-COLOR-DIM)
- [ ] **AC2**: Validate packaging components via services (type, material, color)
- [ ] **AC3**: SKU uniqueness validation
- [ ] **AC4**: Get packaging by filters (type, material, color, dimensions)
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes
- SKU format: MACETA-PLASTICO-NEGRO-10CM
- Dimensions included in SKU for uniqueness

## Time Tracking
- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
