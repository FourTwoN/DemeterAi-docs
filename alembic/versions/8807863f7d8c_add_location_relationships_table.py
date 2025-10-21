"""add location_relationships table

Revision ID: 8807863f7d8c
Revises: 440n457t9cnp
Create Date: 2025-10-20 12:26:12.144439

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8807863f7d8c'
down_revision: Union[str, None] = '440n457t9cnp'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ENUM type (idempotent - checks if exists first)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE relationshiptypeenum AS ENUM ('contains', 'adjacent_to');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # 2. Create location_relationships table (enum already created)
    op.create_table(
        'location_relationships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key'),
        sa.Column('parent_location_id', sa.Integer(), nullable=False, comment='Parent location ID'),
        sa.Column('child_location_id', sa.Integer(), nullable=False, comment='Child location ID'),
        sa.Column('relationship_type', postgresql.ENUM('contains', 'adjacent_to', name='relationshiptypeenum', create_type=False), nullable=False, comment='Relationship type: contains or adjacent_to'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.CheckConstraint('parent_location_id != child_location_id', name='ck_no_self_reference'),
        sa.ForeignKeyConstraint(['child_location_id'], ['storage_locations.location_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_location_id'], ['storage_locations.location_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parent_location_id', 'child_location_id', name='uq_location_pair'),
        comment='Hierarchical and adjacency relationships between storage locations'
    )

    op.create_index('ix_location_relationships_parent_location_id', 'location_relationships', ['parent_location_id'])
    op.create_index('ix_location_relationships_child_location_id', 'location_relationships', ['child_location_id'])


def downgrade() -> None:
    op.drop_index('ix_location_relationships_child_location_id', table_name='location_relationships')
    op.drop_index('ix_location_relationships_parent_location_id', table_name='location_relationships')
    # Drop table (enum auto-dropped by SQLAlchemy)
    op.drop_table('location_relationships')
