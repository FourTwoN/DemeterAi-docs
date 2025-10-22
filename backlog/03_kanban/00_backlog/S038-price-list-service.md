# S038: PriceListService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (3 story points)
- **Area**: `services/config`
- **Dependencies**:
    - Blocks: [C034]
    - Blocked by: [R038, S021, S027]

## Description

**What**: Service for price_lists management (product pricing, discounts, effective dates).

**Why**: Manages product pricing for sales calculations and invoicing.

**Context**: Application Layer. Validates product/packaging via S021/S027.

## Acceptance Criteria

- [ ] **AC1**: Create price list with product/packaging validation
- [ ] **AC2**: Get active price for product (by effective date)
- [ ] **AC3**: Price history tracking
- [ ] **AC4**: Bulk price updates
- [ ] **AC5**: Unit tests ≥85% coverage

## Technical Notes

- Effective dates for price changes
- Price history preserved (soft deletes)

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
