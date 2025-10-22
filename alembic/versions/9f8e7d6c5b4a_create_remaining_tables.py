"""Create remaining tables for packaging, stock, and processing

Revision ID: 9f8e7d6c5b4a
Revises: 8807863f7d8c
Create Date: 2025-10-21 14:00:00.000000

This migration creates all remaining tables that were missing:
- packaging_types, packaging_materials, packaging_colors
- packaging_catalog, price_list
- stock_batches, stock_movements
- photo_processing_sessions, product_sample_images
- detections, estimations, classifications
- storage_location_config, density_parameters
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f8e7d6c5b4a'
down_revision: Union[str, None] = '8807863f7d8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  # ===== CREATE ALL ENUM TYPES FIRST (IDEMPOTENT) =====

  # sessionstatusenum for photo_processing_sessions
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE sessionstatusenum AS ENUM ('pending', 'processing', 'completed', 'failed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # sampletypeenum for product_sample_images
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE sampletypeenum AS ENUM ('reference', 'growth_stage', 'quality_check', 'monthly_sample');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # movementtypeenum for stock_movements
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE movementtypeenum AS ENUM ('plantar', 'sembrar', 'transplante', 'muerte', 'ventas', 'foto', 'ajuste', 'manual_init');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # sourcetypeenum for stock_movements
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE sourcetypeenum AS ENUM ('manual', 'ia');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # calculationmethodenum for estimations
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE calculationmethodenum AS ENUM ('band_estimation', 'density_estimation', 'grid_analysis');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # ===== PACKAGING LAYER (Foundation for catalog) =====

  # packaging_types table
  op.create_table(
      'packaging_types',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('code', sa.String(20), nullable=False, unique=True),
      sa.Column('name', sa.String(100), nullable=False),
      sa.Column('description', sa.Text(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.PrimaryKeyConstraint('id'),
      comment='Packaging types (pot, box, tray, etc.)'
  )
  op.create_index('ix_packaging_types_code', 'packaging_types', ['code'])

  # packaging_materials table
  op.create_table(
      'packaging_materials',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('code', sa.String(20), nullable=False, unique=True),
      sa.Column('name', sa.String(100), nullable=False),
      sa.Column('description', sa.Text(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.PrimaryKeyConstraint('id'),
      comment='Packaging materials (plastic, ceramic, etc.)'
  )
  op.create_index('ix_packaging_materials_code', 'packaging_materials',
                  ['code'])

  # packaging_colors table
  op.create_table(
      'packaging_colors',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('name', sa.String(50), nullable=False, unique=True),
      sa.Column('hex_code', sa.String(7), nullable=False),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.PrimaryKeyConstraint('id'),
      comment='Packaging colors'
  )
  op.create_index('ix_packaging_colors_hex_code', 'packaging_colors',
                  ['hex_code'])

  # packaging_catalog table
  op.create_table(
      'packaging_catalog',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('packaging_type_id', sa.Integer(), nullable=False),
      sa.Column('packaging_material_id', sa.Integer(), nullable=False),
      sa.Column('packaging_color_id', sa.Integer(), nullable=False),
      sa.Column('sku', sa.String(50), nullable=False, unique=True),
      sa.Column('name', sa.String(200), nullable=False),
      sa.Column('volume_liters', sa.Numeric(10, 2), nullable=True),
      sa.Column('diameter_cm', sa.Numeric(10, 2), nullable=True),
      sa.Column('height_cm', sa.Numeric(10, 2), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['packaging_type_id'], ['packaging_types.id'],
                              ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['packaging_material_id'],
                              ['packaging_materials.id'], ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['packaging_color_id'], ['packaging_colors.id'],
                              ondelete='RESTRICT'),
      sa.PrimaryKeyConstraint('id'),
      comment='Packaging catalog - combinations of type, material, color'
  )
  op.create_index('ix_packaging_catalog_sku', 'packaging_catalog', ['sku'])
  op.create_index('ix_packaging_catalog_type', 'packaging_catalog',
                  ['packaging_type_id'])

  # ===== PRICE LIST =====

  op.create_table(
      'price_list',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('packaging_catalog_id', sa.Integer(), nullable=False),
      sa.Column('product_categories_id', sa.Integer(), nullable=False),
      sa.Column('wholesale_unit_price', sa.Numeric(12, 2), nullable=True),
      sa.Column('retail_unit_price', sa.Numeric(12, 2), nullable=True),
      sa.Column('sku', sa.String(100), nullable=True),
      sa.Column('unit_per_storage_box', sa.Integer(), nullable=True),
      sa.Column('wholesale_total_price_per_box', sa.Numeric(12, 2),
                nullable=True),
      sa.Column('observations', sa.Text(), nullable=True),
      sa.Column('availability', sa.String(50), nullable=True),
      sa.Column('discount_factor', sa.Numeric(5, 3), nullable=True),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['packaging_catalog_id'],
                              ['packaging_catalog.id'], ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['product_categories_id'],
                              ['product_categories.id'], ondelete='CASCADE'),
      sa.PrimaryKeyConstraint('id'),
      comment='Price list for products and packaging combinations'
  )
  op.create_index('ix_price_list_sku', 'price_list', ['sku'])

  # ===== STOCK MANAGEMENT =====

  op.create_table(
      'stock_batches',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('batch_code', sa.String(50), nullable=False, unique=True),
      sa.Column('current_storage_bin_id', sa.Integer(), nullable=False),
      sa.Column('product_id', sa.Integer(), nullable=False),
      sa.Column('product_state_id', sa.Integer(), nullable=False),
      sa.Column('product_size_id', sa.Integer(), nullable=True),
      sa.Column('has_packaging', sa.Boolean(), nullable=False,
                server_default='false'),
      sa.Column('packaging_catalog_id', sa.Integer(), nullable=True),
      sa.Column('quantity_initial', sa.Integer(), nullable=False),
      sa.Column('quantity_current', sa.Integer(), nullable=False),
      sa.Column('quantity_empty_containers', sa.Integer(), nullable=False,
                server_default='0'),
      sa.Column('quality_score', sa.Numeric(3, 1), nullable=True),
      sa.Column('planting_date', sa.Date(), nullable=True),
      sa.Column('germination_date', sa.Date(), nullable=True),
      sa.Column('transplant_date', sa.Date(), nullable=True),
      sa.Column('expected_ready_date', sa.Date(), nullable=True),
      sa.Column('notes', sa.Text(), nullable=True),
      sa.Column('custom_attributes', sa.JSON(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.CheckConstraint('quantity_initial >= 0',
                         name='ck_stock_batch_qty_init'),
      sa.CheckConstraint('quantity_current >= 0',
                         name='ck_stock_batch_qty_curr'),
      sa.CheckConstraint('quality_score >= 0 AND quality_score <= 5',
                         name='ck_quality_score'),
      sa.ForeignKeyConstraint(['current_storage_bin_id'],
                              ['storage_bins.bin_id'], ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['product_id'], ['products.id'],
                              ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['product_state_id'],
                              ['product_states.product_state_id'],
                              ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['product_size_id'],
                              ['product_sizes.product_size_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['packaging_catalog_id'],
                              ['packaging_catalog.id'], ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Stock batches - groups of plants with same characteristics'
  )
  op.create_index('ix_stock_batches_batch_code', 'stock_batches',
                  ['batch_code'])
  op.create_index('ix_stock_batches_product_id', 'stock_batches',
                  ['product_id'])
  op.create_index('ix_stock_batches_bin_id', 'stock_batches',
                  ['current_storage_bin_id'])

  # ===== PHOTO PROCESSING & ML =====

  op.create_table(
      'photo_processing_sessions',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('session_id', sa.String(36), nullable=False, unique=True),
      # UUID as string
      sa.Column('storage_location_id', sa.Integer(), nullable=True),
      sa.Column('original_image_id', postgresql.UUID(as_uuid=True),
                nullable=True),  # UUID reference
      sa.Column('processed_image_id', postgresql.UUID(as_uuid=True),
                nullable=True),  # UUID reference
      sa.Column('total_detected', sa.Integer(), nullable=False,
                server_default='0'),
      sa.Column('total_estimated', sa.Integer(), nullable=False,
                server_default='0'),
      sa.Column('total_empty_containers', sa.Integer(), nullable=False,
                server_default='0'),
      sa.Column('avg_confidence', sa.Numeric(3, 2), nullable=True),
      sa.Column('category_counts', sa.JSON(), nullable=True),
      sa.Column('status',
                postgresql.ENUM('pending', 'processing', 'completed', 'failed',
                                name='sessionstatusenum', create_type=False),
                nullable=False, server_default='pending'),
      sa.Column('error_message', sa.Text(), nullable=True),
      sa.Column('validated', sa.Boolean(), nullable=False,
                server_default='false'),
      sa.Column('validated_by_user_id', sa.Integer(), nullable=True),
      sa.Column('validation_date', sa.DateTime(), nullable=True),
      sa.Column('manual_adjustments', sa.JSON(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['storage_location_id'],
                              ['storage_locations.location_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['original_image_id'], ['s3_images.image_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['processed_image_id'], ['s3_images.image_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['validated_by_user_id'], ['users.id'],
                              ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Photo processing sessions for ML pipeline'
  )
  op.create_index('ix_photo_sessions_session_id', 'photo_processing_sessions',
                  ['session_id'])
  op.create_index('ix_photo_sessions_location_id', 'photo_processing_sessions',
                  ['storage_location_id'])
  op.create_index('ix_photo_sessions_status', 'photo_processing_sessions',
                  ['status'])

  # product_sample_images table
  op.create_table(
      'product_sample_images',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('product_id', sa.Integer(), nullable=False),
      sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
      # UUID reference to s3_images
      sa.Column('product_state_id', sa.Integer(), nullable=True),
      sa.Column('product_size_id', sa.Integer(), nullable=True),
      sa.Column('storage_location_id', sa.Integer(), nullable=True),
      sa.Column('sample_type',
                postgresql.ENUM('reference', 'growth_stage', 'quality_check',
                                'monthly_sample',
                                name='sampletypeenum', create_type=False),
                nullable=False),
      sa.Column('capture_date', sa.Date(), nullable=False),
      sa.Column('captured_by_user_id', sa.Integer(), nullable=False),
      sa.Column('notes', sa.Text(), nullable=True),
      sa.Column('display_order', sa.Integer(), nullable=True),
      sa.Column('is_primary', sa.Boolean(), nullable=False,
                server_default='false'),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['product_id'], ['products.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['image_id'], ['s3_images.image_id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['product_state_id'],
                              ['product_states.product_state_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['product_size_id'],
                              ['product_sizes.product_size_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['storage_location_id'],
                              ['storage_locations.location_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['captured_by_user_id'], ['users.id'],
                              ondelete='RESTRICT'),
      sa.PrimaryKeyConstraint('id'),
      comment='Sample images for products at different stages'
  )
  op.create_index('ix_product_sample_images_product_id',
                  'product_sample_images', ['product_id'])

  # ===== STOCK MOVEMENTS =====

  op.create_table(
      'stock_movements',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('movement_id', sa.String(36), nullable=False, unique=True),
      # UUID as string
      sa.Column('batch_id', sa.Integer(), nullable=False),
      sa.Column('movement_type',
                postgresql.ENUM('plantar', 'sembrar', 'transplante', 'muerte',
                                'ventas',
                                'foto', 'ajuste', 'manual_init',
                                name='movementtypeenum', create_type=False),
                nullable=False),
      sa.Column('source_bin_id', sa.Integer(), nullable=True),
      sa.Column('destination_bin_id', sa.Integer(), nullable=True),
      sa.Column('quantity', sa.Integer(), nullable=False),
      sa.Column('user_id', sa.Integer(), nullable=False),
      sa.Column('unit_price', sa.Numeric(12, 2), nullable=True),
      sa.Column('total_price', sa.Numeric(12, 2), nullable=True),
      sa.Column('reason_description', sa.Text(), nullable=True),
      sa.Column('processing_session_id', sa.Integer(), nullable=True),
      sa.Column('source_type',
                postgresql.ENUM('manual', 'ia', name='sourcetypeenum',
                                create_type=False), nullable=False),
      sa.Column('is_inbound', sa.Boolean(), nullable=False),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.CheckConstraint('quantity != 0', name='ck_movement_qty_nonzero'),
      sa.ForeignKeyConstraint(['batch_id'], ['stock_batches.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['source_bin_id'], ['storage_bins.bin_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['destination_bin_id'], ['storage_bins.bin_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['processing_session_id'],
                              ['photo_processing_sessions.id'],
                              ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Stock movement history - tracks all quantity changes'
  )
  op.create_index('ix_stock_movements_movement_id', 'stock_movements',
                  ['movement_id'])
  op.create_index('ix_stock_movements_batch_id', 'stock_movements',
                  ['batch_id'])
  op.create_index('ix_stock_movements_type', 'stock_movements',
                  ['movement_type'])

  # ===== CLASSIFICATIONS & ML OUTPUTS =====

  op.create_table(
      'classifications',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('product_id', sa.Integer(), nullable=False),
      sa.Column('product_size_id', sa.Integer(), nullable=True),
      sa.Column('packaging_catalog_id', sa.Integer(), nullable=True),
      sa.Column('product_conf', sa.Numeric(3, 2), nullable=True),
      sa.Column('packaging_conf', sa.Numeric(3, 2), nullable=True),
      sa.Column('product_size_conf', sa.Numeric(3, 2), nullable=True),
      sa.Column('model_version', sa.String(20), nullable=True),
      sa.Column('name', sa.String(200), nullable=False),
      sa.Column('description', sa.Text(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['product_id'], ['products.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['product_size_id'],
                              ['product_sizes.product_size_id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['packaging_catalog_id'],
                              ['packaging_catalog.id'], ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Classification results from ML models'
  )
  op.create_index('ix_classifications_product_id', 'classifications',
                  ['product_id'])

  # detections table (partitioned by date, but creating base table)
  op.create_table(
      'detections',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('session_id', sa.Integer(), nullable=False),
      sa.Column('stock_movement_id', sa.Integer(), nullable=True),
      sa.Column('classification_id', sa.Integer(), nullable=True),
      sa.Column('center_x_px', sa.Numeric(12, 2), nullable=False),
      sa.Column('center_y_px', sa.Numeric(12, 2), nullable=False),
      sa.Column('width_px', sa.Integer(), nullable=False),
      sa.Column('height_px', sa.Integer(), nullable=False),
      sa.Column('area_px', sa.Integer(), nullable=True),
      sa.Column('bbox_coordinates', sa.JSON(), nullable=True),
      sa.Column('detection_confidence', sa.Numeric(3, 2), nullable=False),
      sa.Column('is_empty_container', sa.Boolean(), nullable=False,
                server_default='false'),
      sa.Column('is_alive', sa.Boolean(), nullable=False,
                server_default='true'),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['session_id'], ['photo_processing_sessions.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['classification_id'], ['classifications.id'],
                              ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Detections from ML models - individual plant detections'
  )
  op.create_index('ix_detections_session_id', 'detections', ['session_id'])
  op.create_index('ix_detections_movement_id', 'detections',
                  ['stock_movement_id'])

  # estimations table (partitioned by date, but creating base table)
  op.create_table(
      'estimations',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('session_id', sa.Integer(), nullable=False),
      sa.Column('stock_movement_id', sa.Integer(), nullable=True),
      sa.Column('classification_id', sa.Integer(), nullable=True),
      sa.Column('vegetation_polygon', sa.JSON(), nullable=True),
      sa.Column('detected_area_cm2', sa.Numeric(12, 2), nullable=True),
      sa.Column('estimated_count', sa.Integer(), nullable=False),
      sa.Column('calculation_method',
                postgresql.ENUM('band_estimation', 'density_estimation',
                                'grid_analysis',
                                name='calculationmethodenum',
                                create_type=False), nullable=False),
      sa.Column('estimation_confidence', sa.Numeric(3, 2), nullable=False,
                server_default='0.70'),
      sa.Column('used_density_parameters', sa.Boolean(), nullable=False,
                server_default='false'),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['session_id'], ['photo_processing_sessions.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id'],
                              ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['classification_id'], ['classifications.id'],
                              ondelete='SET NULL'),
      sa.PrimaryKeyConstraint('id'),
      comment='Estimations from ML models - aggregate plant counts'
  )
  op.create_index('ix_estimations_session_id', 'estimations', ['session_id'])
  op.create_index('ix_estimations_method', 'estimations',
                  ['calculation_method'])

  # ===== CONFIGURATION TABLES =====

  op.create_table(
      'storage_location_config',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('storage_location_id', sa.Integer(), nullable=False),
      sa.Column('product_id', sa.Integer(), nullable=False),
      sa.Column('packaging_catalog_id', sa.Integer(), nullable=True),
      sa.Column('expected_product_state_id', sa.Integer(), nullable=False),
      sa.Column('area_cm2', sa.Numeric(15, 2), nullable=False),
      sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
      sa.Column('notes', sa.Text(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['storage_location_id'],
                              ['storage_locations.location_id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['product_id'], ['products.id'],
                              ondelete='RESTRICT'),
      sa.ForeignKeyConstraint(['packaging_catalog_id'],
                              ['packaging_catalog.id'], ondelete='SET NULL'),
      sa.ForeignKeyConstraint(['expected_product_state_id'],
                              ['product_states.product_state_id'],
                              ondelete='RESTRICT'),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('storage_location_id', 'product_id',
                          'packaging_catalog_id',
                          name='uq_location_product_pkg'),
      comment='Configuration for what products/states are expected in each location'
  )
  op.create_index('ix_storage_location_config_location_id',
                  'storage_location_config', ['storage_location_id'])

  # density_parameters table
  op.create_table(
      'density_parameters',
      sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
      sa.Column('storage_bin_type_id', sa.Integer(), nullable=False),
      sa.Column('product_id', sa.Integer(), nullable=False),
      sa.Column('packaging_catalog_id', sa.Integer(), nullable=False),
      sa.Column('avg_area_per_plant_cm2', sa.Numeric(10, 2), nullable=False),
      sa.Column('plants_per_m2', sa.Numeric(8, 2), nullable=False),
      sa.Column('overlap_adjustment_factor', sa.Numeric(4, 2), nullable=False,
                server_default='0.85'),
      sa.Column('avg_diameter_cm', sa.Numeric(6, 2), nullable=True),
      sa.Column('notes', sa.Text(), nullable=True),
      sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                nullable=False),
      sa.ForeignKeyConstraint(['storage_bin_type_id'],
                              ['storage_bin_types.bin_type_id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['product_id'], ['products.id'],
                              ondelete='CASCADE'),
      sa.ForeignKeyConstraint(['packaging_catalog_id'],
                              ['packaging_catalog.id'], ondelete='CASCADE'),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('storage_bin_type_id', 'product_id',
                          'packaging_catalog_id', name='uq_density_params'),
      comment='Density parameters for plant counting estimations'
  )
  op.create_index('ix_density_parameters_bin_type_id', 'density_parameters',
                  ['storage_bin_type_id'])
  op.create_index('ix_density_parameters_product_id', 'density_parameters',
                  ['product_id'])


def downgrade() -> None:
  # Drop all tables in reverse order of creation
  op.drop_table('density_parameters')
  op.drop_table('storage_location_config')
  op.drop_table('estimations')
  op.drop_table('detections')
  op.drop_table('classifications')
  op.drop_table('stock_movements')
  op.drop_table('product_sample_images')
  op.drop_table('photo_processing_sessions')
  op.drop_table('stock_batches')
  op.drop_table('price_list')
  op.drop_table('packaging_catalog')
  op.drop_table('packaging_colors')
  op.drop_table('packaging_materials')
  op.drop_table('packaging_types')
