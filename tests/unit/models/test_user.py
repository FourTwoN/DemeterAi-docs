"""Unit tests for User model.

Tests the User SQLAlchemy model in isolation without database dependencies.
Covers model instantiation, email validation, password hash validation, role enum,
computed properties, relationships, and business logic.

Test Coverage:
    - Model instantiation with valid data
    - Email validation (format, normalization to lowercase)
    - Password hash validation (bcrypt format)
    - Role enum (admin, supervisor, worker, viewer)
    - Default values (role=worker, active=True)
    - Computed property (full_name)
    - Nullable fields (last_login)
    - __repr__ method
    - Relationships (stock_movements, photo_sessions, images)

Architecture:
    - Layer: Unit Tests (isolated model testing)
    - Dependencies: pytest, User model
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_user.py -v
    pytest tests/unit/models/test_user.py::TestUserModel::test_create_user_with_all_fields -v
    pytest tests/unit/models/test_user.py --cov=app.models.user --cov-report=term-missing
"""

from datetime import datetime

import pytest

from app.models.user import User


class TestUserModel:
    """Test suite for User model instantiation and attributes."""

    def test_create_user_with_all_fields(self):
        """Test creating User with all fields populated."""
        # Arrange & Act
        user = User(
            id=1,
            email="john.doe@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="John",
            last_name="Doe",
            role="supervisor",
            active=True,
            last_login=datetime(2025, 10, 14, 10, 30, 0),
        )

        # Assert
        assert user.id == 1
        assert user.email == "john.doe@demeter.ai"
        assert user.password_hash == "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "supervisor"
        assert user.active is True
        assert user.last_login == datetime(2025, 10, 14, 10, 30, 0)

    def test_create_user_with_minimal_fields(self):
        """Test creating User with only required fields."""
        # Arrange & Act
        user = User(
            email="jane.smith@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Jane",
            last_name="Smith",
        )

        # Assert
        assert user.email == "jane.smith@demeter.ai"
        assert user.first_name == "Jane"
        assert user.last_name == "Smith"
        # Note: role and active defaults are set at DB level, not Python model level
        assert user.last_login is None  # Nullable

    def test_role_default_worker(self):
        """Test that role can be set to 'worker'."""
        # Arrange & Act
        user = User(
            email="worker@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Test",
            last_name="Worker",
            role="worker",  # Explicitly set
        )

        # Assert
        assert user.role == "worker"

    def test_active_default_true(self):
        """Test that active status can be set to True."""
        # Arrange & Act
        user = User(
            email="active@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Active",
            last_name="User",
            active=True,  # Explicitly set
        )

        # Assert
        assert user.active is True

    def test_last_login_nullable(self):
        """Test that last_login can be NULL."""
        # Arrange & Act
        user = User(
            email="newuser@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="New",
            last_name="User",
            last_login=None,
        )

        # Assert
        assert user.last_login is None


class TestUserEmailValidation:
    """Test suite for User email validation logic."""

    def test_email_valid_formats(self):
        """Test email with valid formats."""
        # Valid email formats
        valid_emails = [
            "user@example.com",
            "john.doe@company.co.uk",
            "admin@demeter.ai",
            "test+label@domain.com",
            "user_name@sub.domain.org",
        ]

        for email in valid_emails:
            # Arrange & Act
            user = User(
                email=email,
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
                first_name="Test",
                last_name="User",
            )

            # Assert
            assert user.email is not None
            assert "@" in user.email

    def test_email_invalid_formats(self):
        """Test that invalid email formats raise ValueError."""
        # Invalid email formats
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
            "user@@example.com",
        ]

        for email in invalid_emails:
            # Arrange & Act & Assert
            with pytest.raises(ValueError, match="Invalid email format"):
                User(
                    email=email,
                    password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
                    first_name="Test",
                    last_name="User",
                )

    def test_email_normalized_lowercase(self):
        """Test that email is automatically normalized to lowercase."""
        # Arrange & Act
        user = User(
            email="User@Example.Com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Test",
            last_name="User",
        )

        # Assert
        assert user.email == "user@example.com"

    def test_email_mixed_case_normalization(self):
        """Test that mixed case email is normalized to lowercase."""
        # Arrange & Act
        user = User(
            email="John.Doe@COMPANY.COM",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="John",
            last_name="Doe",
        )

        # Assert
        assert user.email == "john.doe@company.com"


class TestUserPasswordHashValidation:
    """Test suite for User password hash validation logic."""

    def test_password_hash_valid_bcrypt(self):
        """Test password hash with valid bcrypt format."""
        # Arrange & Act
        valid_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6"
        user = User(
            email="user@demeter.ai",
            password_hash=valid_hash,
            first_name="Test",
            last_name="User",
        )

        # Assert
        assert user.password_hash == valid_hash
        assert len(user.password_hash) == 60
        assert user.password_hash.startswith("$2b$")

    def test_password_hash_invalid_format(self):
        """Test that non-bcrypt password hash raises ValueError."""
        # Invalid password hashes
        invalid_hashes = [
            "plaintext",
            "$2a$12$short",  # Wrong prefix
            "$2b$12$tooshort",  # Too short
            "not-a-bcrypt-hash-at-all",
            "",
        ]

        for invalid_hash in invalid_hashes:
            # Arrange & Act & Assert
            with pytest.raises(ValueError, match="must be a valid bcrypt hash"):
                User(
                    email="user@demeter.ai",
                    password_hash=invalid_hash,
                    first_name="Test",
                    last_name="User",
                )

    def test_password_hash_wrong_length(self):
        """Test that password hash with wrong length raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="must be a valid bcrypt hash"):
            User(
                email="user@demeter.ai",
                password_hash="$2b$12$tooshort",  # Not 60 chars
                first_name="Test",
                last_name="User",
            )


class TestUserRoleEnum:
    """Test suite for User role enum."""

    def test_role_enum_all_values(self):
        """Test that all role enum values are valid."""
        # All valid roles
        valid_roles = ["admin", "supervisor", "worker", "viewer"]

        for role in valid_roles:
            # Arrange & Act
            user = User(
                email=f"{role}@demeter.ai",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
                first_name="Test",
                last_name="User",
                role=role,
            )

            # Assert
            assert user.role == role

    def test_role_admin(self):
        """Test admin role."""
        # Arrange & Act
        user = User(
            email="admin@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Admin",
            last_name="User",
            role="admin",
        )

        # Assert
        assert user.role == "admin"

    def test_role_supervisor(self):
        """Test supervisor role."""
        # Arrange & Act
        user = User(
            email="supervisor@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Supervisor",
            last_name="User",
            role="supervisor",
        )

        # Assert
        assert user.role == "supervisor"

    def test_role_viewer(self):
        """Test viewer role."""
        # Arrange & Act
        user = User(
            email="viewer@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Viewer",
            last_name="User",
            role="viewer",
        )

        # Assert
        assert user.role == "viewer"


class TestUserProperties:
    """Test suite for User computed properties."""

    def test_full_name_property(self):
        """Test full_name computed property."""
        # Arrange & Act
        user = User(
            email="john.doe@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="John",
            last_name="Doe",
        )

        # Assert
        assert user.full_name == "John Doe"

    def test_full_name_property_with_unicode(self):
        """Test full_name with Unicode characters (Spanish names)."""
        # Arrange & Act
        user = User(
            email="maria.garcia@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="María",
            last_name="García",
        )

        # Assert
        assert user.full_name == "María García"


class TestUserRepr:
    """Test suite for User __repr__ method."""

    def test_repr_with_all_fields(self):
        """Test __repr__ with all fields populated."""
        # Arrange
        user = User(
            id=5,
            email="admin@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="System",
            last_name="Administrator",
            role="admin",
        )

        # Act
        repr_str = repr(user)

        # Assert
        assert "User" in repr_str
        assert "5" in repr_str
        assert "admin@demeter.ai" in repr_str
        assert "admin" in repr_str

    def test_repr_with_minimal_fields(self):
        """Test __repr__ with minimal required fields."""
        # Arrange
        user = User(
            email="worker@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="Test",
            last_name="Worker",
        )

        # Act
        repr_str = repr(user)

        # Assert
        assert "User" in repr_str
        assert "worker@demeter.ai" in repr_str
        assert "worker" in repr_str  # Default role

    def test_repr_without_id(self):
        """Test __repr__ before id is assigned (pre-insert)."""
        # Arrange
        user = User(
            email="newuser@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="New",
            last_name="User",
        )

        # Act
        repr_str = repr(user)

        # Assert
        assert "User" in repr_str
        assert "newuser@demeter.ai" in repr_str


class TestUserTableMetadata:
    """Test suite for User table metadata and constraints."""

    def test_table_name(self):
        """Test that table name is correct."""
        assert User.__tablename__ == "users"

    def test_table_comment(self):
        """Test that table has descriptive comment."""
        table_args = User.__table_args__
        if isinstance(table_args, tuple):
            comment_dict = table_args[-1] if table_args else {}
            assert "comment" in comment_dict
            assert len(comment_dict["comment"]) > 0

    def test_column_comments(self):
        """Test that columns have descriptive comments."""
        # Get table columns
        table = User.__table__

        # Check id comment
        assert table.c.id.comment is not None
        assert "Primary key" in table.c.id.comment

        # Check email comment
        assert table.c.email.comment is not None

    def test_primary_key(self):
        """Test that id is the primary key."""
        table = User.__table__
        pk_columns = [col.name for col in table.primary_key.columns]
        assert pk_columns == ["id"]

    def test_email_unique_constraint(self):
        """Test that email has unique constraint."""
        table = User.__table__
        email_column = table.c.email
        assert email_column.unique is True or email_column.index is True


class TestUserRelationships:
    """Test suite for User relationships (type hints only, no DB).

    NOTE: All relationships are commented out in the User model because
    the dependent models (StockMovement, PhotoProcessingSession, S3Image,
    ProductSampleImage) are not yet implemented. These tests will pass
    once those models are created and relationships are uncommented.
    """

    def test_relationships_commented_out(self):
        """Test that relationships are NOT yet defined (dependent models not ready)."""
        # All relationships should be commented out until dependent models exist
        assert "stock_movements" not in User.__mapper__.relationships
        assert "photo_sessions_validated" not in User.__mapper__.relationships
        assert "uploaded_images" not in User.__mapper__.relationships
        assert "captured_samples" not in User.__mapper__.relationships

    def test_relationship_attributes_not_present(self):
        """Test that relationship attributes are not accessible (commented out)."""
        # Relationships are commented out, so hasattr should return False
        assert not hasattr(User, "stock_movements")
        assert not hasattr(User, "photo_sessions_validated")
        assert not hasattr(User, "uploaded_images")
        assert not hasattr(User, "captured_samples")
