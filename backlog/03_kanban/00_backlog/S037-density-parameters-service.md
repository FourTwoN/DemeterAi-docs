# S037: DensityParametersService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (3 story points)
- **Area**: `services/config`
- **Dependencies**:
  - Blocks: [ML003, C033]
  - Blocked by: [R037, S021]

## Description

**What**: Service for density_parameters management (plant density calibration for ML estimation).

**Why**: Configures density-based estimation algorithm. Auto-calibrates from photo results.

**Context**: Application Layer. Used by ML pipeline (ML003) for density-based counting.

## Acceptance Criteria

- [ ] **AC1**: CRUD for density parameters
- [ ] **AC2**: Get density by product/size
- [ ] **AC3**: Auto-calibration from photo results (update density from actual counts)
- [ ] **AC4**: Validate density range (0.1-10.0 plants/m²)
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes
- Density in plants per m²
- Auto-calibration improves estimation accuracy over time

## Time Tracking
- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
