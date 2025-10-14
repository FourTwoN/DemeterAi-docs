# [DB028] Users model with role-based access

## Metadata
- **Epic**: epic-002-database-models
- **Sprint**: Sprint-01
- **Priority**: high
- **Complexity**: 1 points
- **Dependencies**: Blocks [AUTH003]

## Description
Users model with role-based access. SQLAlchemy model following Clean Architecture patterns.

## Acceptance Criteria
- [ ] Model created in app/models/users.py
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

## Scrum Master → Team Leader Delegation (2025-10-14 14:30)

**Status**: DELEGATED - Wave 2 Launch (Task 1 of 3)
**Assigned to**: Team Leader
**Priority**: CRITICAL (blocks DB007 StockMovements.user_id, DB012 PhotoProcessingSessions)
**Epic**: epic-002 (Database Models)
**Sprint**: Sprint-01 (FINAL PUSH - 4pts remaining)

**Strategic Context**:
This is the FIRST task in Wave 2 sequential execution. Auth foundation for the entire application. Simple model (45-60 min), standard auth pattern.

**Execution Plan**:
- Mini-Plan: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/DB028-MINI-PLAN.md`
- Time: 45-60 minutes
- Spawn: Python Expert + Testing Expert immediately
- Pattern: Email + bcrypt password + role enum (4 levels)
- Seed Data: Default admin user (admin@demeter.ai / admin123)

**Resources**:
- ERD: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 195-206)
- Pattern: DB017 Products (97% coverage standard - MAINTAIN THIS)
- Template: Standard SQLAlchemy model with validators
- Migration: user_role_enum + indexes (email unique, role, active)

**Quality Gates** (NON-NEGOTIABLE):
- [ ] 14 unit tests + 10 integration tests (as per mini-plan)
- [ ] Coverage ≥85% (higher than 75% in acceptance criteria)
- [ ] Email validation (regex + lowercase normalization)
- [ ] Password hash validation (bcrypt format check)
- [ ] Seed admin user inserted and verified
- [ ] Pre-commit hooks pass (17/17)

**Success Criteria**:
- All acceptance criteria checked ✅
- Coverage ≥85%
- Migration tested (upgrade + downgrade)
- Soft delete pattern implemented (active=False)
- Security reminder documented (change admin password in production)

**Next in Queue**: DB026 Classifications (after DB028 DONE)

---
**Card Created**: 2025-10-09
**Points**: 1
**Wave 2 Started**: 2025-10-14 14:30

---

## Team Leader Delegation (2025-10-14 14:35)

### Task Overview
- **Card**: DB028 - Users Model (Auth + Role Management)
- **Epic**: epic-002 (Database Models)
- **Sprint**: Sprint-01 (FINAL PUSH)
- **Priority**: CRITICAL - Auth foundation
- **Complexity**: 1 point (45-60 min)

### Architecture
**Layer**: Data Layer (Model)
**Pattern**: SQLAlchemy ORM with validators
**Dependencies**: None (independent model)
**Blocks**: DB007 (StockMovements.user_id FK), DB012 (PhotoProcessingSessions.validated_by_user_id FK)

### Files to Create
- [ ] `app/models/user.py` (~110 lines)
- [ ] `alembic/versions/XXXXX_create_users_table.py` (~50 lines)
- [ ] `tests/unit/models/test_user.py` (~300 lines - 14 tests)
- [ ] `tests/integration/test_user_db.py` (~250 lines - 10 tests)

### Database Schema (ERD Lines 195-206)
**Table**: `users`
**Columns**:
- `id` INT PK (autoincrement)
- `email` VARCHAR UK (unique, indexed)
- `password_hash` VARCHAR (bcrypt format)
- `first_name` VARCHAR
- `last_name` VARCHAR
- `role` ENUM (admin|supervisor|worker|viewer) - indexed
- `active` BOOLEAN (default true) - indexed
- `last_login` TIMESTAMP (nullable)
- `created_at` TIMESTAMP
- `updated_at` TIMESTAMP

**Relationships**:
- `stock_movements` → StockMovement.user_id
- `photo_sessions_validated` → PhotoProcessingSession.validated_by_user_id
- `uploaded_images` → S3Image.uploaded_by_user_id
- `captured_samples` → ProductSampleImage.captured_by_user_id

### Implementation Strategy

#### Python Expert Tasks (25 min)
1. Create `app/models/user.py`:
   - SQLAlchemy model with all columns
   - Email validator (regex + lowercase normalization)
   - Password hash validator (bcrypt format: $2b$, 60 chars)
   - Computed property `full_name`
   - Relationships to 4 tables
2. Create Alembic migration:
   - Create `user_role_enum` type
   - Create `users` table
   - Add 3 indexes (email unique, role, active)
   - Seed default admin user (admin@demeter.ai / admin123 hashed)
3. Test migration (upgrade + downgrade)
4. Run pre-commit hooks

#### Testing Expert Tasks (20 min, PARALLEL)
1. Unit tests (14 tests):
   - Email validation (valid/invalid formats)
   - Email normalization (uppercase → lowercase)
   - Password hash validation (bcrypt format)
   - Role enum (4 values)
   - Defaults (role=worker, active=true)
   - Full name property
   - Repr method
   - Relationships
2. Integration tests (10 tests):
   - Insert with all/minimal fields
   - Query by email/role/active
   - Unique email constraint (DB-level)
   - Update last_login
   - Soft delete (active=False)
   - Seed admin user exists
   - Case-insensitive email search
3. Verify coverage ≥85%

### Acceptance Criteria (From Task Card)
- [ ] Model created in app/models/users.py
- [ ] All columns defined with correct types
- [ ] Relationships configured with lazy loading strategy
- [ ] Alembic migration created
- [ ] Indexes added for foreign keys
- [ ] Unit tests ≥75% coverage

### Enhanced Quality Gates (Scrum Master Requirements)
- [ ] 14 unit tests + 10 integration tests
- [ ] Coverage ≥85% (NOT just 75%)
- [ ] Email validation (regex + lowercase)
- [ ] Password hash validation (bcrypt check)
- [ ] Seed admin user verified
- [ ] Pre-commit hooks pass (17/17)
- [ ] Soft delete pattern tested
- [ ] Security reminder documented

### Performance Expectations
- Insert: <5ms
- Query by email: <3ms (unique index)
- Query by role: <10ms (indexed)
- Update last_login: <3ms

### Next Steps
1. ✅ Task already in 02_in-progress/ (Scrum Master)
2. NOW: Spawn Python Expert + Testing Expert (PARALLEL)
3. Monitor progress (check back in 30 min)
4. Review and approve when complete
5. Invoke /complete-task DB028

---

### Delegation to Specialists

#### TO: Python Expert (START NOW)
**Task**: Implement Users model with auth validators
**File**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB028-users-model.md`
**Mini-Plan**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/DB028-MINI-PLAN.md` (lines 25-112 for model code)
**ERD Reference**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 195-206)

**Key Requirements**:
- Email validator: Regex pattern + lowercase normalization
- Password hash validator: Check bcrypt format ($2b$, 60 chars)
- user_role_enum: admin, supervisor, worker, viewer
- Seed data: Default admin user (see mini-plan line 154-164)
- Relationships: 4 tables (StockMovement, PhotoProcessingSession, S3Image, ProductSampleImage)

**Pattern**: Follow DB017 Products model (97% coverage standard)
**Time**: 25 minutes
**Start immediately** (parallel with Testing Expert)

---

#### TO: Testing Expert (START NOW)
**Task**: Write comprehensive tests for Users model
**File**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB028-users-model.md`
**Mini-Plan**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/DB028-MINI-PLAN.md` (lines 185-219 for test strategy)

**Test Requirements**:
- 14 unit tests (email, password, role, defaults, relationships)
- 10 integration tests (insert, query, constraints, seed user)
- Coverage target: ≥85%
- Test email normalization (User@Example.Com → user@example.com)
- Test bcrypt validation (reject non-bcrypt strings)
- Test soft delete (active=False instead of DELETE)

**Pattern**: Follow DB017 test structure
**Time**: 20 minutes
**Start immediately** (parallel with Python Expert)

---

**Team Leader Status**: MONITORING (will check progress in 30 min)
