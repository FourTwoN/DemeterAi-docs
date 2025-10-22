# Frontend Configuration View - Detailed Flow

## Purpose

Shows the frontend UI flow for administrators to view and configure storage locations in a
hierarchical, map-based interface.

## Scope

- **Level**: Frontend implementation detail
- **Audience**: Frontend developers, UX designers
- **Detail**: Complete UI flow with interactions
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete frontend flow including:

1. Hierarchical warehouse view
2. Storage location selection (single/bulk)
3. Configuration form display
4. Real-time validation
5. Submission and feedback

## UI Components

### 1. Warehouse Hierarchy Tree

```typescript
interface WarehouseNode {
    id: number;
    code: string;
    name: string;
    type: 'greenhouse' | 'shadehouse' | 'open_field';
    storageAreas: StorageAreaNode[];
}

interface StorageAreaNode {
    id: number;
    code: string;
    position: 'N' | 'S' | 'E' | 'W' | 'C';
    storageLocations: StorageLocationNode[];
}

interface StorageLocationNode {
    id: number;
    code: string;
    qr_code: string;
    currentConfig?: LocationConfig;
    hasWarning: boolean;  // No config
}
```

### 2. Configuration Form Component

```typescript
interface ConfigFormData {
    productCategory: number;  // cactus, suculenta, injerto
    productFamily: number;    // Filtered by category
    product: number;          // Filtered by family
    packagingType?: number;   // pot, tray, plug
    packaging?: number;       // Filtered by type
    expectedState: number;    // germinado, plantín, etc.
    area: number;             // Auto-calculated
    actionType: 'update' | 'create';
    notes?: string;
}
```

### 3. Bulk Selection Interface

```typescript
interface BulkSelection {
    selectedLocations: number[];  // Location IDs
    displayMode: 'list' | 'map';
    filters: {
        warehouse?: number;
        storageArea?: number;
        hasConfig?: boolean;
    };
}
```

## API Calls

### Load Warehouse Hierarchy

```typescript
async function loadWarehouseHierarchy(): Promise<WarehouseNode[]> {
    const response = await fetch('/api/admin/warehouses/hierarchy', {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.json();
}

// Response example:
[
    {
        id: 1,
        code: "WH-A",
        name: "Warehouse A",
        type: "greenhouse",
        storageAreas: [
            {
                id: 1,
                code: "SA-N",
                position: "N",
                storageLocations: [
                    {
                        id: 1,
                        code: "LOC-1-1-A",
                        qr_code: "QR001",
                        currentConfig: {
                            product: "Cactus Esférico",
                            packaging: "R7 Black",
                            state: "Ready to Sell"
                        },
                        hasWarning: false
                    },
                    {
                        id: 2,
                        code: "LOC-1-1-B",
                        currentConfig: null,
                        hasWarning: true  // No config
                    }
                ]
            }
        ]
    }
]
```

### Submit Configuration

```typescript
async function submitConfiguration(
    locationIds: number[],
    configData: ConfigFormData
): Promise<ConfigResponse> {
    const endpoint = configData.actionType === 'update'
        ? '/api/admin/storage-location-config/bulk-update'
        : '/api/admin/storage-location-config/bulk-create';

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
            location_ids: locationIds,
            product_id: configData.product,
            packaging_catalog_id: configData.packaging,
            expected_product_state_id: configData.expectedState,
            area_cm2: configData.area,
            notes: configData.notes
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
    }

    return response.json();
}
```

## User Interactions

### Single Location Configuration

1. User clicks on storage location node
2. Side panel opens showing:
    - Location details (code, QR, area)
    - Current configuration (if exists)
    - Configuration history link
3. User clicks "Edit Configuration"
4. Form appears with:
    - Pre-filled current values
    - Action type selector (Update/Create)
5. User modifies fields
6. Real-time validation shows errors
7. User clicks "Save"
8. Confirmation dialog appears
9. User confirms
10. API call made
11. Success notification shown
12. View refreshes with new config

### Bulk Configuration

1. User enables "Bulk select mode"
2. User clicks multiple locations (checkboxes appear)
3. Selected count shown: "25 locations selected"
4. User clicks "Configure Selected"
5. Bulk config form appears
6. Warning shown: "This will affect 25 locations"
7. User fills form
8. User selects action type (Update/Create)
9. User clicks "Apply to All"
10. Confirmation dialog lists all affected locations
11. User confirms
12. Progress bar shown (processing N of 25)
13. Success/error summary displayed
14. View refreshes

## Visual Indicators

### Location Node Badges

```typescript
function getLocationBadge(location: StorageLocationNode): BadgeConfig {
    if (!location.currentConfig) {
        return {
            icon: '⚠️',
            color: 'warning',
            tooltip: 'No configuration'
        };
    }

    const daysSinceUpdate = getDaysSince(location.currentConfig.updated_at);
    if (daysSinceUpdate > 90) {
        return {
            icon: 'ℹ️',
            color: 'info',
            tooltip: 'Config may be outdated'
        };
    }

    return {
        icon: '✓',
        color: 'success',
        tooltip: 'Configured'
    };
}
```

### Color Coding

- **Green**: Configured, up-to-date
- **Yellow**: Configured, may be outdated (> 90 days)
- **Red**: No configuration
- **Blue**: Recently updated (< 7 days)

## Responsive Design

### Desktop (> 1024px)

- Left panel: Warehouse tree
- Center panel: Map view (PostGIS polygons)
- Right panel: Configuration form/details

### Tablet (768px - 1024px)

- Collapsible tree
- Map or form (toggle)
- Bottom sheet for details

### Mobile (< 768px)

- Stacked layout
- List view (no map)
- Full-screen form

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
