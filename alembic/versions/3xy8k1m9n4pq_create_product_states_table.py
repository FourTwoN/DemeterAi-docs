"""create_product_states_table

Revision ID: 3xy8k1m9n4pq
Revises: 2wh7p3r9bm6t
Create Date: 2025-10-14 16:50:00.000000

Creates the product_states reference/catalog table with:
- Table with all fields (code, name, description, is_sellable, sort_order)
- CHECK constraint: Code length 3-50 characters
- Indexes: code (UK), is_sellable, sort_order
- SEED DATA: 11 lifecycle states (SEED → DEAD)

This is a SIMPLE reference table (no enums, no PostGIS, no triggers).
"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3xy8k1m9n4pq'
down_revision: Union[str, None] = '2wh7p3r9bm6t'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create product_states table with seed data."""

    # Create product_states table
    op.create_table(
        'product_states',
        sa.Column('product_state_id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key (auto-increment)'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique state code (uppercase, alphanumeric + underscores, 3-50 chars)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Human-readable state name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional detailed description'),
        sa.Column('is_sellable', sa.Boolean(), server_default='false', nullable=False, comment='Business logic flag - can this state be sold? (default FALSE)'),
        sa.Column('sort_order', sa.Integer(), server_default='99', nullable=False, comment='UI dropdown order (lifecycle progression)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Last update timestamp'),
        sa.CheckConstraint("LENGTH(code) >= 3 AND LENGTH(code) <= 50", name='ck_product_state_code_length'),
        sa.PrimaryKeyConstraint('product_state_id'),
        sa.UniqueConstraint('code'),
        comment='Product States - Reference/catalog table defining product lifecycle states'
    )

    # Create indexes
    op.create_index('ix_product_states_code', 'product_states', ['code'], unique=True)
    op.create_index('ix_product_states_is_sellable', 'product_states', ['is_sellable'], unique=False)
    op.create_index('ix_product_states_sort_order', 'product_states', ['sort_order'], unique=False)

    # Insert seed data (11 lifecycle states)
    op.execute("""
        INSERT INTO product_states (code, name, description, is_sellable, sort_order) VALUES

        -- EARLY LIFECYCLE (NOT SELLABLE)
        ('SEED', 'Seed', 'Dormant seed, not yet planted', FALSE, 10),
        ('GERMINATING', 'Germinating', 'Seed has germinated, roots emerging', FALSE, 20),
        ('SEEDLING', 'Seedling', 'Young plant with first true leaves', FALSE, 30),
        ('JUVENILE', 'Juvenile', 'Growing plant, not yet mature', FALSE, 40),

        -- MATURE STAGES (SELLABLE)
        ('ADULT', 'Adult Plant', 'Mature plant, ready for sale', TRUE, 50),
        ('FLOWERING', 'Flowering', 'Plant in bloom, highly desirable', TRUE, 60),
        ('FRUITING', 'Fruiting', 'Producing fruit/seeds', TRUE, 70),

        -- SPECIAL STATES
        ('DORMANT', 'Dormant', 'Resting period (winter dormancy, still sellable)', TRUE, 80),
        ('PROPAGATING', 'Propagating', 'Cutting or division in rooting stage', FALSE, 90),

        -- END-OF-LIFE (NOT SELLABLE)
        ('DYING', 'Dying', 'Plant in decline, not recoverable', FALSE, 100),
        ('DEAD', 'Dead', 'Plant is dead, awaiting disposal', FALSE, 110);
    """)


def downgrade() -> None:
    """Drop product_states table."""

    # Drop indexes
    op.drop_index('ix_product_states_sort_order', table_name='product_states')
    op.drop_index('ix_product_states_is_sellable', table_name='product_states')
    op.drop_index('ix_product_states_code', table_name='product_states')

    # Drop table
    op.drop_table('product_states')
