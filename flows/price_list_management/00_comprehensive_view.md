# Price List Management System - Overview

## Purpose

This diagram provides an **executive-level view** of the Price List Management System, showing how
administrators can manage product catalogs, packaging catalogs, and price lists with support for
bulk operations.

## Scope

- **Level**: High-level architectural overview
- **Audience**: Product managers, administrators, business analysts
- **Detail**: Simplified flow showing catalog management and pricing operations
- **Mermaid Version**: v11.3.0+ (using modern syntax)

## What It Represents

The diagram illustrates the complete price list management system with four main components:

1. **Packaging Catalog Management (CRUD)**:
    - Create, Read, Update, Delete packaging items
    - Macetas: R7, R10, R12, R14, R17, R19, R21
    - Attributes: Type, material, color, dimensions, volume
    - SKU generation and management

2. **Product Catalog Management (CRUD)**:
    - Manage product categories (cactus, suculenta, injerto)
    - Manage product families within categories
    - Manage individual products
    - Scientific and common names
    - Hierarchical structure: Category → Family → Product

3. **Price List Management**:
    - Combine packaging + product category
    - Set wholesale and retail prices
    - Define SKU, units per storage box
    - Calculate total prices per box
    - Set availability status
    - Track discount factors

4. **Bulk Edit Operations**:
    - Increase/decrease all prices by percentage
    - Change availability for categories
    - Update discount factors
    - Apply changes to filtered subsets
    - **Important**: Only affects latest active stock

## Business Context

### Price List Purpose

The `price_list` table is the **client-facing catalog** that combines:

- **What**: Product category (type of plant)
- **How**: Packaging type (what it comes in)
- **Price**: Wholesale and retail pricing
- **Logistics**: Units per box, total box price

This is NOT the internal stock system - it's the **sales catalog** that customers see.

### Historical Integrity Principle

**Critical Rule**: Price changes and bulk operations only affect **current/future prices**.

Historical sales and stock records maintain their original pricing information. When prices are
updated, the changes apply to:

- Current price list view
- New quotes and orders
- Future stock valuations

But NOT to:

- Historical sales records
- Past invoices
- Archived stock valuations

#### Timeline Example

```
Jan 1: Price List A created
       Cactus + R7 = $5.00 wholesale / $8.00 retail

Jan - Mar: Sales occur at these prices
           All invoices reference original prices

Apr 1: Bulk operation: Increase all prices by 10%
       Cactus + R7 = $5.50 wholesale / $8.80 retail

Historical query for Jan-Mar invoices:
→ Still shows $5.00 / $8.00 (original prices)

New quote created Apr 2:
→ Uses new prices $5.50 / $8.80
```

## Database Tables Involved

### Primary Tables

```sql
price_list (
    id SERIAL PRIMARY KEY,
    packaging_catalog_id INT REFERENCES packaging_catalog(id),
    product_categories_id INT REFERENCES product_categories(id),
    wholesale_unit_price INT,  -- Price in cents
    retail_unit_price INT,     -- Price in cents
    SKU VARCHAR(50) UNIQUE,
    unit_per_storage_box INT,
    wholesale_total_price_per_box INT,  -- Calculated field
    observations TEXT,
    availability VARCHAR(20),   -- available, out_of_stock, discontinued
    updated_at TIMESTAMP,
    discount_factor INT         -- Percentage 0-100
)

packaging_catalog (
    id SERIAL PRIMARY KEY,
    packaging_type_id INT REFERENCES packaging_types(id),
    packaging_material_id INT REFERENCES packaging_materials(id),
    packaging_color_id INT REFERENCES packaging_colors(id),
    sku VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    volume_liters NUMERIC(8,2),
    diameter_cm NUMERIC(6,2),
    height_cm NUMERIC(6,2)
)

product_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE,
    name VARCHAR(100)  -- cactus, suculenta, injerto
)

product_families (
    id SERIAL PRIMARY KEY,
    category_id INT REFERENCES product_categories(id),
    name VARCHAR(100),
    scientific_name VARCHAR(200)
)

products (
    id SERIAL PRIMARY KEY,
    family_id INT REFERENCES product_families(id),
    sku VARCHAR(50) UNIQUE,
    common_name VARCHAR(100),
    scientific_name VARCHAR(200),
    description TEXT
)
```

### Constraint: Unique Combination

```sql
-- Each packaging + category combination can only exist once
CREATE UNIQUE INDEX idx_unique_price_list_combo
ON price_list (packaging_catalog_id, product_categories_id);
```

## User Interface Overview

### Admin Price List View

The frontend provides a comprehensive catalog management interface:

```
PRICE LIST MANAGEMENT
├── Packaging Catalog
│   ├── Macetas (Pots)
│   │   ├── R7 Black - Ø7cm, 0.2L [Edit] [Delete]
│   │   ├── R10 White - Ø10cm, 0.5L [Edit] [Delete]
│   │   └── R12 Black - Ø12cm, 0.8L [Edit] [Delete]
│   ├── Bandejas (Trays)
│   └── Plugs
│
├── Product Catalog
│   ├── Cactus
│   │   ├── Cactus Esféricos
│   │   │   └── Echinocactus grusonii [Edit]
│   │   └── Cactus Columnares
│   ├── Suculentas
│   └── Injertos
│
└── Price List
    ├── Cactus + R7 Black
    │   ├── Wholesale: $5.00 | Retail: $8.00
    │   ├── SKU: CACT-R7-BLK
    │   ├── Units/Box: 50 | Box Total: $250.00
    │   └── Status: Available [Edit]
    ├── Suculenta + R10 White
    └── Injerto + R12 Black

[+ New Packaging] [+ New Product] [+ New Price Entry]
[Bulk Operations ▼]
```

### Price List Form

When creating/editing a price list entry:

**Fields**:

1. **Product Category** (required)
    - Dropdown: Cactus, Suculenta, Injerto

2. **Packaging** (required)
    - Cascading dropdown filtered by type
    - Shows: SKU, Name, Dimensions

3. **Pricing** (required)
    - Wholesale Unit Price (in cents)
    - Retail Unit Price (in cents)
    - Auto-validate: retail >= wholesale

4. **Logistics**
    - SKU (auto-generated or manual)
    - Units per Storage Box
    - Total Price per Box (auto-calculated)

5. **Status**
    - Availability: Available / Out of Stock / Discontinued
    - Discount Factor (0-100%)
    - Observations (free text)

### Bulk Operations Panel

```
BULK EDIT OPERATIONS

Select Operation:
( ) Increase prices by percentage
( ) Decrease prices by percentage
(•) Change availability status
( ) Update discount factors

Filters:
[x] Apply to specific category: [Cactus ▼]
[x] Apply to specific packaging type: [Macetas ▼]
[ ] Apply to price range: $__ to $__

Preview Changes: 25 items will be affected
[Preview] [Apply] [Cancel]

⚠️ Warning: This will only affect current price list.
   Historical sales data will remain unchanged.
```

## Workflow Summary

### Creating a New Price List Entry

1. **Admin** navigates to Price List Management
2. **Click** "New Price Entry"
3. **Select** Product Category (e.g., Cactus)
4. **Select** Packaging (e.g., R7 Black)
5. **Enter** Wholesale Price: $5.00
6. **Enter** Retail Price: $8.00
7. **Set** Units per Box: 50
8. **System** auto-calculates: Total per Box = $250.00
9. **Set** Availability: Available
10. **Submit** → Entry created

### Bulk Price Increase

1. **Admin** clicks "Bulk Operations"
2. **Select** "Increase prices by percentage"
3. **Enter** 10%
4. **Filter** by Category: Cactus
5. **Preview** shows 15 items affected
6. **Review** changes:
    - Cactus + R7: $5.00 → $5.50
    - Cactus + R10: $7.00 → $7.70
7. **Apply** changes
8. **System** updates all matching entries
9. **Log** audit trail with timestamp

## Related Detailed Diagrams

For implementation-level details, see:

- **Packaging Catalog CRUD**: `flows/price_list_management/01_packaging_catalog_crud.mmd`
- **Product Catalog CRUD**: `flows/price_list_management/02_product_catalog_crud.mmd`
- **Price List Management**: `flows/price_list_management/03_price_list_management.mmd`
- **Bulk Edit Operations**: `flows/price_list_management/04_bulk_edit_operations.mmd`

## How It Fits in the System

The Price List Management System is a **catalog management layer** that:

- Defines what products are available for sale
- Sets pricing for different packaging options
- Enables quick price adjustments through bulk operations
- Maintains catalog consistency across the system
- Supports sales, quotations, and order processing

Price list data is **referenced** by:

- Quote generation system
- Order processing
- Invoice creation
- Stock valuation (current prices)
- Sales analytics

## Use Cases

### Catalog Manager

- "Add new maceta size R14 to packaging catalog"
- "Create price entries for all cactus + maceta combinations"
- "Update retail prices for the new season"

### Sales Manager

- "Increase all wholesale prices by 8% for 2025"
- "Mark all R7 products as out of stock temporarily"
- "Apply 10% discount factor to succulentas category"

### Operations Manager

- "Update units per box from 50 to 48 for R10 macetas"
- "Change availability status for discontinued packaging"
- "Review and update all SKUs for consistency"

## Technical Highlights

### Price Calculation

All prices stored in **cents** (integer) to avoid floating-point errors:

```python
# Storing prices
wholesale_price_cents = int(5.00 * 100)  # $5.00 = 500 cents
retail_price_cents = int(8.00 * 100)     # $8.00 = 800 cents

# Displaying prices
display_price = wholesale_price_cents / 100  # 500 → $5.00
```

### SKU Generation

Auto-generate SKUs following pattern:

```
{CATEGORY_CODE}-{PACKAGING_CODE}-{COLOR_CODE}

Examples:
- CACT-R7-BLK (Cactus + R7 Black)
- SUCC-R10-WHT (Suculenta + R10 White)
- INJT-R12-BLK (Injerto + R12 Black)
```

### Bulk Operations Performance

Bulk operations use efficient batch updates:

```sql
-- Instead of N individual UPDATEs
-- Use single UPDATE with WHERE IN

UPDATE price_list
SET
    wholesale_unit_price = FLOOR(wholesale_unit_price * 1.10),
    retail_unit_price = FLOOR(retail_unit_price * 1.10),
    wholesale_total_price_per_box = FLOOR(wholesale_unit_price * 1.10) * unit_per_storage_box,
    updated_at = NOW()
WHERE product_categories_id = $1
RETURNING id;

-- Performance: ~50ms for 100 items vs 5000ms individual updates
```

### Data Validation

**Critical Validations**:

1. **Price Integrity**
    - Retail price >= Wholesale price
    - Prices > 0
    - Total box price = unit price × units per box

2. **Unique Constraints**
    - No duplicate packaging + category combinations
    - Unique SKUs across entire price list

3. **Reference Integrity**
    - Packaging must exist in packaging_catalog
    - Category must exist in product_categories
    - All foreign keys valid

## API Endpoints Summary

### Packaging Catalog

- `GET /api/admin/packaging-catalog` - List all packaging
- `POST /api/admin/packaging-catalog` - Create new packaging
- `PUT /api/admin/packaging-catalog/{id}` - Update packaging
- `DELETE /api/admin/packaging-catalog/{id}` - Delete packaging

### Product Catalog

- `GET /api/admin/product-categories` - List categories
- `GET /api/admin/product-families` - List families
- `GET /api/admin/products` - List products
- `POST /api/admin/products` - Create product
- `PUT /api/admin/products/{id}` - Update product

### Price List

- `GET /api/admin/price-list` - List all prices
- `POST /api/admin/price-list` - Create price entry
- `PUT /api/admin/price-list/{id}` - Update price entry
- `DELETE /api/admin/price-list/{id}` - Delete price entry

### Bulk Operations

- `POST /api/admin/price-list/bulk-update-prices` - Bulk price changes
- `POST /api/admin/price-list/bulk-update-availability` - Bulk availability
- `POST /api/admin/price-list/bulk-update-discount` - Bulk discounts

## Performance Targets

| Operation              | Target Time | Notes               |
|------------------------|-------------|---------------------|
| List price entries     | < 200ms     | Paginated, 50 items |
| Create price entry     | < 100ms     | With validation     |
| Update price entry     | < 100ms     | Single item         |
| Bulk update 100 items  | < 500ms     | Single transaction  |
| Bulk update 1000 items | < 2s        | Batched if needed   |

## Security Considerations

### Access Control

Only **admin users** can:

- Modify packaging catalog
- Modify product catalog
- Create/update price list entries
- Execute bulk operations

**Supervisor** users can:

- View all catalogs (read-only)
- Export price lists

**Viewer** users can:

- View published price lists only

### Audit Logging

All modifications logged:

- User ID
- Timestamp
- Operation type (create/update/delete/bulk)
- Changes made (before/after values)
- Affected item count (for bulk ops)

### Rate Limiting

Bulk operations limited to:

- Max 1000 items per operation
- Max 10 bulk operations per user per hour
- Requires confirmation for operations affecting > 100 items

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
