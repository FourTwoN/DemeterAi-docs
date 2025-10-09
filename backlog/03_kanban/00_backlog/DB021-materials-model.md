# [DB021] Materials model (plastic, clay, etc)

## Metadata
- **Epic**: epic-002-database-models
- **Sprint**: Sprint-01
- **Priority**: high
- **Complexity**: 1 points
- **Dependencies**: Blocks [DB023]

## Description
Materials model (plastic, clay, etc). SQLAlchemy model following Clean Architecture patterns.

## Acceptance Criteria
- [ ] Model created in app/models/materials.py
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
**Points**: 1
