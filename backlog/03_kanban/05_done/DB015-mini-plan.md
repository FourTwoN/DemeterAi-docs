# DB015 Mini-Plan: ProductCategories Model - Product Taxonomy ROOT

## Overview

**Task**: DB015 - ProductCategories Model
**Complexity**: S (2 story points)
**Estimated Time**: 45-60 minutes
**Pattern**: Reference catalog with seed data (like DB005, DB018, DB019)

**Goal**: Create ROOT taxonomy table for Product Catalog hierarchy (Category → Family → Product)

---

## Step-by-Step Implementation Plan

### Phase 1: Model Creation (15 minutes)

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/product_category.py`

**Tasks**:
1. Create ProductCategory SQLAlchemy model
2. Define columns:
   - product_category_id (Integer, PK, autoincrement)
   - code (String(50), UK, index)
   - name (String(200), nullable=False)
   - description (Text, nullable=True)
   - created_at (DateTime with timezone, server_default=func.now())
   - updated_at (DateTime with timezone, onupdate=func.now())

3. Add code validation:
   ```python
   @validates('code')
   def validate_code(self, key, code):
       """Validate code: uppercase, alphanumeric + underscores, 3-50 chars."""
       if not code:
           raise ValueError("code cannot be empty")

       code = code.upper()

       if not re.match(r'^[A-Z0-9_]+$', code):
           raise ValueError(f"code must be uppercase alphanumeric + underscores: {code}")

       if not (3 <= len(code) <= 50):
           raise ValueError(f"code must be 3-50 characters: {code} ({len(code)} chars)")

       return code
   ```

4. Add relationships (COMMENT OUT until models ready):
   ```python
   # Relationships (COMMENT OUT - models not ready yet)
   # product_families = relationship('ProductFamily', back_populates='category')
   # price_lists = relationship('PriceList', back_populates='category')
   ```

5. Add `__repr__()` method:
   ```python
   def __repr__(self) -> str:
       return f"<ProductCategory(id={self.product_category_id}, code={self.code}, name={self.name})>"
   ```

6. Add comprehensive docstrings with examples

**Template**: Follow `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py` or `product_state.py`

---

### Phase 2: Migration Creation (10 minutes)

**File**: `/home/lucasg/proyectos/DemeterDocs/alembic/versions/XXXX_create_product_categories_table.py`

**Command**:
```bash
cd /home/lucasg/proyectos/DemeterDocs
alembic revision -m "create product_categories table"
```

**Migration Tasks**:
1. Create table with columns
2. Add UK constraint on code
3. Add B-tree index on code
4. Add CHECK constraint (code length 3-50, uppercase)
5. Insert seed data (8 categories):

```python
# Seed data
op.execute("""
    INSERT INTO product_categories (code, name, description) VALUES
    ('CACTUS', 'Cactus', 'Cacti family (Cactaceae) - succulent plants with spines'),
    ('SUCCULENT', 'Succulent', 'Non-cactus succulents - thick fleshy leaves, drought-tolerant'),
    ('BROMELIAD', 'Bromeliad', 'Bromeliaceae family - epiphytic tropical plants'),
    ('CARNIVOROUS', 'Carnivorous Plant', 'Insectivorous plants (Venus flytrap, pitcher plants, etc.)'),
    ('ORCHID', 'Orchid', 'Orchidaceae family - epiphytic flowering plants'),
    ('FERN', 'Fern', 'Ferns and fern allies - non-flowering vascular plants'),
    ('TROPICAL', 'Tropical Plant', 'General tropical foliage plants (Monstera, Philodendron, etc.)'),
    ('HERB', 'Herb', 'Culinary and medicinal herbs (basil, mint, rosemary, etc.)');
""")
```

6. Add downgrade() function (DROP TABLE CASCADE)

**Template**: Follow `alembic/versions/3xy8k1m9n4pq_create_product_states_table.py`

---

### Phase 3: Update Model Exports (2 minutes)

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/__init__.py`

**Tasks**:
1. Add ProductCategory import
2. Add ProductCategory to `__all__` list
3. Update docstring

```python
from app.models.product_category import ProductCategory

__all__ = [
    # ... existing exports ...
    "ProductCategory",
]
```

---

### Phase 4: Unit Tests (15 minutes)

**File**: `/home/lucasg/proyectos/DemeterDocs/tests/unit/models/test_product_category.py`

**Test Categories** (15-20 tests):

1. **Code Validation Tests** (8 tests):
   - Valid codes (CACTUS, SUCCULENT, ORCHID_12)
   - Auto-uppercase (cactus → CACTUS)
   - Invalid: empty string
   - Invalid: too short (AB)
   - Invalid: too long (51+ chars)
   - Invalid: special characters (@, #, -)
   - Invalid: lowercase (after setting)

2. **Basic CRUD Tests** (3 tests):
   - Create category
   - Update category
   - Delete category

3. **Field Constraint Tests** (3 tests):
   - name required (cannot be None)
   - description nullable (can be None)
   - timestamps auto-set (created_at, updated_at)

4. **__repr__ Test** (1 test):
   - Verify format: `<ProductCategory(id=1, code=CACTUS, name=Cactus)>`

5. **Uniqueness Test** (1 test):
   - Cannot create two categories with same code

**Template**: Follow `tests/unit/models/test_product_state.py`

---

### Phase 5: Integration Tests (10 minutes)

**File**: `/home/lucasg/proyectos/DemeterDocs/tests/integration/models/test_product_category.py`

**Test Categories** (8-10 tests):

1. **Seed Data Tests** (2 tests):
   - Verify 8 categories loaded
   - Verify codes: CACTUS, SUCCULENT, BROMELIAD, CARNIVOROUS, ORCHID, FERN, TROPICAL, HERB

2. **DB Constraint Tests** (2 tests):
   - Code uniqueness at DB level (IntegrityError)
   - CHECK constraint (code length, uppercase)

3. **Query Tests** (4 tests):
   - ORDER BY name
   - Filter by code
   - Count all categories
   - Query by partial name (LIKE '%Plant%')

**Template**: Follow `tests/integration/models/test_product_state.py`

---

### Phase 6: Quality Gates (5 minutes)

**Commands**:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# 1. Mypy strict mode
mypy app/models/product_category.py --strict

# 2. Ruff linting
ruff check app/models/product_category.py

# 3. Test model import
python -c "from app.models.product_category import ProductCategory; print('Import OK')"

# 4. Run unit tests
pytest tests/unit/models/test_product_category.py -v

# 5. Run migration upgrade
alembic upgrade head

# 6. Run integration tests (if DB available)
pytest tests/integration/models/test_product_category.py -v

# 7. Pre-commit hooks
git add .
pre-commit run --all-files
```

---

## Success Criteria

**All 7 Acceptance Criteria Met**:
- [x] AC1: Model created in `app/models/product_category.py`
- [x] AC2: Code validation (uppercase, alphanumeric + underscores, 3-50 chars)
- [x] AC3: Seed data migration (8 categories)
- [x] AC4: Indexes on code (UK)
- [x] AC5: Relationships to ProductFamily (COMMENTED OUT)
- [x] AC6: Alembic migration tested (upgrade + downgrade)
- [x] AC7: Unit tests ≥75% coverage

**Quality Gates**:
- Mypy: 0 errors (strict mode)
- Ruff: 0 violations
- Unit tests: 15-20 passing (≥75% coverage)
- Integration tests: 8-10 passing (≥70% coverage)
- Pre-commit hooks: All passed

---

## Expected Deliverables

1. **Model**: `app/models/product_category.py` (~180 lines)
2. **Migration**: `alembic/versions/XXXX_create_product_categories.py` (~130 lines)
3. **Unit Tests**: `tests/unit/models/test_product_category.py` (~400 lines, 15-20 tests)
4. **Integration Tests**: `tests/integration/models/test_product_category.py` (~300 lines, 8-10 tests)
5. **Updated Exports**: `app/models/__init__.py` (1 line added)

**Total Lines**: ~1,010 lines of production code + test code

---

## Git Commit

**Commit Message**:
```bash
git add app/models/product_category.py \
        alembic/versions/XXXX_create_product_categories.py \
        app/models/__init__.py \
        tests/unit/models/test_product_category.py \
        tests/integration/models/test_product_category.py

git commit -m "feat(models): implement ProductCategory ROOT taxonomy with seed data (DB015)

- Create ProductCategory model with code validation
- Add 8 plant categories seed data (CACTUS, SUCCULENT, etc.)
- Implement unit tests (15-20 tests, ≥75% coverage)
- Implement integration tests (8-10 tests, ≥70% coverage)
- UK constraint on code, B-tree index
- Relationships COMMENTED OUT (ProductFamily, PriceList not ready)

Unblocks:
- DB016: ProductFamilies (category_id FK)
- DB017: Products (indirect via DB016)
- DB027: PriceList (category_id FK)

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Next Steps After Completion

1. **Mark DB015 as COMPLETE** in `05_done/`
2. **Update DATABASE_CARDS_STATUS.md** (2 points complete)
3. **Delegate DB016** (ProductFamilies) to Team Leader immediately
4. **Track progress** through Kanban pipeline

---

## Resources

**Templates**:
- Model: `/home/lucasg/proyectos/DemeterDocs/app/models/product_state.py`
- Migration: `/home/lucasg/proyectos/DemeterDocs/alembic/versions/3xy8k1m9n4pq_create_product_states_table.py`
- Unit Tests: `/home/lucasg/proyectos/DemeterDocs/tests/unit/models/test_product_state.py`
- Integration Tests: `/home/lucasg/proyectos/DemeterDocs/tests/integration/models/test_product_state.py`

**Documentation**:
- ERD: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 75-80)
- Engineering Plan: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md`

---

**Mini-Plan Created**: 2025-10-14 18:00
**Estimated Time**: 45-60 minutes (2 story points)
**Pattern**: Reference catalog with seed data (proven with DB005, DB018, DB019)
**Confidence**: HIGH (3 similar models completed in 30 minutes combined)
