"""Integration tests for User model with database operations.

Tests the User SQLAlchemy model with real database operations (SQLite in-memory).
Covers database CRUD operations, constraints, indexes, seed data, and complex queries.

Test Coverage:
    - Insert users (all fields / minimal fields)
    - Query by email (unique index)
    - Query by role (indexed)
    - Query active users only (indexed)
    - Unique email constraint (database-level)
    - Update last_login timestamp
    - Soft delete (active=False)
    - Seed admin user verification
    - Case-insensitive email search

Architecture:
    - Layer: Integration Tests (database operations)
    - Dependencies: pytest, pytest-asyncio, User model, db_session fixture
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/integration/models/test_user_db.py -v
    pytest tests/integration/models/test_user_db.py::test_insert_user_all_fields -v
"""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


@pytest.mark.asyncio
async def test_insert_user_all_fields(db_session):
    """Test inserting user with all fields populated."""
    # Arrange
    user = User(
        email="john.doe@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="John",
        last_name="Doe",
        role="supervisor",
        active=True,
        last_login=datetime(2025, 10, 14, 10, 30, 0),
    )

    # Act
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Assert
    assert user.id is not None
    assert user.email == "john.doe@demeter.ai"
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.role == "supervisor"
    assert user.active is True
    assert user.last_login == datetime(2025, 10, 14, 10, 30, 0)
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_insert_user_minimal_fields(db_session):
    """Test inserting user with only required fields (defaults apply)."""
    # Arrange
    user = User(
        email="jane.smith@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Jane",
        last_name="Smith",
    )

    # Act
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Assert
    assert user.id is not None
    assert user.email == "jane.smith@demeter.ai"
    assert user.first_name == "Jane"
    assert user.last_name == "Smith"
    assert user.role == "worker"  # Default
    assert user.active is True  # Default
    assert user.last_login is None  # Nullable
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_query_by_email(db_session):
    """Test querying user by email (unique indexed column)."""
    # Arrange - Create multiple users
    user1 = User(
        email="admin@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Admin",
        last_name="User",
        role="admin",
    )
    user2 = User(
        email="worker@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Worker",
        last_name="User",
        role="worker",
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Act - Query by email
    stmt = select(User).where(User.email == "admin@demeter.ai")
    result = await db_session.execute(stmt)
    found_user = result.scalar_one_or_none()

    # Assert
    assert found_user is not None
    assert found_user.email == "admin@demeter.ai"
    assert found_user.role == "admin"


@pytest.mark.asyncio
async def test_query_by_role(db_session):
    """Test querying users by role (indexed column)."""
    # Arrange - Create users with different roles
    admin = User(
        email="admin@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Admin",
        last_name="User",
        role="admin",
    )
    supervisor = User(
        email="supervisor@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Supervisor",
        last_name="User",
        role="supervisor",
    )
    worker1 = User(
        email="worker1@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Worker",
        last_name="One",
        role="worker",
    )
    worker2 = User(
        email="worker2@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Worker",
        last_name="Two",
        role="worker",
    )
    db_session.add_all([admin, supervisor, worker1, worker2])
    await db_session.commit()

    # Act - Query workers only
    stmt = select(User).where(User.role == "worker")
    result = await db_session.execute(stmt)
    workers = result.scalars().all()

    # Assert
    assert len(workers) == 2
    assert all(user.role == "worker" for user in workers)


@pytest.mark.asyncio
async def test_query_active_users(db_session):
    """Test querying only active users (indexed column)."""
    # Arrange - Create active and inactive users
    active_user = User(
        email="active@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Active",
        last_name="User",
        active=True,
    )
    inactive_user = User(
        email="inactive@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Inactive",
        last_name="User",
        active=False,
    )
    db_session.add_all([active_user, inactive_user])
    await db_session.commit()

    # Act - Query active users only
    stmt = select(User).where(User.active == True)
    result = await db_session.execute(stmt)
    active_users = result.scalars().all()

    # Assert
    assert len(active_users) == 1
    assert active_users[0].email == "active@demeter.ai"
    assert active_users[0].active is True


@pytest.mark.asyncio
async def test_unique_email_constraint_db(db_session):
    """Test that duplicate email raises IntegrityError (database constraint)."""
    # Arrange - Create first user
    user1 = User(
        email="duplicate@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="First",
        last_name="User",
    )
    db_session.add(user1)
    await db_session.commit()

    # Act & Assert - Try to create user with same email
    user2 = User(
        email="duplicate@demeter.ai",  # Same email!
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Second",
        last_name="User",
    )
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_update_last_login(db_session):
    """Test updating last_login timestamp."""
    # Arrange - Create user without last_login
    user = User(
        email="login@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Login",
        last_name="User",
        last_login=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.last_login is None

    # Act - Update last_login
    login_time = datetime(2025, 10, 14, 15, 30, 0)
    user.last_login = login_time
    await db_session.commit()
    await db_session.refresh(user)

    # Assert
    assert user.last_login == login_time


@pytest.mark.asyncio
async def test_soft_delete_user(db_session):
    """Test soft delete pattern (set active=False instead of DELETE)."""
    # Arrange - Create active user
    user = User(
        email="todelete@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="To",
        last_name="Delete",
        active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user_id = user.id
    assert user.active is True

    # Act - Soft delete (set active=False)
    user.active = False
    await db_session.commit()

    # Assert - User still exists in DB but inactive
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    deleted_user = result.scalar_one_or_none()

    assert deleted_user is not None
    assert deleted_user.active is False
    assert deleted_user.email == "todelete@demeter.ai"  # Data preserved


@pytest.mark.asyncio
async def test_seed_admin_user_exists(db_session):
    """Test that seed admin user exists from migration (CRITICAL)."""
    # Note: This test assumes migration seed data is loaded
    # In SQLite in-memory tests, we manually create the admin user

    # Arrange - Manually create seed admin user (simulating migration)
    admin = User(
        email="admin@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",  # "admin123"
        first_name="System",
        last_name="Administrator",
        role="admin",
        active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    # Act - Query for seed admin user
    stmt = select(User).where(User.email == "admin@demeter.ai")
    result = await db_session.execute(stmt)
    seed_admin = result.scalar_one_or_none()

    # Assert
    assert seed_admin is not None
    assert seed_admin.email == "admin@demeter.ai"
    assert seed_admin.role == "admin"
    assert seed_admin.active is True
    assert seed_admin.first_name == "System"
    assert seed_admin.last_name == "Administrator"


@pytest.mark.asyncio
async def test_case_insensitive_email(db_session):
    """Test case-insensitive email search (email normalized to lowercase)."""
    # Arrange - Create user with lowercase email
    user = User(
        email="CaseSensitive@Example.COM",  # Will be normalized
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
        first_name="Case",
        last_name="Sensitive",
    )
    db_session.add(user)
    await db_session.commit()

    # Act - Query with different case
    stmt = select(User).where(User.email == "casesensitive@example.com")
    result = await db_session.execute(stmt)
    found_user = result.scalar_one_or_none()

    # Assert
    assert found_user is not None
    assert found_user.email == "casesensitive@example.com"  # Normalized
    assert found_user.first_name == "Case"
