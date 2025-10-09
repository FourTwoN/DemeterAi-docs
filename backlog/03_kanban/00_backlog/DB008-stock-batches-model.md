# [DB008] Stock batches model - aggregated state

## Metadata
- **Epic**: epic-002-database-models
- **Sprint**: Sprint-01
- **Priority**: high
- **Complexity**: 2 points
- **Dependencies**: Blocks [R008]

## Description
Stock batches model - aggregated state. SQLAlchemy model following Clean Architecture patterns.

## Acceptance Criteria
- [ ] Model created in app/models/stock-batches.py
- [ ] All columns defined with correct types
- [ ] Relationships configured with lazy loading strategy
- [ ] Alembic migration created
- [ ] Indexes added for foreign keys
- [ ] Unit tests ≥75% coverage

## Implementation Notes
See database/database.mmd ERD for complete schema.

## Testing
- Test model creation
- Test relationships
- Test constraints

## Handover
Standard SQLAlchemy model. Follow DB011-DB014 patterns.

---
**Card Created**: 2025-10-09
**Points**: 2
