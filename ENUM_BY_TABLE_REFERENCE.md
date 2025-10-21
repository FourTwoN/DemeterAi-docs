# ENUM Reference by Table

Complete mapping of all ENUMs to their tables and columns.

---

## warehouses

**Table**: warehouses
**ENUMs**: 1

### warehouse_type_enum
- **Column**: `warehouse_type`
- **Values**: `'greenhouse'`, `'shadehouse'`, `'open_field'`, `'tunnel'`
- **Migration**: `2f68e3f132f5_create_warehouses_table.py` (Line 59)
- **Default**: None
- **Nullable**: NO
- **SQL Definition**: `sa.Enum('greenhouse', 'shadehouse', 'open_field', 'tunnel', name='warehouse_type_enum')`

---

## storage_areas

**Table**: storage_areas
**ENUMs**: 1

### position_enum
- **Column**: `position`
- **Values**: `'N'`, `'S'`, `'E'`, `'W'`, `'C'` (Cardinal directions)
- **Migration**: `742a3bebd3a8_create_storage_areas_table.py` (Line 65)
- **Default**: None
- **Nullable**: YES
- **Description**: Cardinal direction (North, South, East, West, Center)
- **SQL Definition**: `sa.Enum('N', 'S', 'E', 'W', 'C', name='position_enum')`

---

## users

**Table**: users
**ENUMs**: 1

### user_role_enum
- **Column**: `role`
- **Values**: `'admin'`, `'supervisor'`, `'worker'`, `'viewer'`
- **Migration**: `6kp8m3q9n5rt_create_users_table.py` (Line 59)
- **Default**: `'worker'`
- **Nullable**: NO
- **Hierarchy**: admin > supervisor > worker > viewer
- **SQL Definition**: `sa.Enum('admin', 'supervisor', 'worker', 'viewer', name='user_role_enum')`

---

## storage_bin_types

**Table**: storage_bin_types
**ENUMs**: 1

### bin_category_enum
- **Column**: `category`
- **Values**: `'plug'`, `'seedling_tray'`, `'box'`, `'segment'`, `'pot'`
- **Migration**: `2wh7p3r9bm6t_create_storage_bin_types_table.py` (Line 38)
- **Default**: None
- **Nullable**: NO
- **Seed Data**: 7 predefined bin types
- **SQL Definition**: `sa.Enum('plug', 'seedling_tray', 'box', 'segment', 'pot', name='bin_category_enum')`

---

## storage_bins

**Table**: storage_bins
**ENUMs**: 1

### storage_bin_status_enum
- **Column**: `status`
- **Values**: `'active'`, `'maintenance'`, `'retired'`
- **Migration**: `1wgcfiexamud_create_storage_bins_table.py` (Line 66)
- **Default**: `'active'`
- **Nullable**: NO
- **Description**: retired is terminal state (can only go from active/maintenance to retired)
- **Special Note**: Explicitly dropped in downgrade with `op.execute("DROP TYPE IF EXISTS storage_bin_status_enum;")`
- **SQL Definition**: `sa.Enum('active', 'maintenance', 'retired', name='storage_bin_status_enum')`

---

## s3_images

**Table**: s3_images
**ENUMs**: 3

### content_type_enum
- **Column**: `content_type`
- **Values**: `'image/jpeg'`, `'image/png'`
- **Migration**: `440n457t9cnp_create_s3_images_table.py` (Line 52)
- **Default**: None
- **Nullable**: NO
- **MIME Types**: Standard image content types
- **SQL Definition**: `sa.Enum('image/jpeg', 'image/png', name='content_type_enum')`

### upload_source_enum
- **Column**: `upload_source`
- **Values**: `'web'`, `'mobile'`, `'api'`
- **Migration**: `440n457t9cnp_create_s3_images_table.py` (Line 88)
- **Default**: `'web'`
- **Nullable**: NO
- **SQL Definition**: `sa.Enum('web', 'mobile', 'api', name='upload_source_enum')`

### processing_status_enum
- **Column**: `status`
- **Values**: `'uploaded'`, `'processing'`, `'ready'`, `'failed'`
- **Migration**: `440n457t9cnp_create_s3_images_table.py` (Line 101)
- **Default**: `'uploaded'`
- **Nullable**: NO
- **Description**: Image processing lifecycle
- **SQL Definition**: `sa.Enum('uploaded', 'processing', 'ready', 'failed', name='processing_status_enum')`

---

## location_relationships

**Table**: location_relationships
**ENUMs**: 1

### relationshiptypeenum
- **Column**: `relationship_type`
- **Values**: `'contains'`, `'adjacent_to'`
- **Migration**: `8807863f7d8c_add_location_relationships_table.py` (Line 28)
- **Default**: None
- **Nullable**: NO
- **Description**: Hierarchical and adjacency relationships between storage locations
- **SQL Definition**: `sa.Enum('contains', 'adjacent_to', name='relationshiptypeenum')`

---

## photo_processing_sessions

**Table**: photo_processing_sessions
**ENUMs**: 1

### sessionstatusenum
- **Column**: `status`
- **Values**: `'pending'`, `'processing'`, `'completed'`, `'failed'`
- **Migration**: `9f8e7d6c5b4a_create_remaining_tables.py` (Line 172)
- **Default**: `'pending'`
- **Nullable**: NO
- **Description**: Photo processing session lifecycle
- **SQL Definition**: `sa.Enum('pending', 'processing', 'completed', 'failed', name='sessionstatusenum')`

---

## product_sample_images

**Table**: product_sample_images
**ENUMs**: 1

### sampletypeenum
- **Column**: `sample_type`
- **Values**: `'reference'`, `'growth_stage'`, `'quality_check'`, `'monthly_sample'`
- **Migration**: `9f8e7d6c5b4a_create_remaining_tables.py` (Line 201)
- **Default**: None
- **Nullable**: NO
- **Description**: Type of sample image for products at different stages
- **SQL Definition**: `sa.Enum('reference', 'growth_stage', 'quality_check', 'monthly_sample', name='sampletypeenum')`

---

## stock_movements

**Table**: stock_movements
**ENUMs**: 2

### movementtypeenum
- **Column**: `movement_type`
- **Values**: `'plantar'`, `'sembrar'`, `'transplante'`, `'muerte'`, `'ventas'`, `'foto'`, `'ajuste'`, `'manual_init'`
- **Migration**: `9f8e7d6c5b4a_create_remaining_tables.py` (Line 227)
- **Default**: None
- **Nullable**: NO
- **Description**: Type of stock movement (planting, sowing, transplant, death, sales, photo, adjustment, manual init)
- **Language**: Spanish + English acronyms
- **SQL Definition**: `sa.Enum('plantar', 'sembrar', 'transplante', 'muerte', 'ventas', 'foto', 'ajuste', 'manual_init', name='movementtypeenum')`

### sourcetypeenum
- **Column**: `source_type`
- **Values**: `'manual'`, `'ia'`
- **Migration**: `9f8e7d6c5b4a_create_remaining_tables.py` (Line 238)
- **Default**: None
- **Nullable**: NO
- **Description**: Source of movement (manual entry or IA/ML prediction)
- **SQL Definition**: `sa.Enum('manual', 'ia', name='sourcetypeenum')`

---

## estimations

**Table**: estimations
**ENUMs**: 1

### calculationmethodenum
- **Column**: `calculation_method`
- **Values**: `'band_estimation'`, `'density_estimation'`, `'grid_analysis'`
- **Migration**: `9f8e7d6c5b4a_create_remaining_tables.py` (Line 313)
- **Default**: None
- **Nullable**: NO
- **Description**: Method used to calculate plant count estimations
- **SQL Definition**: `sa.Enum('band_estimation', 'density_estimation', 'grid_analysis', name='calculationmethodenum')`

---

## Summary Statistics

| Statistic | Count |
|-----------|-------|
| Total Tables with ENUMs | 11 |
| Total ENUMs | 14 |
| Tables with 1 ENUM | 9 |
| Tables with 2 ENUMs | 1 (stock_movements) |
| Tables with 3 ENUMs | 1 (s3_images) |
| ENUMs with defaults | 5 |
| Required ENUMs (nullable=false) | 14 |
| Optional ENUMs (nullable=true) | 1 (position_enum) |

---

## Import Paths

When working with these ENUMs in Python models:

```python
# SQLAlchemy model column definitions
from sqlalchemy import Enum

# Example usage
warehouse_type = Column(
    Enum('greenhouse', 'shadehouse', 'open_field', 'tunnel', name='warehouse_type_enum'),
    nullable=False
)

# Pydantic schema definitions
from enum import Enum

class WarehouseType(str, Enum):
    GREENHOUSE = 'greenhouse'
    SHADEHOUSE = 'shadehouse'
    OPEN_FIELD = 'open_field'
    TUNNEL = 'tunnel'
```

---

**Last Updated**: 2025-10-21
**Created by**: ENUM Analysis Tool
**Status**: Complete and Verified
