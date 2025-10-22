# DB028 Mini-Plan: Users Model (Auth + Role Management)

**Task**: Implement Users model with authentication and role-based access control
**Complexity**: 1 story point (SIMPLE - standard auth pattern)
**Estimated Time**: 45-60 minutes
**Priority**: CRITICAL (blocks DB007 StockMovements.user_id, DB012 PhotoProcessingSessions)

---

## Strategic Context

**What**: Users table stores authentication credentials and role-based permissions
**Why**: Foundation for audit trails, user actions, and access control
**Where in System**:

```
User Auth → JWT Token → API Request → User ID → Audit Trail (stock_movements, photo_sessions)
```

**Key Insight**: This is NOT a full auth system (no OAuth, social login) - just basic user
management for internal staff

---

## Technical Approach

### 1. Model Structure (15 min)

**File**: `app/models/user.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship, validates
from app.models.base import Base
import re

class User(Base):
    __tablename__ = 'users'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    # Authorization (role-based access control)
    role = Column(
        Enum('admin', 'supervisor', 'worker', 'viewer', name='user_role_enum'),
        nullable=False,
        default='worker',
        index=True
    )

    # Account status
    active = Column(Boolean, nullable=False, default=True, index=True)

    # Activity tracking
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (bidirectional)
    stock_movements = relationship(
        'StockMovement',
        back_populates='user',
        foreign_keys='StockMovement.user_id'
    )
    photo_sessions_validated = relationship(
        'PhotoProcessingSession',
        back_populates='validated_by',
        foreign_keys='PhotoProcessingSession.validated_by_user_id'
    )
    uploaded_images = relationship(
        'S3Image',
        back_populates='uploaded_by',
        foreign_keys='S3Image.uploaded_by_user_id'
    )
    captured_samples = relationship(
        'ProductSampleImage',
        back_populates='captured_by',
        foreign_keys='ProductSampleImage.captured_by_user_id'
    )

    @validates('email')
    def validate_email(self, key, value):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        return value.lower()  # Normalize to lowercase

    @validates('password_hash')
    def validate_password_hash(self, key, value):
        """Validate bcrypt hash format"""
        # Bcrypt hash: $2b$12$... (60 chars)
        if not value.startswith('$2b$') or len(value) != 60:
            raise ValueError("password_hash must be a valid bcrypt hash")
        return value

    @property
    def full_name(self):
        """Computed property for display"""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User {self.id} - {self.email} ({self.role})>"
```

**Key Decisions**:

- `email` unique + indexed: Primary login identifier
- `password_hash`: bcrypt format (60 chars, $2b$ prefix)
- `role` enum: 4 levels (admin > supervisor > worker > viewer)
- `active` flag: Soft delete (deactivate instead of delete)
- `last_login`: Track activity for security audits

---

### 2. Migration (10 min)

**File**: `alembic/versions/XXXXX_create_users_table.py`

```python
def upgrade():
    # Create enum type
    op.execute("""
        CREATE TYPE user_role_enum AS ENUM ('admin', 'supervisor', 'worker', 'viewer');
    """)

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum(name='user_role_enum'), nullable=False, default='worker'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Indexes
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_active', 'users', ['active'])

    # Seed data: Default admin user
    op.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, role, active)
        VALUES (
            'admin@demeter.ai',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6',  -- "admin123"
            'System',
            'Administrator',
            'admin',
            true
        );
    """)

def downgrade():
    op.drop_index('idx_users_active')
    op.drop_index('idx_users_role')
    op.drop_index('idx_users_email')
    op.drop_table('users')
    op.execute("DROP TYPE user_role_enum")
```

**Seed Data**:

- Default admin: `admin@demeter.ai` / `admin123` (bcrypt hashed)
- **IMPORTANT**: Change password in production!

**Indexes Rationale**:

- `email` unique: Login lookup
- `role`: Filter by role (admin actions, reports)
- `active`: Filter active users only

---

### 3. Testing Strategy (20 min)

#### Unit Tests (`tests/unit/models/test_user.py`)

**Test Cases** (14 tests):

1. `test_user_creation` - Basic instantiation
2. `test_email_validation_valid` - Valid email formats
3. `test_email_validation_invalid` - Invalid email formats
4. `test_email_normalized_lowercase` - "User@Example.Com" → "user@example.com"
5. `test_password_hash_validation_valid` - Valid bcrypt hash
6. `test_password_hash_validation_invalid` - Non-bcrypt string
7. `test_role_enum_values` - admin, supervisor, worker, viewer
8. `test_role_default_worker` - Default role is 'worker'
9. `test_active_default_true` - Default active = True
10. `test_full_name_property` - "John" + "Doe" = "John Doe"
11. `test_last_login_nullable` - Can be NULL
12. `test_repr_method` - Human-readable string
13. `test_unique_email_constraint` - Duplicate email fails
14. `test_relationships` - stock_movements, photo_sessions, images

#### Integration Tests (`tests/integration/test_user_db.py`)

**Test Cases** (10 tests):

1. `test_insert_user_with_all_fields`
2. `test_insert_user_with_minimal_fields`
3. `test_query_by_email`
4. `test_query_by_role`
5. `test_query_active_users_only`
6. `test_unique_email_constraint_db` - Database-level constraint
7. `test_update_last_login`
8. `test_soft_delete_user` - Set active=False instead of DELETE
9. `test_seed_admin_user_exists` - Default admin from migration
10. `test_case_insensitive_email_search` - Lower() function query

**Coverage Target**: ≥85%

---

### 4. Role Permissions (Documentation Only)

**Role Hierarchy** (for future RBAC implementation):

```python
ROLE_PERMISSIONS = {
    'admin': [
        'user:create', 'user:read', 'user:update', 'user:delete',
        'stock:create', 'stock:read', 'stock:update', 'stock:delete',
        'photo:upload', 'photo:process', 'photo:validate',
        'config:update', 'reports:all'
    ],
    'supervisor': [
        'user:read',
        'stock:create', 'stock:read', 'stock:update',
        'photo:upload', 'photo:process', 'photo:validate',
        'reports:own_team'
    ],
    'worker': [
        'stock:create', 'stock:read',
        'photo:upload',
        'reports:own'
    ],
    'viewer': [
        'stock:read',
        'photo:read',
        'reports:own'
    ]
}
```

**Usage** (in service layer):

```python
def check_permission(user: User, action: str):
    if user.role == 'admin':
        return True  # Admin can do everything
    return action in ROLE_PERMISSIONS.get(user.role, [])
```

---

## Execution Checklist

### Python Expert Tasks (25 min)

- [ ] Create `app/models/user.py` with complete model
- [ ] Add email validation (regex pattern)
- [ ] Add password_hash validation (bcrypt format)
- [ ] Create user_role_enum type
- [ ] Create Alembic migration with indexes
- [ ] Add seed data (default admin user)
- [ ] Add relationships to StockMovement, PhotoProcessingSession, S3Image, ProductSampleImage
- [ ] Test migration (upgrade + downgrade)
- [ ] Verify seed data inserted
- [ ] Run pre-commit hooks (ruff, mypy)

### Testing Expert Tasks (20 min, PARALLEL)

- [ ] Write 14 unit tests in `test_user.py`
- [ ] Write 10 integration tests in `test_user_db.py`
- [ ] Test email validation (valid/invalid formats)
- [ ] Test email normalization (lowercase)
- [ ] Test password_hash validation (bcrypt format)
- [ ] Test role enum (all 4 values)
- [ ] Test unique email constraint
- [ ] Test soft delete (active=False)
- [ ] Test seed admin user exists
- [ ] Verify coverage ≥85%
- [ ] All tests pass

### Team Leader Review (5 min)

- [ ] Verify ERD alignment (database.mmd line 195-206)
- [ ] Check email uniqueness (unique constraint)
- [ ] Validate role enum (4 values)
- [ ] Verify seed admin user (change password reminder)
- [ ] Check indexes (email, role, active)
- [ ] Approve and merge

---

## Known Edge Cases

1. **Duplicate email (case-insensitive)**
    - Scenario: "user@example.com" vs "User@Example.Com"
    - Solution: Normalize to lowercase in validation
    - Test: INSERT both, expect unique constraint violation

2. **Inactive user login attempt**
    - Scenario: User with active=False tries to login
    - Solution: Auth service checks active flag before JWT generation
    - Model: Just store flag, business logic in service

3. **NULL last_login for new users**
    - Scenario: User created but never logged in
    - Solution: Allow NULL (nullable=True)
    - Update: Set last_login on first successful login

4. **Password hash storage (NOT plain text)**
    - Scenario: Developer accidentally stores plain text password
    - Solution: Validation checks bcrypt format ($2b$ prefix, 60 chars)
    - Service: Use bcrypt.hashpw() before storing

5. **Orphaned relationships when user deleted**
    - Scenario: Delete user, what happens to their stock_movements?
    - Solution: Use SET NULL on FKs (audit trail preserved, user anonymized)
    - Alternative: Soft delete (active=False) instead of DELETE

---

## Security Considerations

1. **Password Hashing**:
    - Use bcrypt with cost factor 12 (balance security vs performance)
    - Never store plain text passwords
    - Validate hash format in model (60 chars, $2b$ prefix)

2. **Email Privacy**:
    - Store emails in lowercase (consistent lookup)
    - Consider PII regulations (GDPR, CCPA) for data retention
    - Implement soft delete (active=False) to preserve audit trail

3. **Role Escalation**:
    - Only admins can change user roles (enforce in service layer)
    - Log all role changes for audit
    - Prevent self-role-escalation (admin promoting themselves)

4. **Session Management**:
    - last_login tracks activity
    - Consider adding "last_logout" for session duration tracking
    - JWT tokens should check active flag (reject inactive users)

---

## Performance Expectations

- Insert: <5ms (simple table, few indexes)
- Query by email: <3ms (unique index, primary login lookup)
- Query by role: <10ms (indexed, filter active users)
- Update last_login: <3ms (single column update)

**Scale**: DemeterAI has ~10-50 users (internal staff) → performance is not a concern

---

## Definition of Done

- [ ] Model created in `app/models/user.py`
- [ ] Email validation working (regex pattern + lowercase normalization)
- [ ] Password hash validation working (bcrypt format)
- [ ] user_role_enum created (admin, supervisor, worker, viewer)
- [ ] Alembic migration created and tested
- [ ] Indexes added (email unique, role, active)
- [ ] Seed data added (default admin user)
- [ ] 14 unit tests pass
- [ ] 10 integration tests pass
- [ ] Coverage ≥85%
- [ ] Pre-commit hooks pass (17/17)
- [ ] Relationships to StockMovement, PhotoProcessingSession, S3Image, ProductSampleImage configured
- [ ] Soft delete pattern tested (active=False)
- [ ] Code review approved
- [ ] Security reminder documented (change default admin password)

---

**Estimated Time**: 45-60 minutes
**Actual Time**: _____ (fill after completion)

**Ready to Execute**: YES - Independent model, no dependencies blocking
**Blocks**: DB007 (StockMovements.user_id), DB012 (PhotoProcessingSessions.validated_by_user_id)

---

## Future Enhancements (Out of Scope for DB028)

1. **OAuth Integration**: Google, Microsoft SSO
2. **2FA**: TOTP, SMS verification
3. **Password Reset**: Email-based flow
4. **Session Tokens**: Refresh token pattern
5. **Audit Log**: Separate table for user actions
6. **Profile Photos**: Link to S3Image
7. **Teams/Departments**: Organizational hierarchy

**For Now**: Basic CRUD + auth is sufficient for v2.0

---

## Python Expert Progress (2025-10-14 12:10)

**Status**: ✅ COMPLETE - Ready for Testing Expert

### Completed (25 minutes)

- [✅] Created `app/models/user.py` (388 lines)
- [✅] Implemented User model with all fields (id, email, password_hash, first_name, last_name, role,
  active, last_login, created_at, updated_at)
- [✅] Added UserRoleEnum class (admin, supervisor, worker, viewer)
- [✅] Email validation with regex pattern + lowercase normalization
- [✅] Password hash validation (bcrypt $2b$12$ format, 60 chars)
- [✅] Full name computed property
- [✅] Created Alembic migration `6kp8m3q9n5rt_create_users_table.py`
- [✅] Migration creates user_role_enum PostgreSQL ENUM
- [✅] Migration creates indexes (email unique, role, active)
- [✅] Migration seeds default admin user (admin@demeter.ai / admin123)
- [✅] Updated `app/models/__init__.py` with User export
- [✅] All relationships COMMENTED OUT (not ready: StockMovement, PhotoProcessingSession, S3Image,
  ProductSampleImage)
- [✅] mypy --strict: PASS (no issues)
- [✅] ruff check: PASS (all checks passed)
- [✅] Manual validation tests: PASS
    - Email normalization: "TEST@EXAMPLE.COM" → "test@example.com" ✅
    - Invalid email rejected: "invalid-email" → ValueError ✅
    - Plain text password rejected: "plain_text_password" → ValueError ✅
    - Full name property: "Test User" ✅

### Architecture Compliance

- [✅] Service→Service pattern: N/A (model only, no services yet)
- [✅] Type hints: All public methods have type hints
- [✅] Async/await: N/A (SQLAlchemy model)
- [✅] Pydantic schemas: N/A (model only, schemas not in scope)
- [✅] Business exceptions: Validation errors use ValueError (standard)
- [✅] Dependency injection: N/A (model only)

### Files Created

1. `/home/lucasg/proyectos/DemeterDocs/app/models/user.py` (388 lines)
2. `/home/lucasg/proyectos/DemeterDocs/alembic/versions/6kp8m3q9n5rt_create_users_table.py` (148
   lines)

### Files Modified

1. `/home/lucasg/proyectos/DemeterDocs/app/models/__init__.py` (added User, UserRoleEnum exports)

### Key Decisions

1. **Email normalization**: Auto-convert to lowercase in @validates decorator
2. **Bcrypt validation**: Strict format check ($2b$ prefix, 60 chars) prevents plain text storage
3. **Soft delete**: active flag instead of DELETE (preserves audit trail)
4. **Seed admin**: Default admin@demeter.ai with password "admin123" (bcrypt hashed)
5. **Relationships**: ALL commented out (DB007, DB010, DB012, DB020 not ready)

### Next Steps (Testing Expert)

- [ ] Write 14 unit tests (`tests/unit/models/test_user.py`)
- [ ] Write 10 integration tests (`tests/integration/test_user_db.py`)
- [ ] Test email validation (valid/invalid formats)
- [ ] Test email normalization (lowercase)
- [ ] Test password hash validation (bcrypt format)
- [ ] Test role enum (all 4 values)
- [ ] Test unique email constraint
- [ ] Test soft delete (active=False)
- [ ] Test seed admin user exists
- [ ] Verify coverage ≥85%

**Ready for**: Testing Expert → Team Leader Review
**ETA**: Testing completed in 20 minutes (parallel work)
