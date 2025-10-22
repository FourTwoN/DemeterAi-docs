# Diagram 03: Photo Gallery View

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 00_comprehensive_view.mmd
**Related Diagrams:** 02_job_monitoring_progress.mmd, 05_photo_detail_display.mmd

## Purpose

This diagram documents the **photo gallery view** that allows users to browse all uploaded photos
across all sessions, filter by various criteria, and navigate to detailed views. This is the primary
interface for viewing photo processing results.

## Scope

**Input:**

- User authentication token
- Optional filters (date range, warehouse, status)
- Pagination parameters (page, per_page)

**Output:**

- Thumbnail grid of all photos
- Filter controls
- Pagination controls
- Photo metadata and status badges
- Navigation to detail views

**Performance Target:**

- Initial load: < 300ms
- Thumbnail loading: < 50ms per image (S3 presigned URLs)
- Filter application: < 200ms
- Infinite scroll: < 100ms per page

## Gallery Design

### Why Gallery View?

**Problem:** Users need to:

- See all processed photos at a glance
- Identify failed/warning photos quickly
- Navigate to detailed views
- Monitor processing history over time

**Solution:** Responsive thumbnail grid with filters and status indicators

### Gallery Features

**Core features:**

1. **Thumbnail grid**: Fast loading with S3 presigned URLs
2. **Advanced filters**: Date, warehouse, status
3. **Status badges**: Visual indicators for success/warning/error
4. **Pagination/Infinite scroll**: Handle large datasets
5. **Batch operations**: Select multiple photos, delete
6. **Quick actions**: Click to open detail view

## Key Components

### 1. Gallery Page Layout (lines 120-220)

**React/TypeScript component structure:**

```tsx
interface Photo {
    image_id: string
    thumbnail_url: string
    original_url: string
    status: 'uploaded' | 'processing' | 'ready' | 'failed'
    uploaded_at: string
    processing_session?: {
        session_id: string
        total_detected: number
        storage_location_id?: number
        storage_location_name?: string
    }
    warehouse_name?: string
    error_details?: string
}

interface GalleryFilters {
    date_from?: string
    date_to?: string
    warehouse_ids?: number[]
    status?: 'all' | 'success' | 'errors'
    search?: string
}

function PhotoGalleryPage() {
    const [photos, setPhotos] = useState<Photo[]>([])
    const [filters, setFilters] = useState<GalleryFilters>({
        status: 'all'
    })
    const [pagination, setPagination] = useState({
        page: 1,
        per_page: 50,
        total_pages: 0,
        total_items: 0
    })
    const [loading, setLoading] = useState(true)
    const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set())

    // Load photos on mount and when filters change
    useEffect(() => {
        loadPhotos()
    }, [filters, pagination.page])

    async function loadPhotos() {
        setLoading(true)

        try {
            const queryParams = new URLSearchParams({
                page: pagination.page.toString(),
                per_page: pagination.per_page.toString(),
                status: filters.status || 'all',
                ...(filters.date_from && { date_from: filters.date_from }),
                ...(filters.date_to && { date_to: filters.date_to }),
                ...(filters.warehouse_ids?.length && {
                    warehouse_ids: filters.warehouse_ids.join(',')
                }),
                ...(filters.search && { search: filters.search })
            })

            const response = await fetch(
                `/api/v1/photos/gallery?${queryParams}`,
                {
                    headers: {
                        'Authorization': `Bearer ${getToken()}`
                    }
                }
            )

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }

            const data = await response.json()
            setPhotos(data.photos)
            setPagination(prev => ({
                ...prev,
                total_pages: data.pagination.total_pages,
                total_items: data.pagination.total_items
            }))

        } catch (error) {
            showError(`Failed to load gallery: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="gallery-page">
            <GalleryHeader
                filters={filters}
                onFiltersChange={setFilters}
                selectedCount={selectedPhotos.size}
                onDeleteSelected={() => deletePhotos(Array.from(selectedPhotos))}
            />

            {loading ? (
                <LoadingSpinner />
            ) : (
                <>
                    <PhotoGrid
                        photos={photos}
                        selectedPhotos={selectedPhotos}
                        onPhotoSelect={togglePhotoSelection}
                        onPhotoClick={openPhotoDetail}
                    />

                    <PaginationControls
                        pagination={pagination}
                        onPageChange={page => setPagination(prev => ({ ...prev, page }))}
                    />
                </>
            )}
        </div>
    )
}
```

### 2. Filter Controls (lines 260-380)

**Filter UI component:**

```tsx
interface FilterControlsProps {
    filters: GalleryFilters
    onFiltersChange: (filters: GalleryFilters) => void
}

function FilterControls({ filters, onFiltersChange }: FilterControlsProps) {
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])

    useEffect(() => {
        loadWarehouses()
    }, [])

    return (
        <div className="filter-controls">
            {/* Date range picker */}
            <div className="filter-group">
                <label>Date Range</label>
                <DateRangePicker
                    value={{
                        from: filters.date_from,
                        to: filters.date_to
                    }}
                    onChange={(range) => {
                        onFiltersChange({
                            ...filters,
                            date_from: range.from,
                            date_to: range.to
                        })
                    }}
                    presets={[
                        { label: 'Today', value: 'today' },
                        { label: 'Last 7 days', value: 'last_7_days' },
                        { label: 'Last 30 days', value: 'last_30_days' },
                        { label: 'This month', value: 'this_month' },
                        { label: 'Custom', value: 'custom' }
                    ]}
                />
            </div>

            {/* Warehouse selector */}
            <div className="filter-group">
                <label>Warehouse</label>
                <MultiSelect
                    options={warehouses.map(w => ({
                        value: w.id,
                        label: w.name
                    }))}
                    value={filters.warehouse_ids || []}
                    onChange={(ids) => {
                        onFiltersChange({
                            ...filters,
                            warehouse_ids: ids
                        })
                    }}
                    placeholder="All warehouses"
                />
            </div>

            {/* Status filter */}
            <div className="filter-group">
                <label>Status</label>
                <Select
                    options={[
                        { value: 'all', label: 'All Photos' },
                        { value: 'success', label: 'Success Only' },
                        { value: 'errors', label: 'Errors Only' }
                    ]}
                    value={filters.status || 'all'}
                    onChange={(status) => {
                        onFiltersChange({
                            ...filters,
                            status
                        })
                    }}
                />
            </div>

            {/* Search */}
            <div className="filter-group">
                <label>Search</label>
                <input
                    type="text"
                    placeholder="Search by filename..."
                    value={filters.search || ''}
                    onChange={(e) => {
                        onFiltersChange({
                            ...filters,
                            search: e.target.value
                        })
                    }}
                />
            </div>

            {/* Clear filters button */}
            {hasActiveFilters(filters) && (
                <button
                    onClick={() => onFiltersChange({ status: 'all' })}
                    className="btn-clear-filters"
                >
                    Clear Filters
                </button>
            )}
        </div>
    )
}
```

### 3. Photo Grid Component (lines 420-540)

**Thumbnail grid with lazy loading:**

```tsx
interface PhotoGridProps {
    photos: Photo[]
    selectedPhotos: Set<string>
    onPhotoSelect: (imageId: string) => void
    onPhotoClick: (photo: Photo) => void
}

function PhotoGrid({
    photos,
    selectedPhotos,
    onPhotoSelect,
    onPhotoClick
}: PhotoGridProps) {
    return (
        <div className="photo-grid">
            {photos.map(photo => (
                <PhotoCard
                    key={photo.image_id}
                    photo={photo}
                    selected={selectedPhotos.has(photo.image_id)}
                    onSelect={() => onPhotoSelect(photo.image_id)}
                    onClick={() => onPhotoClick(photo)}
                />
            ))}
        </div>
    )
}

function PhotoCard({
    photo,
    selected,
    onSelect,
    onClick
}: {
    photo: Photo
    selected: boolean
    onSelect: () => void
    onClick: () => void
}) {
    const [imageLoaded, setImageLoaded] = useState(false)

    return (
        <div
            className={`photo-card ${selected ? 'selected' : ''}`}
            onClick={onClick}
        >
            {/* Checkbox for selection */}
            <div className="photo-checkbox" onClick={(e) => {
                e.stopPropagation()  // Prevent card click
                onSelect()
            }}>
                <input
                    type="checkbox"
                    checked={selected}
                    onChange={onSelect}
                />
            </div>

            {/* Thumbnail with lazy loading */}
            <div className="photo-thumbnail">
                {!imageLoaded && (
                    <div className="thumbnail-skeleton">
                        <LoadingSpinner size="small" />
                    </div>
                )}
                <img
                    src={photo.thumbnail_url}
                    alt={`Photo ${photo.image_id}`}
                    loading="lazy"  // Native lazy loading
                    onLoad={() => setImageLoaded(true)}
                    style={{ display: imageLoaded ? 'block' : 'none' }}
                />
            </div>

            {/* Status badge */}
            <StatusBadge
                status={photo.status}
                errorDetails={photo.error_details}
            />

            {/* Metadata overlay */}
            <div className="photo-metadata">
                <div className="photo-date">
                    {formatDate(photo.uploaded_at)}
                </div>
                {photo.processing_session && (
                    <div className="photo-detections">
                        {photo.processing_session.total_detected} plants detected
                    </div>
                )}
                {photo.warehouse_name && (
                    <div className="photo-warehouse">
                        {photo.warehouse_name}
                    </div>
                )}
            </div>
        </div>
    )
}
```

**CSS for responsive grid:**

```css
.photo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    padding: 20px;
}

.photo-card {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.photo-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.photo-card.selected {
    border: 3px solid #2196f3;
}

.photo-thumbnail {
    width: 100%;
    height: 250px;
    background-color: #f5f5f5;
}

.photo-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

@media (max-width: 768px) {
    .photo-grid {
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 10px;
    }

    .photo-thumbnail {
        height: 150px;
    }
}
```

### 4. Status Badge Component (lines 580-660)

**Visual status indicators:**

```tsx
function StatusBadge({
    status,
    errorDetails
}: {
    status: string
    errorDetails?: string
}) {
    const config = {
        'ready': {
            color: '#4caf50',
            icon: '✓',
            label: 'Success',
            tooltip: 'Photo processed successfully'
        },
        'processing': {
            color: '#2196f3',
            icon: '⟳',
            label: 'Processing',
            tooltip: 'ML processing in progress'
        },
        'failed': {
            color: '#f44336',
            icon: '✗',
            label: 'Error',
            tooltip: errorDetails || 'Processing failed'
        },
        'uploaded': {
            color: '#ff9800',
            icon: '⋯',
            label: 'Pending',
            tooltip: 'Waiting for processing'
        }
    }

    const statusConfig = config[status] || config['uploaded']

    return (
        <div
            className="status-badge"
            style={{
                backgroundColor: statusConfig.color,
                opacity: 0.9
            }}
            title={statusConfig.tooltip}
        >
            <span className="status-icon">{statusConfig.icon}</span>
            <span className="status-label">{statusConfig.label}</span>
        </div>
    )
}
```

**Special handling for warning states:**

```tsx
function WarningBadge({ errorDetails }: { errorDetails: string }) {
    // Parse error type
    let warningType = 'error'
    let warningMessage = errorDetails

    if (errorDetails.includes('needs_location')) {
        warningType = 'needs_location'
        warningMessage = 'Missing GPS location'
    } else if (errorDetails.includes('needs_config')) {
        warningType = 'needs_config'
        warningMessage = 'Storage location not configured'
    } else if (errorDetails.includes('needs_calibration')) {
        warningType = 'needs_calibration'
        warningMessage = 'Calibration required'
    }

    return (
        <div className="warning-badge" data-type={warningType}>
            <span className="warning-icon">⚠</span>
            <span className="warning-message">{warningMessage}</span>
            <button
                className="btn-fix"
                onClick={(e) => {
                    e.stopPropagation()
                    openErrorModal(errorDetails)
                }}
            >
                Fix
            </button>
        </div>
    )
}
```

### 5. Backend: Gallery Endpoint (lines 700-860)

**FastAPI implementation:**

```python
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta
import boto3
from botocore.client import Config

router = APIRouter()

@router.get('/photos/gallery')
async def get_photo_gallery(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str = Query('all', regex='^(all|success|errors)$'),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    warehouse_ids: Optional[str] = Query(None),  # Comma-separated IDs
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get photo gallery with filters and pagination

    Returns:
        {
            "photos": [...],
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total_pages": 5,
                "total_items": 237
            }
        }

    Performance: < 200ms (with proper indexes)
    """

    # Build query
    query = select(
        S3Image.image_id,
        S3Image.s3_key_original,
        S3Image.s3_key_thumbnail,
        S3Image.status,
        S3Image.error_details,
        S3Image.created_at,
        PhotoProcessingSession.session_id,
        PhotoProcessingSession.total_detected,
        PhotoProcessingSession.storage_location_id,
        StorageLocation.full_path.label('storage_location_name'),
        Warehouse.name.label('warehouse_name')
    ).select_from(S3Image).outerjoin(
        PhotoProcessingSession,
        PhotoProcessingSession.original_image_id == S3Image.id
    ).outerjoin(
        StorageLocation,
        StorageLocation.id == PhotoProcessingSession.storage_location_id
    ).outerjoin(
        Warehouse,
        Warehouse.id == StorageLocation.warehouse_id
    ).where(
        S3Image.uploaded_by_user_id == current_user.id,
        S3Image.deleted_at.is_(None)  # Exclude soft-deleted
    )

    # Apply filters
    if status == 'success':
        query = query.where(S3Image.status == 'ready')
    elif status == 'errors':
        query = query.where(S3Image.status == 'failed')

    if date_from:
        date_from_dt = datetime.fromisoformat(date_from)
        query = query.where(S3Image.created_at >= date_from_dt)

    if date_to:
        date_to_dt = datetime.fromisoformat(date_to)
        query = query.where(S3Image.created_at <= date_to_dt)

    if warehouse_ids:
        ids = [int(id_str) for id_str in warehouse_ids.split(',')]
        query = query.where(Warehouse.id.in_(ids))

    if search:
        # Search in S3 key (contains original filename)
        query = query.where(
            S3Image.s3_key_original.ilike(f'%{search}%')
        )

    # Order by most recent first
    query = query.order_by(S3Image.created_at.desc())

    # Get total count (for pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_items = await db.scalar(count_query)

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Generate presigned URLs for thumbnails
    s3_client = boto3.client(
        's3',
        config=Config(signature_version='s3v4')
    )

    photos = []
    for row in rows:
        # Generate presigned URL (valid for 1 hour)
        thumbnail_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': 'demeter-photos',
                'Key': row.s3_key_thumbnail or row.s3_key_original
            },
            ExpiresIn=3600  # 1 hour
        )

        original_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': 'demeter-photos',
                'Key': row.s3_key_original
            },
            ExpiresIn=3600
        )

        photo = {
            'image_id': str(row.image_id),
            'thumbnail_url': thumbnail_url,
            'original_url': original_url,
            'status': row.status,
            'uploaded_at': row.created_at.isoformat(),
            'warehouse_name': row.warehouse_name
        }

        # Add processing session info if available
        if row.session_id:
            photo['processing_session'] = {
                'session_id': str(row.session_id),
                'total_detected': row.total_detected,
                'storage_location_id': row.storage_location_id,
                'storage_location_name': row.storage_location_name
            }

        # Add error details if failed
        if row.status == 'failed' and row.error_details:
            photo['error_details'] = row.error_details

        photos.append(photo)

    # Calculate pagination
    total_pages = (total_items + per_page - 1) // per_page

    return {
        'photos': photos,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_items
        }
    }
```

**Performance optimizations:**

```sql
-- Required indexes for fast query
CREATE INDEX idx_s3_images_user_created ON s3_images(uploaded_by_user_id, created_at DESC);
CREATE INDEX idx_s3_images_status ON s3_images(status);
CREATE INDEX idx_s3_images_deleted ON s3_images(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_processing_session_image ON photo_processing_sessions(original_image_id);
CREATE INDEX idx_storage_location_warehouse ON storage_locations(warehouse_id);
```

### 6. Pagination Controls (lines 900-980)

**Pagination UI:**

```tsx
function PaginationControls({
    pagination,
    onPageChange
}: {
    pagination: Pagination
    onPageChange: (page: number) => void
}) {
    const { page, total_pages, total_items } = pagination

    // Calculate page range to show (e.g., 1 2 3 ... 8 9 10)
    const pageRange = calculatePageRange(page, total_pages)

    return (
        <div className="pagination-controls">
            <div className="pagination-info">
                Showing {(page - 1) * pagination.per_page + 1} to{' '}
                {Math.min(page * pagination.per_page, total_items)} of{' '}
                {total_items} photos
            </div>

            <div className="pagination-buttons">
                <button
                    onClick={() => onPageChange(page - 1)}
                    disabled={page === 1}
                    className="btn-page"
                >
                    ← Previous
                </button>

                {pageRange.map((p, index) => (
                    typeof p === 'number' ? (
                        <button
                            key={index}
                            onClick={() => onPageChange(p)}
                            className={`btn-page ${p === page ? 'active' : ''}`}
                        >
                            {p}
                        </button>
                    ) : (
                        <span key={index} className="pagination-ellipsis">
                            ...
                        </span>
                    )
                ))}

                <button
                    onClick={() => onPageChange(page + 1)}
                    disabled={page === total_pages}
                    className="btn-page"
                >
                    Next →
                </button>
            </div>
        </div>
    )
}

function calculatePageRange(
    currentPage: number,
    totalPages: number
): (number | string)[] {
    /*
    Generate smart page range: [1, 2, 3, '...', 8, 9, 10]
    Always show first, last, and pages around current
    */

    if (totalPages <= 7) {
        // Show all pages
        return Array.from({ length: totalPages }, (_, i) => i + 1)
    }

    const range: (number | string)[] = []

    // Always show first page
    range.push(1)

    if (currentPage > 3) {
        range.push('...')
    }

    // Show pages around current
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
        range.push(i)
    }

    if (currentPage < totalPages - 2) {
        range.push('...')
    }

    // Always show last page
    if (totalPages > 1) {
        range.push(totalPages)
    }

    return range
}
```

### 7. Batch Operations (lines 1020-1100)

**Delete multiple photos:**

```tsx
async function deletePhotos(imageIds: string[]) {
    // Show confirmation dialog
    const confirmed = await showConfirmDialog({
        title: 'Delete Photos',
        message: `Are you sure you want to delete ${imageIds.length} photo(s)? This action cannot be undone.`,
        confirmLabel: 'Delete',
        confirmColor: 'red'
    })

    if (!confirmed) {
        return
    }

    try {
        const response = await fetch('/api/v1/photos/batch-delete', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image_ids: imageIds })
        })

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json()

        showSuccess(`Successfully deleted ${result.deleted_count} photo(s)`)

        // Clear selection and reload gallery
        setSelectedPhotos(new Set())
        loadPhotos()

    } catch (error) {
        showError(`Failed to delete photos: ${error.message}`)
    }
}
```

**Backend batch delete endpoint:**

```python
@router.post('/photos/batch-delete')
async def batch_delete_photos(
    request: BatchDeleteRequest,  # { image_ids: List[str] }
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete multiple photos

    Note: Soft delete (set deleted_at), don't actually delete S3 files
    """

    # Verify user owns all photos
    query = select(S3Image).where(
        S3Image.image_id.in_(request.image_ids),
        S3Image.uploaded_by_user_id == current_user.id,
        S3Image.deleted_at.is_(None)
    )

    result = await db.execute(query)
    images = result.scalars().all()

    if len(images) != len(request.image_ids):
        raise HTTPException(400, 'Some photos not found or not owned by user')

    # Soft delete
    for image in images:
        image.deleted_at = datetime.utcnow()

    await db.commit()

    return {
        'deleted_count': len(images),
        'deleted_image_ids': [str(img.image_id) for img in images]
    }
```

## Performance Breakdown

**Gallery load timing (for 50 photos per page):**

| Phase                            | Time             | Details                    |
|----------------------------------|------------------|----------------------------|
| **Database query**               | 50-100ms         | With proper indexes        |
| **S3 presigned URLs**            | 50 × 2ms = 100ms | 50 URLs × 2 operations     |
| **JSON serialization**           | 20ms             | Serialize response         |
| **Network transfer**             | 50-100ms         | ~150KB payload             |
| **Frontend parsing**             | 10ms             | Parse JSON                 |
| **Initial render**               | 50ms             | React rendering            |
| **Thumbnail loading**            | 1-2s             | Lazy loading (staggered)   |
| **Total (excluding thumbnails)** | ~300-350ms       | User sees grid immediately |

**Thumbnail optimization:**

- **Size**: 300×300px JPEG (quality 80%) ≈ 30KB each
- **Total**: 50 × 30KB = 1.5MB per page
- **Loading**: Lazy (native `loading="lazy"` attribute)
- **Caching**: Browser cache + CloudFront CDN (1 hour TTL)

## Error Handling

### 1. Empty Gallery

**Scenario:** User has no uploaded photos

**UI:**

```tsx
if (photos.length === 0 && !loading) {
    return (
        <EmptyState
            icon="📷"
            title="No photos yet"
            message="Upload your first batch of photos to get started"
            action={{
                label: 'Upload Photos',
                onClick: () => navigate('/upload')
            }}
        />
    )
}
```

### 2. S3 Presigned URL Generation Failure

**Scenario:** AWS credentials invalid, S3 unavailable

**Fallback:**

```python
try:
    thumbnail_url = s3_client.generate_presigned_url(...)
except Exception as e:
    logger.error(f'Failed to generate presigned URL: {e}')
    # Return placeholder image URL
    thumbnail_url = '/static/placeholder-thumbnail.jpg'
```

### 3. Thumbnail Loading Failure

**Scenario:** S3 image deleted, URL expired

**UI:**

```tsx
<img
    src={photo.thumbnail_url}
    alt={`Photo ${photo.image_id}`}
    loading="lazy"
    onError={(e) => {
        // Replace with placeholder on error
        e.currentTarget.src = '/static/placeholder-thumbnail.jpg'
    }}
/>
```

## Related Diagrams

- **02_job_monitoring_progress.mmd:** Monitoring before navigating to gallery
- **04_error_recovery_reprocessing.mmd:** Fixing errors from gallery view
- **05_photo_detail_display.mmd:** Detail view accessed from gallery

## Version History

| Version | Date       | Changes                      |
|---------|------------|------------------------------|
| 1.0.0   | 2025-10-08 | Initial gallery view subflow |

---

**Notes:**

- Gallery shows ALL photos (not just current session)
- Thumbnail URLs cached for 1 hour (reduce API calls)
- Lazy loading critical for performance (50+ images)
- Soft delete preserves data for recovery
- Infinite scroll can replace pagination in v2.0
