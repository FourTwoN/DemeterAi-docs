# Historical Timeline - Storage Location Evolution Tracking

**Version:** 1.0.0
**Date:** 2025-10-08
**System:** DemeterAI Map Warehouse Views
**Parent Flow:** 00_comprehensive_view

## Purpose

This subflow details the **historical timeline view** showing storage_location evolution over time
with photo periods (every 3 months), tracking quantity changes through plantados, muertes,
transplantes, and ventas.

## Scope

- **Level**: Detailed subflow (Level 4 of 4)
- **Audience**: Developers, operations managers, agronomists
- **Detail**: Historical tracking, period calculations, movement traceability
- **Technology**: React, REST API, materialized views

## What It Represents

The historical timeline provides **full traceability** for a storage_location:

1. **User clicks "View History"** from detail view (Level 3)
2. **Fetch historical data** → `/api/v1/storage-locations/{id}/history` (~500ms)
3. **Display timeline** with photo periods (typically every 3 months)
4. **Per period metrics**:
    - Fecha (date)
    - Cantidad inicial (starting quantity from previous period)
    - Muertes (deaths/losses during period)
    - Transplantes (transplants out to other locations)
    - Plantados (new plantings during period)
    - Cantidad vendida (quantity sold during period)
    - Cantidad final (ending quantity, should match next period start)
5. **Visualizations**: Line chart showing quantity evolution, movement breakdown

## Data Structure

```typescript
interface HistoricalPeriod {
  fecha: string;  // ISO 8601 - period start date
  period_end: string | null;  // ISO 8601 - period end date (null for current)
  session_id: string;  // Photo session UUID
  photo_thumbnail_url: string;  // S3 URL
  cantidad_inicial: number;  // Starting quantity
  muertes: number;  // Deaths during period
  transplantes: number;  // Transplants out
  plantados: number;  // New plantings
  cantidad_vendida: number;  // Sales
  cantidad_final: number;  // Ending quantity
  net_change: number;  // cantidad_final - cantidad_inicial
}

interface HistoricalTimelineResponse {
  storage_location: {
    id: number;
    code: string;
    name: string;
  };
  periods: HistoricalPeriod[];
  summary: {
    total_periods: number;
    earliest_date: string;
    latest_date: string;
    total_muertes: number;
    total_transplantes: number;
    total_plantados: number;
    total_vendidos: number;
    overall_growth_rate_percent: number;
  };
  pagination: {
    page: number;
    per_page: number;
    total_pages: number;
    total_items: number;
  };
}
```

## Materialized View: mv_storage_location_history

Pre-aggregated historical timeline data for fast queries.

```sql
CREATE MATERIALIZED VIEW mv_storage_location_history AS
WITH period_boundaries AS (
    -- Define period boundaries from photo sessions
    SELECT
        storage_location_id,
        created_at AS period_start,
        LEAD(created_at) OVER (
            PARTITION BY storage_location_id
            ORDER BY created_at
        ) AS period_end,
        session_id,
        total_detected AS quantity_final
    FROM photo_processing_sessions
    WHERE status = 'completed' AND storage_location_id IS NOT NULL
),
period_movements AS (
    -- Aggregate movements per period
    SELECT
        pb.storage_location_id,
        pb.period_start,
        pb.period_end,
        pb.session_id,
        pb.quantity_final,
        LAG(pb.quantity_final) OVER (
            PARTITION BY pb.storage_location_id
            ORDER BY pb.period_start
        ) AS quantity_inicial,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'muerte' THEN sm.quantity ELSE 0 END), 0) AS muertes,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'transplante' AND sm.from_location_id = pb.storage_location_id THEN sm.quantity ELSE 0 END), 0) AS transplantes,
        COALESCE(SUM(CASE WHEN sm.movement_type IN ('plantar', 'sembrar') THEN sm.quantity ELSE 0 END), 0) AS plantados,
        COALESCE(SUM(CASE WHEN sm.movement_type = 'ventas' THEN sm.quantity ELSE 0 END), 0) AS vendidos
    FROM period_boundaries pb
    LEFT JOIN stock_movements sm ON (
        sm.from_location_id = pb.storage_location_id OR
        sm.to_location_id = pb.storage_location_id
    )
    AND sm.created_at >= pb.period_start
    AND (pb.period_end IS NULL OR sm.created_at < pb.period_end)
    GROUP BY pb.storage_location_id, pb.period_start, pb.period_end, pb.session_id, pb.quantity_final
)
SELECT
    storage_location_id,
    period_start AS fecha,
    period_end,
    session_id,
    COALESCE(quantity_inicial, 0) AS cantidad_inicial,
    muertes,
    transplantes,
    plantados,
    vendidos,
    quantity_final AS cantidad_final,
    quantity_final - COALESCE(quantity_inicial, 0) AS net_change
FROM period_movements
ORDER BY storage_location_id, period_start;

-- Indexes
CREATE INDEX idx_mv_location_history_location ON mv_storage_location_history(storage_location_id);
CREATE INDEX idx_mv_location_history_fecha ON mv_storage_location_history(fecha DESC);
```

**Refresh strategy:**

```sql
-- Refresh daily at midnight via pg_cron
SELECT cron.schedule(
    'refresh-location-history',
    '0 0 * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_history'
);

-- Manual refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_storage_location_history;
```

## API Endpoint

### GET /api/v1/storage-locations/{id}/history

**Request:**

```http
GET /api/v1/storage-locations/1/history?page=1&per_page=12 HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters:**

- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 12 = 3 years of quarterly data)

**Response:** (See HistoricalTimelineResponse structure above)

**Performance:**

- **Response time target**: < 500ms
- **Cache**: Redis TTL 1 day
- **Invalidation**: After stock movement transaction or daily materialized view refresh
- **Pagination**: 12 periods per page (configurable)

## Component Implementation

```typescript
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, ArrowLeft } from 'lucide-react';

export const HistoricalTimeline: React.FC = () => {
  const { locationId } = useParams<{ locationId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<HistoricalTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`/api/v1/storage-locations/${locationId}/history`, {
          headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const historyData = await response.json();
        setData(historyData);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchHistory();
  }, [locationId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
        <span className="ml-2">Loading history...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="alert alert-error">
          <p>Error: {error || 'Not found'}</p>
          <button onClick={() => navigate(-1)} className="btn btn-sm">Go Back</button>
        </div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = data.periods.map(period => ({
    date: new Date(period.fecha).toLocaleDateString('es-AR', { month: 'short', year: '2-digit' }),
    quantity: period.cantidad_final,
    muertes: period.muertes,
    plantados: period.plantados,
    vendidos: period.cantidad_vendida,
    transplantes: period.transplantes
  }));

  return (
    <div className="historical-timeline bg-gray-50 min-h-screen">
      {/* Header */}
      <header className="bg-white shadow p-4 mb-4">
        <button
          onClick={() => navigate(-1)}
          className="text-blue-600 mb-2 flex items-center gap-1"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Detail
        </button>
        <h1 className="text-2xl font-bold">Historical Timeline</h1>
        <p className="text-gray-600">
          {data.storage_location.name} ({data.storage_location.code})
        </p>
      </header>

      <div className="container mx-auto px-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Total Periods</div>
            <div className="text-2xl font-bold">{data.summary.total_periods}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Total Plantados</div>
            <div className="text-2xl font-bold text-green-600">+{data.summary.total_plantados}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Total Vendidos</div>
            <div className="text-2xl font-bold text-blue-600">-{data.summary.total_vendidos}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-600">Growth Rate</div>
            <div className="text-2xl font-bold text-green-600">
              +{data.summary.overall_growth_rate_percent.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Quantity Evolution Chart */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Quantity Evolution Over Time</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="quantity"
                stroke="#2196F3"
                strokeWidth={2}
                name="Total Quantity"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Movements Breakdown Chart */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Movements Breakdown</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="plantados" fill="#4CAF50" name="Plantados" />
              <Bar dataKey="vendidos" fill="#2196F3" name="Vendidos" />
              <Bar dataKey="muertes" fill="#F44336" name="Muertes" />
              <Bar dataKey="transplantes" fill="#FF9800" name="Transplantes" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Period Details List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Period Details</h2>
          <div className="space-y-4">
            {data.periods.map((period, index) => (
              <div key={period.session_id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex gap-4">
                  {/* Photo Thumbnail */}
                  <img
                    src={period.photo_thumbnail_url}
                    alt={`Period ${index + 1}`}
                    className="w-24 h-24 object-cover rounded"
                    loading="lazy"
                  />

                  {/* Period Details */}
                  <div className="flex-1">
                    <h3 className="font-bold text-lg mb-2">
                      {new Date(period.fecha).toLocaleDateString('es-AR', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                      })}
                    </h3>

                    <div className="grid grid-cols-3 gap-3 text-sm">
                      <div>
                        <span className="text-gray-500">Inicial:</span>
                        <span className="font-semibold ml-1">{period.cantidad_inicial}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Plantados:</span>
                        <span className="font-semibold ml-1 text-green-600">+{period.plantados}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Vendidos:</span>
                        <span className="font-semibold ml-1 text-blue-600">-{period.cantidad_vendida}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Muertes:</span>
                        <span className="font-semibold ml-1 text-red-600">-{period.muertes}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Transplantes:</span>
                        <span className="font-semibold ml-1 text-orange-600">-{period.transplantes}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Final:</span>
                        <span className="font-semibold ml-1">{period.cantidad_final}</span>
                      </div>
                    </div>

                    <div className="mt-2">
                      <span
                        className={`badge ${
                          period.net_change >= 0 ? 'badge-success' : 'badge-error'
                        }`}
                      >
                        Net Change: {period.net_change > 0 ? '+' : ''}{period.net_change}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
```

## Movement Type Definitions

### plantar

New plants added to location (from nursery, external source, etc.)

### sembrar

Seeds sown in location (beginning of cultivation cycle)

### transplante

Plants moved from this location to another storage_location

### muerte

Plants that died or were discarded (health issues, pests, etc.)

### ventas

Plants sold to customers (removed from inventory)

### foto

Photo capture event (triggers quantity detection via ML)

### ajuste

Manual inventory adjustment (corrections, reconciliation)

## Traceability Features

### Movement Audit Trail

Each movement in `stock_movements` table includes:

- `created_by_user_id`: Who made the change
- `created_at`: When the change occurred
- `reference_session_id`: Link to photo session (if applicable)
- `notes`: Optional comments

### Balance Verification

```typescript
// Verify period balance
const expectedFinal = cantidad_inicial + plantados - (muertes + transplantes + vendidos);

if (expectedFinal !== cantidad_final) {
  console.warn('Period balance mismatch:', {
    expected: expectedFinal,
    actual: cantidad_final,
    difference: cantidad_final - expectedFinal
  });
}
```

### Full Chain of Custody

- Link movements to specific users
- Link movements to photo sessions
- Link movements between locations (transplante)
- Track product states (seedling → mature → ready_for_sale)

## Performance Considerations

### Materialized View Benefits

- **Pre-aggregated data**: Complex joins and aggregations done once
- **Fast queries**: < 500ms response time
- **Daily refresh**: Balance between freshness and performance
- **Concurrent refresh**: No blocking during refresh

### Pagination Strategy

- **Default**: 12 periods per page (3 years of quarterly photos)
- **Why 12**: Balance between data completeness and load time
- **Infinite scroll**: Optional for better UX

### Cache Strategy

```python
# Redis cache key
cache_key = f"cache:location:{location_id}:history:page:{page}"

# TTL: 1 day (matches materialized view refresh)
redis_client.setex(cache_key, 86400, json.dumps(response))
```

## Related Subflows

- **04_storage_location_detail.md**: Previous level - detail view with "View History" button
- **00_comprehensive_view.md**: Complete system overview

## Version History

| Version | Date       | Changes                             |
|---------|------------|-------------------------------------|
| 1.0.0   | 2025-10-08 | Initial historical timeline subflow |

---

**Notes:**

- Timeline shows complete traceability for compliance and auditing
- Photo periods typically every 3 months (configurable)
- Movement types align with agronomic operations
- Balance verification ensures data integrity
- Materialized view provides fast query performance
- Charts visualize trends and patterns over time
