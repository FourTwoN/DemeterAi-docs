# Storage Location Configuration System - Overview

## Purpose

This diagram provides an **executive-level view** of the Storage Location Configuration System, showing how administrators can configure and update the expected product/packaging combinations for storage locations (claros).

## Scope

- **Level**: High-level architectural overview
- **Audience**: Product managers, administrators, business analysts
- **Detail**: Simplified flow showing configuration management paths
- **Mermaid Version**: v11.3.0+ (using modern syntax)

## What It Represents

The diagram illustrates two main configuration approaches:

1. **Update Existing Configuration (UPDATE)**:
   - Modify current active configuration
   - **Impacts current stock immediately**
   - Use when: Product/packaging changed but same crop cycle
   - Example: Changed pot color from black to white

2. **Create New Configuration (CREATE)**:
   - Create new configuration, preserve historical
   - **Does NOT impact historical stock**
   - Use when: Complete crop change, new cultivation cycle
   - Example: Sold all cactus, now planting succulents

## Business Context

### Storage Location Config Purpose

Each storage location (claro) has a `storage_location_config` that defines:
- **Expected Product**: Which plant species should be there
- **Expected Packaging**: Which pot type/size should be used
- **Expected State**: What growth stage is expected
- **Area**: Physical area of the location

This configuration is used by the ML system to:
- Validate detection results
- Calculate expected vs actual quantities
- Identify configuration mismatches
- Track cultivation plan compliance

### Historical Integrity Principle

**Critical Rule**: Historical data must remain **immutable**.

When a photo is taken on Sept 1st and stock is calculated, that stock record is **frozen in time**. Any future configuration changes should NOT affect that historical record.

#### Timeline Example

```
Sept 1: Photo taken → Stock A calculated (500 cactus in R7)
        Config 1: {product: cactus, packaging: R7}

Sept - Nov: Sales occur, transplants happen
           All operations reference Config 1

Dec 1: Sold everything, replanting with succulents
       User creates Config 2: {product: suculenta, packaging: R10}
       Photo taken → Stock B calculated (300 suculenta in R10)

Historical query for Sept-Nov period:
→ Still uses Config 1 (cactus + R7)

Current query (Dec onwards):
→ Uses Config 2 (suculenta + R10)
```

### UPDATE vs CREATE Decision Matrix

| Scenario | Action | Impact | Use Case |
|----------|--------|--------|----------|
| Pot color changed | UPDATE | Current stock updated | Aesthetic change |
| Pot size changed | UPDATE | Current stock updated | Same plants, different pots |
| Plant species changed completely | CREATE | New stock period starts | New cultivation cycle |
| Sold all stock, replanting | CREATE | Preserve sales history | Major crop change |
| Fixed configuration error | UPDATE | Correct current data | Data quality fix |

## Database Tables Involved

### Primary Table

```sql
storage_location_config (
    id SERIAL PRIMARY KEY,
    storage_location_id INT REFERENCES storage_locations(id),
    product_id INT REFERENCES products(id),
    packaging_catalog_id INT REFERENCES packaging_catalog(id) NULLABLE,
    expected_product_state_id INT REFERENCES product_states(id),
    area_cm2 NUMERIC,
    active BOOLEAN DEFAULT true,  -- Only one active config per location
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

-- Constraint: Only one active config per storage_location_id
CREATE UNIQUE INDEX idx_active_config_per_location
ON storage_location_config (storage_location_id)
WHERE active = true;
```

### Related Tables

```sql
storage_locations (id, storage_area_id, code, qr_code, geojson_coordinates)
products (id, family_id, sku, common_name)
product_families (id, category_id, name)
product_categories (id, code, name)  -- cactus, suculenta, injerto
packaging_catalog (id, packaging_type_id, sku, name, volume_liters)
product_states (id, code, name, is_sellable)  -- germinado, plantín, ready_to_sell
```

## User Interface Overview

### Admin Configuration View

The frontend provides a hierarchical view:

```
Warehouse A
├── Cantero Norte
│   ├── Claro 1-1-A [Config: Cactus + R7 Black]
│   ├── Claro 1-1-B [Config: Suculenta + R10 White]
│   └── Claro 1-1-C [⚠️ No config]
├── Cantero Sur
│   └── ...
```

### Configuration Form

When configuring a storage location:

**Fields**:
1. **Product Selection** (required)
   - Category: Dropdown (Cactus, Suculenta, Injerto)
   - Family: Cascading dropdown (filtered by category)
   - Product: Cascading dropdown (filtered by family)

2. **Packaging Selection** (optional)
   - Type: Dropdown (Pot, Tray, Plug)
   - Catalog: Cascading dropdown (R7, R10, R12, etc.)
   - Color: Dropdown

3. **Expected State** (required)
   - Germinado, Plantín, Ready to Sell, etc.

4. **Area** (auto-calculated from geojson, but can override)

5. **Action Type**
   - Radio button: **Update existing** vs **Create new**
   - Help text explains impact

6. **Notes** (optional)

### Bulk Configuration

Admin can select multiple storage locations and apply same config:

```
Selected: 25 storage locations in Cantero Norte

Apply configuration:
[Product: Cactus Esférico]
[Packaging: R7 Black]
[State: Ready to Sell]

(•) Update existing configurations (affects current stock)
( ) Create new configurations (preserve history)

[Apply to All]
```

## Related Detailed Diagrams

For implementation-level details, see:

- **Update Existing Config**: `flows/location_config/01_update_existing_config.mmd`
- **Create New Config**: `flows/location_config/02_create_new_config.mmd`
- **Frontend Configuration View**: `flows/location_config/03_frontend_configuration_view.mmd`

## How It Fits in the System

The Configuration System is a **foundational management layer** that:

- Defines expected cultivation plan
- Enables ML validation (actual vs expected)
- Supports historical accuracy
- Facilitates warehouse management
- Enables analytics and reporting

Configuration changes are **metadata operations** - they describe what SHOULD be in a location, not what IS there (that comes from photos).

## Workflow Summary

1. **Admin** navigates to configuration management view
2. **Select** one or more storage locations
3. **Choose** configuration mode:
   - Update: Modify current without creating history
   - Create: New config, preserve existing as historical
4. **Fill form** with product, packaging, state, area
5. **Submit** changes
6. **System** validates and applies:
   - Update: Sets `updated_at`, modifies fields
   - Create: Sets old config `active=false`, inserts new with `active=true`
7. **Frontend** refreshes view showing new configuration
8. **Future photos** use new configuration for validation

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
