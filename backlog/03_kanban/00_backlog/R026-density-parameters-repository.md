# R026: Density Parameters Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [ML006, S023]
  - Blocked by: [F006, F007, DB025, R005, R008, R014]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L315-L327)

## Description

**What**: Implement repository class for `density_parameters` table with CRUD operations and ML calibration queries.

**Why**: Density parameters define plant density calibration data (avg area per plant, plants per m²) for ML estimation algorithms. Repository provides density lookup for band-estimation and density-estimation methods.

**Context**: Used by ML pipeline (ML006 density-estimation service). Each combination of bin_type + product + packaging has calibrated density parameters. Critical for accurate plant counting in high-density scenarios.

## Acceptance Criteria

- [ ] **AC1**: `DensityParametersRepository` class inherits from `AsyncRepository[DensityParameters]`
- [ ] **AC2**: Implements `get_by_bin_type_and_product(bin_type_id: int, product_id: int, packaging_id: int)` for ML lookup
- [ ] **AC3**: Implements `get_by_product_id(product_id: int)` for calibration overview
- [ ] **AC4**: Implements `calculate_expected_count(area_cm2: float, parameters_id: int)` for ML estimation
- [ ] **AC5**: Includes eager loading for storage_bin_type, product, packaging_catalog
- [ ] **AC6**: Query performance: <15ms

## Technical Implementation Notes

**Code hints**: get_by_bin_type_and_product (composite lookup for ML), calculate_expected_count (area_cm2 / avg_area_per_plant), get_uncalibrated_combinations (find missing density data).

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Density calculation tested
- [ ] ML lookup tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 2 story points (~4 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
