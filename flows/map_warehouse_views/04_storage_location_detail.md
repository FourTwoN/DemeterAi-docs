# Storage Location Detail View - Full Information Display

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Map Warehouse Views
**Parent Flow:** 00_comprehensive_view

## Purpose

This subflow details the **full storage_location detail view** displaying processed image, detections, quantity by category, empty containers, financial data, maceta types, quality score, and optional graphs.

## Scope

- **Level**: Detailed subflow (Level 3 of 4)
- **Audience**: Developers, UX designers
- **Detail**: Detail view layout, API endpoint, data fetching strategy
- **Technology**: React, REST API, on-demand loading

## What It Represents

The storage_location detail view provides **comprehensive information** when user clicks a preview card:

1. **User clicks preview card** → Triggers API call
2. **Fetch detail data** → `/api/v1/storage-locations/{id}/detail` (~300ms)
3. **Display full information**:
   - Processed image with ML detections
   - Detection results by category
   - Empty containers count
   - Financial metrics (price, cost, potential value)
   - Maceta type distribution
   - Quality score with optional graphs
4. **Navigation options**: Configure, View Analytics, View History

## Data Structure

```typescript
interface StorageLocationDetail {
  storage_location: {
    id: number;
    code: string;
    name: string;
    description: string;
    storage_area: {
      id: number;
      code: string;
      name: string;
      position: string;
    };
    warehouse: {
      id: number;
      code: string;
      name: string;
    };
    active: boolean;
  };

  latest_session: {
    session_id: string;
    processed_image_url: string;  // S3 URL with annotations
    original_image_url: string;  // S3 URL original
    created_at: string;  // ISO 8601
    total_detected: number;
    total_estimated: number;
    total_empty_containers: number;
    avg_confidence: number;  // 0.0 to 1.0
    category_counts: {
      cactus: number;
      suculenta: number;
      injerto: number;
    };
    validated: boolean;
    validated_by: string;
    validation_date: string;
  };

  detections: Array<{
    id: number;
    category: string;
    bbox: { x: number; y: number; width: number; height: number };
    confidence: number;
    product_id: number;
    product_name: string;
  }>;

  stock_summary: {
    total_quantity: number;
    total_value: number;
    potential_value: number;
    avg_quality_score: number;
    maceta_distribution: Record<string, number>;
    cost_per_unit_avg: number;
  };

  financial: {
    current_price_per_unit: number;
    total_cost: number;
    potential_revenue: number;
    roi_percent: number;
  };

  quality_metrics: {
    overall_score: number;
    health_score: number;
    growth_rate_percent: number;
    mortality_rate_percent: number;
  };
}
```

## API Endpoint

### GET /api/v1/storage-locations/{id}/detail

**Request:**
```http
GET /api/v1/storage-locations/1/detail HTTP/1.1
Authorization: Bearer <token>
```

**Response:** (See data structure above)

**Performance:**
- **Response time target**: < 300ms
- **Cache**: Redis TTL 1 hour
- **Invalidation**: On new photo processing completion
- **Fetch strategy**: On-demand (only when user clicks preview card)

## Component Implementation

```typescript
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, Settings, TrendingUp, History } from 'lucide-react';

export const StorageLocationDetail: React.FC = () => {
  const { locationId } = useParams<{ locationId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<StorageLocationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const response = await fetch(`/api/v1/storage-locations/${locationId}/detail`, {
          headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        setDetail(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchDetail();
  }, [locationId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
        <span className="ml-2">Loading detail...</span>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="alert alert-error">
          <p>Error: {error || 'Not found'}</p>
          <button onClick={() => navigate(-1)} className="btn btn-sm">Go Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="storage-location-detail bg-gray-50 min-h-screen">
      {/* Header */}
      <header className="bg-white shadow p-4 mb-4">
        <button onClick={() => navigate(-1)} className="text-blue-600 mb-2">← Back</button>
        <h1 className="text-2xl font-bold">{detail.storage_location.name}</h1>
        <p className="text-gray-600">
          {detail.storage_location.code} · {detail.storage_location.warehouse.name} ·{' '}
          {detail.storage_location.storage_area.name}
        </p>
      </header>

      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Image */}
          <div className="image-section">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-bold mb-4">Processed Image</h2>
              <div className="relative">
                {!imageLoaded && (
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                    <Loader2 className="w-8 h-8 animate-spin" />
                  </div>
                )}
                <img
                  src={detail.latest_session.processed_image_url}
                  alt="Processed"
                  className="w-full rounded-lg shadow-lg"
                  onLoad={() => setImageLoaded(true)}
                />
              </div>
              <div className="mt-2 text-sm text-gray-600">
                Captured: {new Date(detail.latest_session.created_at).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Right: Details */}
          <div className="details-section space-y-4">
            {/* Detection Results */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-bold mb-4">Detection Results</h2>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(detail.latest_session.category_counts).map(([category, count]) => (
                  <div key={category} className="stat-card text-center">
                    <div className="text-3xl font-bold text-blue-600">{count}</div>
                    <div className="text-sm text-gray-600 capitalize">{category}</div>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Total Detected:</span>
                  <span className="font-bold ml-2">{detail.latest_session.total_detected}</span>
                </div>
                <div>
                  <span className="text-gray-600">Empty Containers:</span>
                  <span className="font-bold ml-2">{detail.latest_session.total_empty_containers}</span>
                </div>
                <div>
                  <span className="text-gray-600">Avg Confidence:</span>
                  <span className="font-bold ml-2">
                    {(detail.latest_session.avg_confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Validated:</span>
                  <span className={`font-bold ml-2 ${detail.latest_session.validated ? 'text-green-600' : 'text-yellow-600'}`}>
                    {detail.latest_session.validated ? 'Yes' : 'Pending'}
                  </span>
                </div>
              </div>
            </div>

            {/* Financial Information */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-bold mb-4">Financial Information</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="stat-card">
                  <div className="text-sm text-gray-600">Current Value</div>
                  <div className="text-2xl font-bold text-green-600">
                    ${detail.stock_summary.total_value.toFixed(2)}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="text-sm text-gray-600">Potential Value</div>
                  <div className="text-2xl font-bold text-blue-600">
                    ${detail.stock_summary.potential_value.toFixed(2)}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="text-sm text-gray-600">Price/Unit</div>
                  <div className="text-lg font-bold">
                    ${detail.financial.current_price_per_unit.toFixed(2)}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="text-sm text-gray-600">ROI</div>
                  <div className="text-lg font-bold text-green-600">
                    +{detail.financial.roi_percent.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Maceta Distribution */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-bold mb-4">Container Distribution</h2>
              <div className="flex flex-wrap gap-3">
                {Object.entries(detail.stock_summary.maceta_distribution).map(([size, count]) => (
                  <div key={size} className="badge badge-lg badge-outline">
                    {size}: {count}
                  </div>
                ))}
              </div>
            </div>

            {/* Quality Metrics */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-bold mb-4">Quality Metrics</h2>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Overall Score</span>
                    <span className="font-bold">{detail.quality_metrics.overall_score.toFixed(1)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${detail.quality_metrics.overall_score}%` }}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Health Score:</span>
                    <span className="font-bold ml-2">{detail.quality_metrics.health_score.toFixed(1)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Growth Rate:</span>
                    <span className="font-bold ml-2 text-green-600">
                      +{detail.quality_metrics.growth_rate_percent.toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Mortality Rate:</span>
                    <span className="font-bold ml-2 text-red-600">
                      {detail.quality_metrics.mortality_rate_percent.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => navigate(`/storage-locations/${locationId}/history`)}
                className="btn btn-primary flex-1 flex items-center justify-center gap-2"
              >
                <History className="w-4 h-4" />
                View History
              </button>
              <button
                onClick={() => navigate(`/storage-locations/${locationId}/configure`)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Configure
              </button>
              <button
                onClick={() => navigate(`/storage-locations/${locationId}/analytics`)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <TrendingUp className="w-4 h-4" />
                Analytics
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Related Subflows

- **03_storage_location_preview.md**: Previous level - preview cards
- **05_historical_timeline.md**: Next level - historical evolution tracking

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial storage location detail subflow |
