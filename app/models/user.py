"""User model - Authentication and role-based access control.

This module defines the User SQLAlchemy model for authentication, authorization,
and user management. Represents internal staff (admins, supervisors, workers, viewers)
with bcrypt password hashing and role-based permissions.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Internal authentication (NOT OAuth/SSO)

Design Decisions:
    - Email as login identifier: Unique, indexed, normalized to lowercase
    - Bcrypt password hashing: $2b$12$ format (60 chars)
    - Role-based access control: 4 levels (admin > supervisor > worker > viewer)
    - Soft delete pattern: active flag instead of DELETE (audit trail preservation)
    - INT PK: Simple auto-increment (user_id)
    - NO OAuth: Basic internal authentication only
    - last_login tracking: Security audit capability

See:
    - Database ERD: ../../database/database.mmd (lines 195-206)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/01_ready/DB028-MINI-PLAN.md

Example:
    ```python
    # Create user with bcrypt password
    from bcrypt import hashpw, gensalt

    password_hash = hashpw(b"secure_password", gensalt(rounds=12)).decode('utf-8')

    admin_user = User(
        email="admin@demeter.ai",
        password_hash=password_hash,
        first_name="System",
        last_name="Administrator",
        role="admin",
        active=True
    )

    # Query active users by role
    supervisors = session.query(User).filter_by(role="supervisor", active=True).all()

    # Soft delete (deactivate instead of DELETE)
    user.active = False
    session.commit()  # Preserves audit trail

    # Access computed property
    # Example: user.full_name returns "System Administrator"
    ```
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    # NOTE: Uncomment after dependent models are complete
    from app.models.photo_processing_session import PhotoProcessingSession
    from app.models.product_sample_image import ProductSampleImage
    from app.models.s3_image import S3Image
    from app.models.stock_movement import StockMovement


# Enum definition (will be created in migration as PostgreSQL ENUM)
class UserRoleEnum:
    """User role constants for role-based access control.

    Hierarchy (descending permissions):
        - admin: Full system access (user management, config, all operations)
        - supervisor: Team management, validation, reporting
        - worker: Stock operations, photo uploads
        - viewer: Read-only access

    Note: This is a Python class for type hints. The actual database ENUM
    is created in the migration file.
    """

    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    VIEWER = "viewer"


class User(Base):
    """User model for authentication and role-based access control.

    Internal staff authentication model with bcrypt password hashing and 4-level
    role hierarchy. Supports soft delete pattern (active flag) to preserve audit
    trails for stock movements, photo sessions, and other user actions.

    Key Features:
        - Email authentication: Unique, indexed, normalized to lowercase
        - Bcrypt password hashing: $2b$12$ format validation (60 chars)
        - Role-based access: 4 levels (admin > supervisor > worker > viewer)
        - Soft delete: active flag (deactivate instead of DELETE)
        - Activity tracking: last_login for security audits
        - NO OAuth: Internal authentication only (NOT social login)

    Attributes:
        id: Primary key (auto-increment)
        email: Unique login identifier (255 chars max, lowercase, indexed)
        password_hash: Bcrypt hash (60 chars, $2b$ prefix, NOT NULL)
        first_name: User first name (100 chars max, NOT NULL)
        last_name: User last name (100 chars max, NOT NULL)
        role: User role enum (admin/supervisor/worker/viewer, default 'worker', indexed)
        active: Account status (Boolean, default True, indexed)
        last_login: Last successful login timestamp (NULLABLE)
        created_at: Account creation timestamp (auto-generated)
        updated_at: Last modification timestamp (auto-updated)

    Relationships (ALL COMMENTED OUT - not ready):
        stock_movements: List of StockMovement instances (one-to-many)
        photo_sessions_validated: List of PhotoProcessingSession instances (one-to-many)
        uploaded_images: List of S3Image instances (one-to-many)
        captured_samples: List of ProductSampleImage instances (one-to-many)

    Indexes:
        - B-tree index on email (unique constraint)
        - B-tree index on role (filter by role)
        - B-tree index on active (filter active users)

    Constraints:
        - email unique constraint
        - email format validation (via @validates decorator)
        - password_hash format validation (bcrypt $2b$12$... format)

    Example:
        ```python
        # Create admin user
        admin = User(
            email="admin@demeter.ai",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",
            first_name="System",
            last_name="Administrator",
            role="admin",
            active=True
        )

        # Query active supervisors
        supervisors = session.query(User).filter_by(
            role="supervisor",
            active=True
        ).all()

        # Soft delete
        user.active = False

        # Full name property
        # Example: user.full_name returns "System Administrator"
        ```
    """

    __tablename__ = "users"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Authentication fields
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique login identifier (normalized to lowercase)",
    )

    password_hash = Column(
        String(60),
        nullable=False,
        comment="Bcrypt password hash ($2b$12$... format, 60 chars)",
    )

    # Profile fields
    first_name = Column(
        String(100),
        nullable=False,
        comment="User first name",
    )

    last_name = Column(
        String(100),
        nullable=False,
        comment="User last name",
    )

    # Authorization (role-based access control)
    role = Column(
        Enum(
            UserRoleEnum.ADMIN,
            UserRoleEnum.SUPERVISOR,
            UserRoleEnum.WORKER,
            UserRoleEnum.VIEWER,
            name="user_role_enum",
        ),
        nullable=False,
        default=UserRoleEnum.WORKER,
        index=True,
        comment="User role (admin > supervisor > worker > viewer)",
    )

    # Account status
    active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Account status (soft delete pattern)",
    )

    # Activity tracking
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
        comment="Account creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last modification timestamp",
    )

    # Relationships (ALL COMMENTED OUT - not ready)

    # One-to-many: User → StockMovement (COMMENT OUT - DB007 not ready)
    # NOTE: Uncomment after DB007 (StockMovement) is complete
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="user",
        foreign_keys="StockMovement.user_id",
        doc="Stock movements performed by this user",
    )

    # One-to-many: User → PhotoProcessingSession (COMMENT OUT - DB012 not ready)
    # NOTE: Uncomment after DB012 (PhotoProcessingSession) is complete
    photo_sessions_validated: Mapped[list["PhotoProcessingSession"]] = relationship(
        "PhotoProcessingSession",
        back_populates="validated_by_user",
        foreign_keys="PhotoProcessingSession.validated_by_user_id",
        doc="Photo sessions validated by this user",
    )

    # One-to-many: User → S3Image (COMMENT OUT - DB010 not ready)
    # NOTE: Uncomment after DB010 (S3Image) is complete
    uploaded_images: Mapped[list["S3Image"]] = relationship(
        "S3Image",
        back_populates="uploaded_by_user",
        foreign_keys="S3Image.uploaded_by_user_id",
        doc="S3 images uploaded by this user",
    )

    # One-to-many: User → ProductSampleImage (COMMENT OUT - DB020 not ready)
    # NOTE: Uncomment after DB020 (ProductSampleImage) is complete
    captured_samples: Mapped[list["ProductSampleImage"]] = relationship(
        "ProductSampleImage",
        back_populates="captured_by_user",
        foreign_keys="ProductSampleImage.captured_by_user_id",
        doc="Product sample images captured by this user",
    )

    # Table constraints
    __table_args__ = (
        {"comment": "Users - Authentication and role-based access control (internal staff)"},
    )

    @validates("email")
    def validate_email(self, key: str, value: str | None) -> str:
        """Validate and normalize email field.

        Rules:
            - Format: Standard email pattern (user@domain.tld)
            - Auto-convert to lowercase (case-insensitive lookup)
            - Max length: 255 characters

        Args:
            key: Field name ("email")
            value: Email address to validate

        Returns:
            Normalized email (lowercase)

        Raises:
            ValueError: If email format is invalid

        Examples:
            >>> user.email = "Admin@Demeter.AI"
            >>> user.email
            "admin@demeter.ai"

            >>> user.email = "invalid-email"
            ValueError: Invalid email format: invalid-email

            >>> user.email = "user@domain"
            ValueError: Invalid email format: user@domain
        """
        if value is None:
            raise ValueError("Email cannot be None")

        # Auto-convert to lowercase
        value = value.lower()

        # Validate email format (standard pattern)
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")

        return value

    @validates("password_hash")
    def validate_password_hash(self, key: str, value: str | None) -> str:
        """Validate bcrypt password hash format.

        Rules:
            - Prefix: Must start with '$2b$' (bcrypt identifier)
            - Length: Exactly 60 characters
            - Format: $2b$12$... (12 = bcrypt cost factor)

        Args:
            key: Field name ("password_hash")
            value: Bcrypt hash to validate

        Returns:
            Validated bcrypt hash

        Raises:
            ValueError: If hash format is invalid

        Examples:
            >>> user.password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6"
            >>> user.password_hash
            "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6"

            >>> user.password_hash = "plain_text_password"
            ValueError: password_hash must be a valid bcrypt hash (must start with $2b$ and be 60 chars)

            >>> user.password_hash = "$2b$12$short"
            ValueError: password_hash must be a valid bcrypt hash (must start with $2b$ and be 60 chars)
        """
        if value is None:
            raise ValueError("password_hash cannot be None")

        # Validate bcrypt format: $2b$12$... (60 chars total)
        if not value.startswith("$2b$") or len(value) != 60:
            raise ValueError(
                "password_hash must be a valid bcrypt hash (must start with $2b$ and be 60 chars)"
            )

        return value

    @property
    def full_name(self) -> str:
        """Computed property for user's full name.

        Returns:
            Full name (first_name + last_name)

        Example:
            >>> user = User(first_name="John", last_name="Doe")
            >>> user.full_name
            "John Doe"
        """
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, email, and role

        Example:
            <User(id=1, email='admin@demeter.ai', role='admin')>
        """
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
