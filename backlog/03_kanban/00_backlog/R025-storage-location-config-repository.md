# R025: Storage Location Config Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S022]
  - Blocked by: [F006, F007, DB024, R003, R008, R014]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L303-L314)

## Description

**What**: Implement repository class for `storage_location_config` table with CRUD operations and validation queries.

**Why**: Storage location configs define expected products/packaging for locations (for manual stock initialization validation). Repository provides configuration lookup and validation for manual workflows.

**Context**: Used by manual stock initialization to validate user input. Links storage_locations to expected products/packaging/states. Active flag enables/disables configurations.

## Acceptance Criteria

- [ ] **AC1**: `StorageLocationConfigRepository` class inherits from `AsyncRepository[StorageLocationConfig]`
- [ ] **AC2**: Implements `get_by_storage_location_id(location_id: int)` for validation
- [ ] **AC3**: Implements `get_active_configs(location_id: int)` filtering by active flag
- [ ] **AC4**: Implements `validate_product_for_location(location_id: int, product_id: int)` for manual input validation
- [ ] **AC5**: Includes eager loading for storage_location, product, packaging_catalog, expected_product_state
- [ ] **AC6**: Query performance: <20ms

## Technical Implementation Notes

**Code hints**: get_active_configs (active=true), validate_product_for_location (check if product allowed for location), get_configs_by_product (reverse lookup).

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Validation logic tested
- [ ] Active filtering tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 2 story points (~4 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
