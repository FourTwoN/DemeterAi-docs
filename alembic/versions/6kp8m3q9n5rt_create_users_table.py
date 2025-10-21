"""create users table

Revision ID: 6kp8m3q9n5rt
Revises: 5gh9j2n4k7lm
Create Date: 2025-10-14 12:07:03.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6kp8m3q9n5rt'
down_revision: Union[str, None] = '5gh9j2n4k7lm'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table with authentication and role-based access control."""
    # 1. Create ENUM type (idempotent - checks if exists first)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE user_role_enum AS ENUM ('admin', 'supervisor', 'worker', 'viewer');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # 2. Create users table (enum already created)
    op.create_table(
        'users',
        sa.Column(
            'id',
            sa.Integer(),
            autoincrement=True,
            nullable=False,
            comment='Primary key (auto-increment)'
        ),
        sa.Column(
            'email',
            sa.String(length=255),
            nullable=False,
            comment='Unique login identifier (normalized to lowercase)'
        ),
        sa.Column(
            'password_hash',
            sa.String(length=60),
            nullable=False,
            comment='Bcrypt password hash ($2b$12$... format, 60 chars)'
        ),
        sa.Column(
            'first_name',
            sa.String(length=100),
            nullable=False,
            comment='User first name'
        ),
        sa.Column(
            'last_name',
            sa.String(length=100),
            nullable=False,
            comment='User last name'
        ),
        sa.Column(
            'role',
            postgresql.ENUM('admin', 'supervisor', 'worker', 'viewer', name='user_role_enum', create_type=False),
            nullable=False,
            server_default='worker',
            comment='User role (admin > supervisor > worker > viewer)'
        ),
        sa.Column(
            'active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='Account status (soft delete pattern)'
        ),
        sa.Column(
            'last_login',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last successful login timestamp'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
            comment='Account creation timestamp'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last modification timestamp'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
        comment='Users - Authentication and role-based access control (internal staff)'
    )

    # 3. Create indexes
    op.create_index(
        op.f('ix_users_email'),
        'users',
        ['email'],
        unique=True
    )
    op.create_index(
        op.f('ix_users_role'),
        'users',
        ['role'],
        unique=False
    )
    op.create_index(
        op.f('ix_users_active'),
        'users',
        ['active'],
        unique=False
    )

    # 4. Seed default admin user
    # Password: "admin123" (bcrypt hashed with cost factor 12)
    # IMPORTANT: Change this password in production!
    op.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, role, active)
        VALUES (
            'admin@demeter.ai',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6',
            'System',
            'Administrator',
            'admin',
            true
        );
    """)


def downgrade() -> None:
    """Drop users table and user_role_enum type."""
    # 1. Drop indexes
    op.drop_index(op.f('ix_users_active'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')

    # 2. Drop table (enum auto-dropped by SQLAlchemy)
    op.drop_table('users')
