# Storage Location Preview Cards - Key Metrics Display

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Map Warehouse Views
**Parent Flow:** 00_comprehensive_view

## Purpose

This subflow details the **storage location preview card** component displaying key metrics:
quantity, maceta type, value, última foto, increase/decrease indicators, and valor potencial.

## Scope

- **Level**: Component-level detail (Level 2.5 of 4)
- **Audience**: Frontend developers, UX designers
- **Detail**: Preview card layout, metrics calculation, visual indicators
- **Technology**: React component

## What It Represents

Each storage_location preview card provides a **quick overview** without requiring API calls:

- **Visual thumbnail**: Last photo from S3 (300x300px)
- **Current quantity**: Plant count with trend arrow (↑↓→)
- **Maceta type**: Primary container type
- **Financial metrics**: Current value and potential value
- **Category breakdown**: Cactus, suculenta, injerto counts
- **Status indicator**: Success/warning/error badge
- **Last updated**: Timestamp of última foto

## Preview Card Data Structure

```typescript
interface StorageLocationPreview {
  id: number;
  storage_area_id: number;
  warehouse_id: number;
  code: string;  // e.g., "WH-001-N-001"
  name: string;  // e.g., "Rack 1 Shelf 1"
  cantero_position: 'N' | 'S' | 'E' | 'W' | 'C';
  cantero_name: string;  // e.g., "Norte"
  preview: {
    // Quantity metrics
    current_quantity: number;  // From latest photo session
    previous_quantity: number;  // From previous photo session
    quantity_change: number;  // current - previous (can be negative)

    // Financial metrics
    current_value: number;  // quantity × cost_per_unit
    potential_value: number;  // current_value × 1.3 (30% growth estimate)

    // Quality and status
    quality_score: number;  // 0-100
    last_photo_date: string;  // ISO 8601
    last_photo_thumbnail_url: string;  // Presigned S3 URL

    // Container distribution
    maceta_primary: string;  // Most common maceta type ("10cm")
    maceta_distribution: {
      "8cm": number;
      "10cm": number;
      "12cm": number;
    };

    // Category breakdown
    category_counts: {
      "cactus": number;
      "suculenta": number;
      "injerto": number;
    };

    // Status
    status: string;  // "completed" | "processing" | "failed"
    error_message: string | null;
  };
}
```

## Component Implementation

### StorageLocationPreviewCard.tsx

```typescript
import React from 'react';
import { ArrowUp, ArrowDown, Minus, AlertCircle } from 'lucide-react';

interface Props {
  location: StorageLocationPreview;
  onClick: () => void;
}

export const StorageLocationPreviewCard: React.FC<Props> = ({ location, onClick }) => {
  const { preview } = location;

  // Handle case where no preview data exists
  if (!preview) {
    return (
      <div
        className="preview-card bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
        onClick={onClick}
      >
        <h3 className="font-bold text-lg">{location.name}</h3>
        <p className="text-sm text-gray-500">{location.code}</p>
        <p className="text-xs text-gray-400 mt-2">No data available</p>
      </div>
    );
  }

  // Trend indicator logic
  const getTrendIcon = () => {
    if (preview.quantity_change > 0) {
      return <ArrowUp className="text-green-500 w-4 h-4" />;
    }
    if (preview.quantity_change < 0) {
      return <ArrowDown className="text-red-500 w-4 h-4" />;
    }
    return <Minus className="text-gray-500 w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (preview.quantity_change > 0) return 'text-green-600';
    if (preview.quantity_change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const getTrendPercentage = () => {
    if (preview.previous_quantity === 0) return null;
    const percent = (preview.quantity_change / preview.previous_quantity) * 100;
    return Math.abs(percent).toFixed(1);
  };

  // Status badge logic
  const getStatusBadge = () => {
    if (preview.error_message) {
      return (
        <span className="badge badge-error badge-sm flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          Error
        </span>
      );
    }
    if (preview.status === 'completed') {
      return <span className="badge badge-success badge-sm">OK</span>;
    }
    if (preview.status === 'processing') {
      return <span className="badge badge-warning badge-sm">Processing</span>;
    }
    return <span className="badge badge-secondary badge-sm">Pending</span>;
  };

  // Quality score color
  const getQualityColor = () => {
    if (preview.quality_score >= 80) return 'text-green-600';
    if (preview.quality_score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  // Calculate ROI percentage
  const roiPercent = preview.current_value > 0
    ? ((preview.potential_value - preview.current_value) / preview.current_value * 100).toFixed(0)
    : 0;

  return (
    <div
      className="preview-card bg-white rounded-lg shadow hover:shadow-xl transition-all cursor-pointer overflow-hidden border border-gray-200 hover:border-blue-400"
      onClick={onClick}
    >
      {/* Thumbnail Image */}
      <div className="card-image relative h-48 bg-gray-100">
        {preview.last_photo_thumbnail_url ? (
          <img
            src={preview.last_photo_thumbnail_url}
            alt={location.name}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.src = '/placeholder-image.png';
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <span>No photo</span>
          </div>
        )}

        {/* Overlay badges */}
        <div className="absolute top-2 left-2 right-2 flex justify-between items-start">
          <span className="badge badge-primary badge-sm font-mono">
            {location.code}
          </span>
          {getStatusBadge()}
        </div>

        {/* Cantero position indicator */}
        <div className="absolute bottom-2 left-2">
          <span className="badge badge-sm bg-black bg-opacity-50 text-white border-0">
            {location.cantero_name}
          </span>
        </div>
      </div>

      {/* Card Content */}
      <div className="card-content p-4">
        {/* Title */}
        <h3 className="font-bold text-lg truncate" title={location.name}>
          {location.name}
        </h3>

        {/* Metrics Grid */}
        <div className="metrics-grid grid grid-cols-2 gap-3 mt-3">
          {/* Quantity with Trend */}
          <div className="metric">
            <label className="text-xs text-gray-500 block mb-1">Quantity</label>
            <div className="flex items-center gap-1">
              <span className="text-2xl font-bold">{preview.current_quantity}</span>
              {getTrendIcon()}
              <div className="flex flex-col text-xs">
                <span className={getTrendColor()}>
                  {preview.quantity_change > 0 ? '+' : ''}{preview.quantity_change}
                </span>
                {getTrendPercentage() && (
                  <span className={getTrendColor()}>
                    ({getTrendPercentage()}%)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Maceta Type */}
          <div className="metric">
            <label className="text-xs text-gray-500 block mb-1">Maceta</label>
            <span className="text-xl font-bold">{preview.maceta_primary || 'N/A'}</span>
            {preview.maceta_distribution && (
              <div className="text-xs text-gray-500">
                {Object.keys(preview.maceta_distribution).length} types
              </div>
            )}
          </div>

          {/* Current Value */}
          <div className="metric">
            <label className="text-xs text-gray-500 block mb-1">Current Value</label>
            <span className="text-base font-semibold">
              {formatCurrency(preview.current_value)}
            </span>
          </div>

          {/* Potential Value */}
          <div className="metric">
            <label className="text-xs text-gray-500 block mb-1">
              Potential (+{roiPercent}%)
            </label>
            <span className="text-base font-semibold text-green-600">
              {formatCurrency(preview.potential_value)}
            </span>
          </div>
        </div>

        {/* Category Breakdown */}
        {preview.category_counts && Object.keys(preview.category_counts).length > 0 && (
          <div className="category-breakdown mt-3 pt-3 border-t border-gray-200">
            <label className="text-xs text-gray-500 block mb-1">Categories</label>
            <div className="flex gap-2 flex-wrap">
              {Object.entries(preview.category_counts).map(([category, count]) => (
                <span
                  key={category}
                  className="badge badge-outline badge-xs capitalize"
                >
                  {category}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Quality Score */}
        {preview.quality_score !== null && (
          <div className="quality-score mt-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Quality Score</span>
              <span className={`font-bold ${getQualityColor()}`}>
                {preview.quality_score.toFixed(1)}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
              <div
                className={`h-1.5 rounded-full ${
                  preview.quality_score >= 80
                    ? 'bg-green-600'
                    : preview.quality_score >= 60
                    ? 'bg-yellow-600'
                    : 'bg-red-600'
                }`}
                style={{ width: `${preview.quality_score}%` }}
              />
            </div>
          </div>
        )}

        {/* Footer - Last Updated */}
        <div className="footer mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
          <span>
            Updated: {preview.last_photo_date
              ? new Date(preview.last_photo_date).toLocaleDateString('es-AR', {
                  day: '2-digit',
                  month: 'short',
                  year: 'numeric'
                })
              : 'Never'}
          </span>
          {preview.error_message && (
            <span className="text-red-600 text-xs truncate max-w-[120px]" title={preview.error_message}>
              {preview.error_message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
```

## Visual Design Specifications

### Card Dimensions

- **Width**: Responsive (flex/grid layout)
- **Height**: Auto (content-driven)
- **Image height**: 192px (h-48)
- **Padding**: 16px (p-4)
- **Border radius**: 8px (rounded-lg)

### Color Scheme

```css
/* Status badges */
.badge-success { background: #10B981; color: white; }  /* Green - OK */
.badge-warning { background: #F59E0B; color: white; }  /* Amber - Warning */
.badge-error { background: #EF4444; color: white; }    /* Red - Error */

/* Trend indicators */
.trend-positive { color: #16A34A; }  /* Green arrow up */
.trend-negative { color: #DC2626; }  /* Red arrow down */
.trend-neutral { color: #6B7280; }   /* Gray minus */

/* Quality score bars */
.quality-high { background: #10B981; }    /* Green >= 80 */
.quality-medium { background: #F59E0B; }  /* Yellow 60-79 */
.quality-low { background: #EF4444; }     /* Red < 60 */
```

### Typography

- **Card title**: font-bold text-lg (18px)
- **Metric labels**: text-xs text-gray-500 (12px)
- **Metric values**: text-2xl font-bold (24px) for quantity, text-base (16px) for currency
- **Footer**: text-xs (12px)

### Hover Effects

```css
.preview-card:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  border-color: #60A5FA;  /* Blue-400 */
  transform: translateY(-2px);
  transition: all 0.2s ease-in-out;
}
```

## Metrics Calculation

### Quantity Change

```typescript
// Calculated in materialized view
quantity_change = current_quantity - previous_quantity

// Trend indicator
if (quantity_change > 0) → Arrow Up (Green)
if (quantity_change < 0) → Arrow Down (Red)
if (quantity_change === 0) → Minus (Gray)

// Percentage change
percent_change = (quantity_change / previous_quantity) × 100
```

### Potential Value

```typescript
// 30% growth estimate (configurable per product type)
potential_value = current_value × 1.3

// ROI percentage
roi_percent = ((potential_value - current_value) / current_value) × 100
```

### Quality Score

```typescript
// Weighted average from stock_batches
quality_score = AVG(stock_batches.quality_score)
WHERE current_storage_bin_id = storage_location_id

// Color coding
if (quality_score >= 80) → Green (excellent)
if (quality_score >= 60) → Yellow (good)
if (quality_score < 60) → Red (needs attention)
```

### Primary Maceta Type

```typescript
// Most common maceta type
maceta_primary = MODE(packaging_catalog.name)
FROM stock_batches
WHERE current_storage_bin_id = storage_location_id
GROUP BY packaging_catalog_id
ORDER BY COUNT(*) DESC
LIMIT 1
```

## Performance Considerations

### Image Loading

- **Lazy loading**: Images load as they scroll into view
- **Placeholder**: Show gray box with "No photo" text while loading
- **Error handling**: Fallback to placeholder image if S3 URL fails
- **Presigned URLs**: Valid for 1 hour, generated during bulk-load

### Rendering Optimization

- **React.memo**: Memoize component to prevent unnecessary re-renders
- **Virtualization**: Use `react-window` for 500+ cards
- **Debounced filtering**: Debounce search input to reduce re-renders

```typescript
export const StorageLocationPreviewCard = React.memo<Props>(
  ({ location, onClick }) => {
    // Component implementation
  },
  (prevProps, nextProps) => {
    // Only re-render if location.id or preview data changed
    return prevProps.location.id === nextProps.location.id &&
           prevProps.location.preview === nextProps.location.preview;
  }
);
```

## Accessibility

### ARIA Labels

```tsx
<div
  className="preview-card"
  onClick={onClick}
  role="button"
  tabIndex={0}
  aria-label={`View details for ${location.name}`}
  onKeyPress={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      onClick();
    }
  }}
>
```

### Keyboard Navigation

- **Tab**: Focus card
- **Enter/Space**: Click card to view detail
- **Arrow keys**: Navigate between cards (optional)

### Screen Reader Support

- **Alt text**: Descriptive alt text for images
- **ARIA labels**: Clear labels for interactive elements
- **Status announcements**: Announce filter/sort changes

## Related Subflows

- **02_warehouse_internal_structure.md**: Parent view containing preview cards grid
- **04_storage_location_detail.md**: Next level - full detail view on card click
- **05_historical_timeline.md**: Historical data available from detail view

## Version History

| Version | Date       | Changes                                      |
|---------|------------|----------------------------------------------|
| 1.0.0   | 2025-10-08 | Initial preview card component specification |

---

**Notes:**

- Preview cards designed for quick scanning of key metrics
- No API calls needed - all data from bulk-load response
- Trend indicators provide instant insight into quantity changes
- Color-coded status badges for quick error identification
- Responsive grid layout adapts to screen size
- Lazy image loading optimizes performance for large datasets
