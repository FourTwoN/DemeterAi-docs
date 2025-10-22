# DB026 Mini-Plan: Classifications Model

**Task**: Implement Classifications model (product + packaging + size classification results)
**Complexity**: 1 story point (SIMPLE)
**Estimated Time**: 45-60 minutes
**Priority**: CRITICAL (blocks DB013 Detections, DB014 Estimations)

---

## Strategic Context

**What**: Classifications table stores ML model predictions for detected/estimated plants
**Why**: Links ML predictions (confidence scores) to actual entities (product, packaging, size)
**Where in Pipeline**:

```
Photo → YOLO Segmentation → YOLO Detection → Classifications → Detections/Estimations
```

**Key Insight**: This is the "ML prediction cache" - stores model outputs so we don't re-run
inference

---

## Technical Approach

### 1. Model Structure (15 min)

**File**: `app/models/classification.py`

```python
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base

class Classification(Base):
    __tablename__ = 'classifications'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys (links to actual entities)
    product_id = Column(
        Integer,
        ForeignKey('products.id', ondelete='CASCADE'),
        nullable=False
    )
    product_size_id = Column(
        Integer,
        ForeignKey('product_sizes.id', ondelete='SET NULL'),
        nullable=True  # May not classify size
    )
    packaging_catalog_id = Column(
        Integer,
        ForeignKey('packaging_catalog.id', ondelete='SET NULL'),
        nullable=True  # May not have packaging
    )

    # ML model confidence scores (0.0-1.0)
    product_conf = Column(Numeric(4, 3), nullable=False)  # e.g., 0.952
    packaging_conf = Column(Numeric(4, 3), nullable=True)  # nullable if no packaging
    product_size_conf = Column(Numeric(4, 3), nullable=True)  # nullable if size not classified

    # Model versioning (for A/B testing, rollbacks)
    model_version = Column(String(50), nullable=False)  # e.g., "yolo11n-v1.2.0"

    # Human-readable label (for debugging)
    name = Column(String(255), nullable=False)  # e.g., "Echeveria elegans + 10cm pot"
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship('Product', back_populates='classifications')
    product_size = relationship('ProductSize', back_populates='classifications')
    packaging = relationship('PackagingCatalog', back_populates='classifications')
    detections = relationship('Detection', back_populates='classification')
    estimations = relationship('Estimation', back_populates='classification')
```

**Key Decisions**:

- `Numeric(4,3)` for confidence: 0.000 to 0.999 (3 decimal precision)
- `model_version`: Enables ML model A/B testing and rollback
- `name`: Human-readable label for quick debugging
- CASCADE on product_id: If product deleted, classification invalid
- SET NULL on size/packaging: Optional fields

---

### 2. Migration (10 min)

**File**: `alembic/versions/XXXXX_create_classifications_table.py`

```python
def upgrade():
    op.create_table(
        'classifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_size_id', sa.Integer(), nullable=True),
        sa.Column('packaging_catalog_id', sa.Integer(), nullable=True),
        sa.Column('product_conf', sa.Numeric(4, 3), nullable=False),
        sa.Column('packaging_conf', sa.Numeric(4, 3), nullable=True),
        sa.Column('product_size_conf', sa.Numeric(4, 3), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_size_id'], ['product_sizes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['packaging_catalog_id'], ['packaging_catalog.id'], ondelete='SET NULL'),
    )

    # Indexes for common queries
    op.create_index('idx_classifications_product', 'classifications', ['product_id'])
    op.create_index('idx_classifications_model_version', 'classifications', ['model_version'])
    op.create_index('idx_classifications_created_at', 'classifications', ['created_at'], desc=True)

def downgrade():
    op.drop_index('idx_classifications_created_at')
    op.drop_index('idx_classifications_model_version')
    op.drop_index('idx_classifications_product')
    op.drop_table('classifications')
```

**Indexes Rationale**:

- `product_id`: Most common query ("show all classifications for product X")
- `model_version`: For A/B test analysis, rollback queries
- `created_at DESC`: Recent classifications first (time-series queries)

---

### 3. Testing Strategy (20 min)

#### Unit Tests (`tests/unit/models/test_classification.py`)

**Test Cases** (15 tests):

1. `test_classification_creation` - Basic instantiation
2. `test_confidence_score_validation` - 0.0 ≤ conf ≤ 1.0
3. `test_nullable_fields` - size_id, packaging_id can be NULL
4. `test_model_version_format` - Semantic versioning pattern
5. `test_name_generation` - Auto-generate from product + packaging
6. `test_product_relationship` - Bidirectional FK to Product
7. `test_cascade_delete_on_product` - Delete product → delete classification
8. `test_set_null_on_packaging_delete` - Delete packaging → SET NULL
9. `test_numeric_precision` - Confidence stored with 3 decimals
10. `test_created_at_timestamp` - Auto-generated timestamp
11. `test_multiple_classifications_per_product` - Same product, different versions
12. `test_confidence_edge_cases` - 0.0, 1.0, 0.999
13. `test_description_optional` - Can be NULL
14. `test_repr_method` - Human-readable string representation
15. `test_model_version_indexing` - Query by version

#### Integration Tests (`tests/integration/test_classification_db.py`)

**Test Cases** (8 tests):

1. `test_insert_classification_with_all_fields`
2. `test_insert_classification_without_packaging`
3. `test_query_by_model_version`
4. `test_cascade_delete_product`
5. `test_set_null_on_packaging_delete`
6. `test_query_by_confidence_threshold` - WHERE product_conf > 0.8
7. `test_classification_count_per_product`
8. `test_created_at_ordering` - Recent first

**Coverage Target**: ≥85% (simple model, high coverage expected)

---

### 4. Validation Logic (10 min)

**Add to model class**:

```python
from sqlalchemy.orm import validates

@validates('product_conf', 'packaging_conf', 'product_size_conf')
def validate_confidence(self, key, value):
    """Confidence must be between 0.0 and 1.0"""
    if value is not None:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"{key} must be between 0.0 and 1.0, got {value}")
    return value

@validates('model_version')
def validate_model_version(self, key, value):
    """Model version should follow semantic versioning"""
    import re
    # Pattern: yolo11n-v1.2.0 or resnet50-v2.0.1
    pattern = r'^[a-z0-9]+-v\d+\.\d+\.\d+$'
    if not re.match(pattern, value):
        raise ValueError(
            f"model_version must follow pattern 'modelname-vX.Y.Z', got {value}"
        )
    return value
```

---

## Execution Checklist

### Python Expert Tasks (30 min)

- [ ] Create `app/models/classification.py` with complete model
- [ ] Add confidence validation (0.0-1.0 bounds)
- [ ] Add model_version validation (semantic versioning)
- [ ] Create Alembic migration with indexes
- [ ] Add relationships to Product, ProductSize, PackagingCatalog
- [ ] Test migration (upgrade + downgrade)
- [ ] Run pre-commit hooks (ruff, mypy)

### Testing Expert Tasks (25 min, PARALLEL)

- [ ] Write 15 unit tests in `test_classification.py`
- [ ] Write 8 integration tests in `test_classification_db.py`
- [ ] Test confidence validation edge cases
- [ ] Test CASCADE and SET NULL behaviors
- [ ] Test model version format validation
- [ ] Verify coverage ≥85%
- [ ] All tests pass

### Team Leader Review (5 min)

- [ ] Verify ERD alignment (database.mmd line 290-302)
- [ ] Check confidence precision (3 decimals)
- [ ] Validate indexes (product_id, model_version, created_at)
- [ ] Approve and merge

---

## Known Edge Cases

1. **Same product, multiple classifications**
    - Scenario: ML model upgraded from v1.0 to v2.0
    - Solution: Allow multiple classifications per product (no unique constraint)
    - Query: `SELECT * WHERE model_version = 'yolo11n-v2.0.0'`

2. **Confidence = 0.0 (valid but suspicious)**
    - Scenario: Model predicts product but confidence is 0.0
    - Solution: Allow 0.0 (valid range), but log warning in service layer
    - Test: Ensure 0.0 is accepted by validation

3. **Orphaned classifications**
    - Scenario: Product deleted, classification should be deleted too
    - Solution: CASCADE delete on product_id FK
    - Test: Delete product → verify classification gone

4. **NULL packaging but non-NULL packaging_conf**
    - Scenario: Model predicted packaging confidence but no packaging_catalog_id
    - Solution: Allow this (model may predict confidence even if mapping fails)
    - Validation: No constraint between packaging_id and packaging_conf

---

## Performance Expectations

- Insert: <5ms (simple table, indexed FKs)
- Query by product_id: <10ms (indexed)
- Query by model_version: <20ms (indexed)
- Query with confidence filter: <30ms (sequential scan on confidence column)

**Future optimization**: If confidence queries become common, add partial index:

```sql
CREATE INDEX idx_high_confidence ON classifications(product_conf)
WHERE product_conf > 0.8;
```

---

## Definition of Done

- [ ] Model created in `app/models/classification.py`
- [ ] Alembic migration created and tested
- [ ] Indexes added (product_id, model_version, created_at)
- [ ] Confidence validation working (0.0-1.0)
- [ ] Model version validation working (semantic versioning pattern)
- [ ] 15 unit tests pass
- [ ] 8 integration tests pass
- [ ] Coverage ≥85%
- [ ] Pre-commit hooks pass (17/17)
- [ ] Relationships to Product, ProductSize, PackagingCatalog working
- [ ] CASCADE and SET NULL behaviors tested
- [ ] Code review approved

---

**Estimated Time**: 45-60 minutes
**Actual Time**: _____ (fill after completion)

**Ready to Execute**: YES - DB017 (Products) is dependency, will be complete soon
**Blocks**: DB013 (Detections), DB014 (Estimations) - HIGH PRIORITY unblock
