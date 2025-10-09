# [DB005] StorageBinTypes Model - Container Type Catalog

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `high` (reference data for DB004)
- **Complexity**: S (1 story point)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB004, DB025]
  - Blocked by**: [F007-alembic-setup]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd

## Description

Create the `storage_bin_types` SQLAlchemy model - a catalog/reference table defining container types (plug trays, boxes, segments, pots) with dimensions and capacity.

**What**: SQLAlchemy model for `storage_bin_types` table:
- Reference data for container types (plug_tray_288, seedling_box_standard, segmento_rectangular, etc.)
- Dimensions: length_cm, width_cm, height_cm
- Capacity: rows × columns for grid types (plugs), or total capacity for boxes
- Category enum: plug, seedling_tray, box, segment, pot

**Why**:
- **Capacity planning**: Know max plants per bin type
- **Density estimation**: ML uses bin type + area to estimate plant count
- **Standardization**: Consistent container definitions across system
- **Reporting**: Group inventory by bin type

**Context**: This is reference/catalog data. Loaded via seed migration. StorageBins FK to this table.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/storage_bin_type.py` with category enum, dimensions (nullable), capacity fields, grid flag
- [ ] **AC2**: Category enum created (`CREATE TYPE bin_category_enum AS ENUM ('plug', 'seedling_tray', 'box', 'segment', 'pot')`)
- [ ] **AC3**: Code validation (uppercase, alphanumeric, 3-50 chars, unique)
- [ ] **AC4**: CHECK constraint: if is_grid=true, then rows/columns must be NOT NULL
- [ ] **AC5**: Seed data migration with common bin types (plug_tray_288, plug_tray_128, seedling_box_standard, etc.)
- [ ] **AC6**: Indexes on code, category
- [ ] **AC7**: Alembic migration with seed data

## Technical Implementation Notes

### Model Signature

```python
class StorageBinType(Base):
    __tablename__ = 'storage_bin_types'

    bin_type_id = Column(Integer, PK, autoincrement=True)
    code = Column(String(50), UK, index=True)
    name = Column(String(200), nullable=False)
    category = Column(Enum('plug', 'seedling_tray', 'box', 'segment', 'pot'), index=True)
    description = Column(Text, nullable=True)

    # Dimensions (nullable - may not be relevant for all types)
    rows = Column(Integer, nullable=True)
    columns = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)  # Total capacity (may differ from rows×columns)

    length_cm = Column(Numeric(6,2), nullable=True)
    width_cm = Column(Numeric(6,2), nullable=True)
    height_cm = Column(Numeric(6,2), nullable=True)

    is_grid = Column(Boolean, default=False)  # True for plug trays (rows×columns grid)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    storage_bins = relationship('StorageBin', back_populates='storage_bin_type')
    density_parameters = relationship('DensityParameter', back_populates='storage_bin_type')
```

### Seed Data Examples

```sql
-- Common bin types (loaded via migration)
INSERT INTO storage_bin_types (code, name, category, rows, columns, capacity, is_grid) VALUES
('PLUG_TRAY_288', '288-Cell Plug Tray', 'plug', 18, 16, 288, true),
('PLUG_TRAY_128', '128-Cell Plug Tray', 'plug', 8, 16, 128, true),
('PLUG_TRAY_72', '72-Cell Plug Tray', 'plug', 6, 12, 72, true),
('SEEDLING_BOX_STD', 'Standard Seedling Box', 'seedling_tray', NULL, NULL, 50, false),
('SEGMENTO_RECT', 'Rectangular Segment', 'segment', NULL, NULL, NULL, false),
('CAJON_GRANDE', 'Large Box', 'box', NULL, NULL, 100, false);
```

### CHECK Constraint for Grid Types

```sql
-- If is_grid=true, rows and columns must be NOT NULL
ALTER TABLE storage_bin_types
ADD CONSTRAINT check_grid_has_rows_columns
CHECK (
    (is_grid = false) OR
    (is_grid = true AND rows IS NOT NULL AND columns IS NOT NULL)
);
```

### Testing Requirements

**Unit Tests** (`tests/models/test_storage_bin_type.py`):
- Category enum validation
- Code validation (uppercase, alphanumeric)
- Grid constraint (is_grid=true requires rows/columns)

**Integration Tests** (`tests/integration/test_storage_bin_type.py`):
- Seed data loaded correctly
- RESTRICT delete (cannot delete if storage_bins reference it)
- Relationship to storage_bins

**Coverage Target**: ≥75%

### Performance Expectations
- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- Retrieve all: <10ms (small reference table, <100 rows expected)

## Handover Briefing

**Context**: Reference/catalog table. Defines container types used throughout the system. Loaded via seed migration, rarely modified.

**Key decisions**:
1. **Category enum**: 5 types (plug, seedling_tray, box, segment, pot)
2. **Nullable dimensions**: Not all types have dimensions (segments detected by ML don't have predefined size)
3. **is_grid flag**: True for plug trays (grid-based capacity calculation)
4. **CHECK constraint**: Grid types must have rows/columns
5. **Seed data**: Common types preloaded in migration

**Next steps**: DB004 (StorageBins FK to this), DB025 (DensityParameters uses bin_type for ML estimation)

## Definition of Done Checklist

- [ ] Model code written
- [ ] Category enum created
- [ ] CHECK constraint for grid types
- [ ] Code validation working
- [ ] Seed data migration created
- [ ] Unit tests ≥75% coverage
- [ ] Integration tests pass
- [ ] Alembic migration tested
- [ ] PR reviewed and approved

## Time Tracking
- **Estimated**: 1 story point
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
