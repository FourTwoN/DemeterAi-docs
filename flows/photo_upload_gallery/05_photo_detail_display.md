# Diagram 05: Photo Detail Display

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 00_comprehensive_view.mmd
**Related Diagrams:** 03_photo_gallery_view.mmd

## Purpose

This diagram documents the **photo detail view** that displays comprehensive information about a single photo, including detection results, storage location history, and traceability (trazabilidad) information. This is accessed by clicking a photo in the gallery.

## Scope

**Input:**
- `image_id` (UUID): Photo identifier
- User authentication token

**Output:**
- Full-resolution image with annotations
- Detection results and confidence scores
- Storage location information
- Historical timeline of all photos for this location
- Traceability information (who, when, what)
- Download options (original, annotated, JSON)

**Performance Target:**
- Initial load: < 300ms
- Image load: 1-3s (full resolution)
- History query: < 100ms
- Total render: < 500ms

## Detail View Design

### Why Detail View?

**Problem:** Users need to:
- See full-resolution photo with detection annotations
- Verify ML detection accuracy
- View detection confidence scores
- Track storage location history over time
- Access traceability information for compliance
- Download photos and data for analysis

**Solution:** Comprehensive detail page with tabbed interface

### Detail View Features

**Core features:**
1. **Large image viewer**: Zoom, pan, annotations toggle
2. **Detection summary**: Total count, confidence, quality score
3. **Storage location info**: Full path, product, packaging
4. **Historical timeline**: All photos for this location
5. **Traceability**: Upload user, processing details, validations
6. **Download options**: Original, annotated, raw data JSON

## Key Components

### 1. Detail Page Layout (lines 120-260)

**React/TypeScript component:**
```tsx
interface PhotoDetail {
    image_id: string
    original_url: string
    thumbnail_url: string
    annotated_url?: string  // Image with bounding boxes
    status: string
    uploaded_at: string
    metadata: {
        file_size_bytes: number
        width_px: number
        height_px: number
        content_type: string
        exif: any
    }
    processing_session?: {
        session_id: string
        status: string
        storage_location_id?: number
        storage_location_name?: string
        total_detected: number
        total_estimated: number
        avg_confidence: number
        category_counts: Record<string, number>
        validated: boolean
        validated_by?: string
        validation_date?: string
    }
    storage_location_history?: Array<{
        timestamp: string
        event: string
        total_plants: number
        session_id: string
        validated: boolean
    }>
}

function PhotoDetailPage({ imageId }: { imageId: string }) {
    const [photo, setPhoto] = useState<PhotoDetail | null>(null)
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<'details' | 'history' | 'traceability'>('details')

    useEffect(() => {
        loadPhotoDetail()
    }, [imageId])

    async function loadPhotoDetail() {
        setLoading(true)

        try {
            const response = await fetch(
                `/api/v1/photos/${imageId}`,
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
            setPhoto(data)

        } catch (error) {
            showError(`Failed to load photo: ${error.message}`)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return <LoadingSpinner />
    }

    if (!photo) {
        return <NotFoundMessage />
    }

    return (
        <div className="photo-detail-page">
            {/* Header with back button */}
            <div className="detail-header">
                <button onClick={() => navigate('/gallery')} className="btn-back">
                    ← Back to Gallery
                </button>

                <h1>Photo Detail</h1>

                <DownloadMenu photo={photo} />
            </div>

            {/* Main content: Image viewer + Sidebar */}
            <div className="detail-content">
                <div className="detail-main">
                    <ImageViewer photo={photo} />
                </div>

                <div className="detail-sidebar">
                    <DetectionSummary photo={photo} />

                    {/* Tabbed content */}
                    <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

                    {activeTab === 'details' && (
                        <DetailsTab photo={photo} />
                    )}

                    {activeTab === 'history' && (
                        <HistoryTab photo={photo} />
                    )}

                    {activeTab === 'traceability' && (
                        <TraceabilityTab photo={photo} />
                    )}
                </div>
            </div>
        </div>
    )
}
```

### 2. Image Viewer Component (lines 300-440)

**Large image with zoom and annotations:**
```tsx
function ImageViewer({ photo }: { photo: PhotoDetail }) {
    const [showAnnotations, setShowAnnotations] = useState(true)
    const [zoom, setZoom] = useState(1)
    const [pan, setPan] = useState({ x: 0, y: 0 })
    const imageRef = useRef<HTMLImageElement>(null)

    // Image URL: Show annotated if available, else original
    const imageUrl = showAnnotations && photo.annotated_url
        ? photo.annotated_url
        : photo.original_url

    return (
        <div className="image-viewer">
            {/* Toolbar */}
            <div className="image-toolbar">
                <button
                    onClick={() => setShowAnnotations(!showAnnotations)}
                    className={showAnnotations ? 'active' : ''}
                    disabled={!photo.annotated_url}
                >
                    {showAnnotations ? 'Hide' : 'Show'} Annotations
                </button>

                <div className="zoom-controls">
                    <button onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}>
                        −
                    </button>
                    <span>{Math.round(zoom * 100)}%</span>
                    <button onClick={() => setZoom(Math.min(3, zoom + 0.25))}>
                        +
                    </button>
                    <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }) }}>
                        Reset
                    </button>
                </div>

                <button onClick={() => downloadImage(imageUrl)} className="btn-download">
                    Download Image
                </button>
            </div>

            {/* Image container with zoom and pan */}
            <div
                className="image-container"
                style={{
                    overflow: zoom > 1 ? 'scroll' : 'hidden',
                    cursor: zoom > 1 ? 'grab' : 'default'
                }}
            >
                <img
                    ref={imageRef}
                    src={imageUrl}
                    alt="Photo detail"
                    style={{
                        transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)`,
                        transformOrigin: 'center center',
                        transition: 'transform 0.2s'
                    }}
                    draggable={false}
                />
            </div>

            {/* Image metadata */}
            <div className="image-metadata-bar">
                <span>{photo.metadata.width_px} × {photo.metadata.height_px}px</span>
                <span>{formatFileSize(photo.metadata.file_size_bytes)}</span>
                <span>{formatDateTime(photo.uploaded_at)}</span>
            </div>
        </div>
    )
}
```

### 3. Detection Summary Card (lines 480-600)

**Overview of detection results:**
```tsx
function DetectionSummary({ photo }: { photo: PhotoDetail }) {
    const session = photo.processing_session

    if (!session) {
        return (
            <div className="detection-summary empty">
                <p>No processing results available</p>
                {photo.status === 'failed' && (
                    <ErrorBadge errorDetails={photo.error_details} />
                )}
            </div>
        )
    }

    return (
        <div className="detection-summary">
            <h2>Detection Results</h2>

            {/* Main metrics */}
            <div className="metrics-grid">
                <MetricCard
                    label="Total Detected"
                    value={session.total_detected}
                    icon="🌱"
                    color="green"
                />

                <MetricCard
                    label="Estimated"
                    value={session.total_estimated}
                    icon="📊"
                    color="blue"
                />

                <MetricCard
                    label="Avg Confidence"
                    value={`${(session.avg_confidence * 100).toFixed(1)}%`}
                    icon="✓"
                    color={session.avg_confidence > 0.85 ? 'green' : 'orange'}
                />
            </div>

            {/* Category breakdown */}
            {session.category_counts && (
                <div className="category-breakdown">
                    <h3>Categories</h3>
                    {Object.entries(session.category_counts).map(([category, count]) => (
                        <div key={category} className="category-row">
                            <span className="category-name">
                                {formatCategoryName(category)}
                            </span>
                            <span className="category-count">{count}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Storage location */}
            {session.storage_location_name && (
                <div className="storage-location-info">
                    <h3>Storage Location</h3>
                    <div className="location-path">
                        {session.storage_location_name}
                    </div>
                    <button
                        onClick={() => navigate(`/storage-locations/${session.storage_location_id}`)}
                        className="btn-link"
                    >
                        View Location Details →
                    </button>
                </div>
            )}

            {/* Validation status */}
            <div className="validation-status">
                {session.validated ? (
                    <div className="validated">
                        <span className="icon">✓</span>
                        Validated by {session.validated_by}
                        <br />
                        <small>{formatDateTime(session.validation_date)}</small>
                    </div>
                ) : (
                    <button onClick={() => openValidationModal()} className="btn-validate">
                        Validate Results
                    </button>
                )}
            </div>
        </div>
    )
}
```

### 4. History Tab (lines 640-760)

**Timeline of all photos for this storage location:**
```tsx
function HistoryTab({ photo }: { photo: PhotoDetail }) {
    const history = photo.storage_location_history || []

    if (!photo.processing_session?.storage_location_id) {
        return (
            <div className="history-tab empty">
                <p>No storage location assigned. History not available.</p>
            </div>
        )
    }

    if (history.length === 0) {
        return (
            <div className="history-tab empty">
                <p>This is the first photo for this storage location.</p>
            </div>
        )
    }

    return (
        <div className="history-tab">
            <h3>Location History</h3>

            <p className="help-text">
                All photos taken of{' '}
                <strong>{photo.processing_session.storage_location_name}</strong>{' '}
                over time.
            </p>

            <div className="timeline">
                {history.map((event, index) => (
                    <div key={event.session_id} className="timeline-event">
                        <div className="timeline-marker">
                            {index === 0 && <span className="current">Current</span>}
                        </div>

                        <div className="timeline-content">
                            <div className="event-header">
                                <strong>{formatDate(event.timestamp)}</strong>
                                {event.validated && (
                                    <span className="badge badge-green">Validated</span>
                                )}
                            </div>

                            <div className="event-details">
                                <div className="event-metric">
                                    Total plants: <strong>{event.total_plants}</strong>
                                </div>

                                <button
                                    onClick={() => navigate(`/sessions/${event.session_id}`)}
                                    className="btn-link-small"
                                >
                                    View Session →
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Trend chart (optional) */}
            {history.length >= 3 && (
                <div className="trend-chart">
                    <h4>Plant Count Trend</h4>
                    <LineChart
                        data={history.map(h => ({
                            date: h.timestamp,
                            count: h.total_plants
                        }))}
                    />
                </div>
            )}
        </div>
    )
}
```

### 5. Traceability Tab (lines 800-920)

**Comprehensive audit trail:**
```tsx
function TraceabilityTab({ photo }: { photo: PhotoDetail }) {
    return (
        <div className="traceability-tab">
            <h3>Traceability Information</h3>

            <div className="traceability-section">
                <h4>Upload Information</h4>
                <dl>
                    <dt>Uploaded by</dt>
                    <dd>{photo.uploaded_by_name || 'Unknown'}</dd>

                    <dt>Upload date</dt>
                    <dd>{formatDateTime(photo.uploaded_at)}</dd>

                    <dt>Upload source</dt>
                    <dd>{photo.upload_source || 'web'}</dd>

                    <dt>Image ID</dt>
                    <dd className="mono">{photo.image_id}</dd>
                </dl>
            </div>

            {photo.metadata.exif && (
                <div className="traceability-section">
                    <h4>Camera Information</h4>
                    <dl>
                        {photo.metadata.exif.camera_make && (
                            <>
                                <dt>Camera</dt>
                                <dd>
                                    {photo.metadata.exif.camera_make}{' '}
                                    {photo.metadata.exif.camera_model}
                                </dd>
                            </>
                        )}

                        {photo.metadata.exif.datetime_original && (
                            <>
                                <dt>Photo taken</dt>
                                <dd>{formatDateTime(photo.metadata.exif.datetime_original)}</dd>
                            </>
                        )}

                        {photo.metadata.exif.gps_latitude && (
                            <>
                                <dt>GPS Coordinates</dt>
                                <dd>
                                    {photo.metadata.exif.gps_latitude.toFixed(6)},{' '}
                                    {photo.metadata.exif.gps_longitude.toFixed(6)}
                                    <button
                                        onClick={() => openMap(
                                            photo.metadata.exif.gps_latitude,
                                            photo.metadata.exif.gps_longitude
                                        )}
                                        className="btn-link-small"
                                    >
                                        View on Map
                                    </button>
                                </dd>
                            </>
                        )}
                    </dl>
                </div>
            )}

            {photo.processing_session && (
                <div className="traceability-section">
                    <h4>Processing Information</h4>
                    <dl>
                        <dt>Session ID</dt>
                        <dd className="mono">{photo.processing_session.session_id}</dd>

                        <dt>Processing status</dt>
                        <dd>
                            <StatusBadge status={photo.processing_session.status} />
                        </dd>

                        <dt>Processed at</dt>
                        <dd>{formatDateTime(photo.processing_session.created_at)}</dd>

                        {photo.processing_session.validated && (
                            <>
                                <dt>Validated by</dt>
                                <dd>
                                    {photo.processing_session.validated_by}
                                    <br />
                                    <small>
                                        {formatDateTime(photo.processing_session.validation_date)}
                                    </small>
                                </dd>
                            </>
                        )}
                    </dl>
                </div>
            )}

            <div className="traceability-section">
                <h4>Storage Information</h4>
                <dl>
                    <dt>S3 Bucket</dt>
                    <dd className="mono">{photo.s3_bucket}</dd>

                    <dt>S3 Key (original)</dt>
                    <dd className="mono">{photo.s3_key_original}</dd>

                    {photo.s3_key_thumbnail && (
                        <>
                            <dt>S3 Key (thumbnail)</dt>
                            <dd className="mono">{photo.s3_key_thumbnail}</dd>
                        </>
                    )}

                    <dt>File size</dt>
                    <dd>{formatFileSize(photo.metadata.file_size_bytes)}</dd>
                </dl>
            </div>
        </div>
    )
}
```

### 6. Download Menu (lines 960-1040)

**Export options:**
```tsx
function DownloadMenu({ photo }: { photo: PhotoDetail }) {
    const [menuOpen, setMenuOpen] = useState(false)

    return (
        <div className="download-menu">
            <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="btn-download-menu"
            >
                Download ▼
            </button>

            {menuOpen && (
                <div className="download-dropdown">
                    <button onClick={() => downloadImage(photo.original_url)}>
                        Original Image
                    </button>

                    {photo.annotated_url && (
                        <button onClick={() => downloadImage(photo.annotated_url)}>
                            Annotated Image
                        </button>
                    )}

                    <button onClick={() => downloadJSON(photo)}>
                        Raw Data (JSON)
                    </button>

                    {photo.processing_session && (
                        <button onClick={() => downloadCSV(photo)}>
                            Detection Data (CSV)
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}

async function downloadImage(url: string) {
    const response = await fetch(url)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = objectUrl
    a.download = url.split('/').pop() || 'image.jpg'
    a.click()

    URL.revokeObjectURL(objectUrl)
}

function downloadJSON(photo: PhotoDetail) {
    const data = JSON.stringify(photo, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = `photo-${photo.image_id}.json`
    a.click()

    URL.revokeObjectURL(url)
}
```

### 7. Backend: Photo Detail Endpoint (lines 1080-1240)

**FastAPI implementation:**
```python
@router.get('/photos/{image_id}')
async def get_photo_detail(
    image_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive photo details

    Returns:
        Complete photo information including:
        - Image metadata and URLs
        - Processing session results
        - Storage location history
        - Traceability information
    """

    # Query photo with all relationships
    query = select(
        S3Image,
        PhotoProcessingSession,
        StorageLocation,
        User.email.label('uploaded_by_email')
    ).select_from(S3Image).outerjoin(
        PhotoProcessingSession,
        PhotoProcessingSession.original_image_id == S3Image.id
    ).outerjoin(
        StorageLocation,
        StorageLocation.id == PhotoProcessingSession.storage_location_id
    ).outerjoin(
        User,
        User.id == S3Image.uploaded_by_user_id
    ).where(
        S3Image.image_id == image_id,
        S3Image.uploaded_by_user_id == current_user.id
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(404, 'Photo not found')

    image, session, location, uploaded_by_email = row

    # Generate presigned URLs
    s3_client = get_s3_client()

    original_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'demeter-photos', 'Key': image.s3_key_original},
        ExpiresIn=3600
    )

    thumbnail_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'demeter-photos', 'Key': image.s3_key_thumbnail or image.s3_key_original},
        ExpiresIn=3600
    )

    annotated_url = None
    if session and session.processed_image_id:
        processed_image = await db.get(S3Image, session.processed_image_id)
        if processed_image and processed_image.s3_key_original:
            annotated_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': 'demeter-photos', 'Key': processed_image.s3_key_original},
                ExpiresIn=3600
            )

    # Build response
    response = {
        'image_id': str(image.image_id),
        'original_url': original_url,
        'thumbnail_url': thumbnail_url,
        'annotated_url': annotated_url,
        'status': image.status,
        'uploaded_at': image.created_at.isoformat(),
        'uploaded_by_name': uploaded_by_email,
        'upload_source': image.upload_source,
        's3_bucket': image.s3_bucket,
        's3_key_original': image.s3_key_original,
        's3_key_thumbnail': image.s3_key_thumbnail,
        'metadata': {
            'file_size_bytes': image.file_size_bytes,
            'width_px': image.width_px,
            'height_px': image.height_px,
            'content_type': image.content_type,
            'exif': image.exif_metadata
        }
    }

    # Add processing session if exists
    if session:
        response['processing_session'] = {
            'session_id': str(session.session_id),
            'status': session.status,
            'storage_location_id': session.storage_location_id,
            'storage_location_name': location.full_path if location else None,
            'total_detected': session.total_detected,
            'total_estimated': session.total_estimated,
            'avg_confidence': float(session.avg_confidence) if session.avg_confidence else None,
            'category_counts': session.category_counts,
            'validated': session.validated,
            'validated_by': session.validated_by_user_id,
            'validation_date': session.validation_date.isoformat() if session.validation_date else None,
            'created_at': session.created_at.isoformat()
        }

        # Get storage location history
        if session.storage_location_id:
            history_query = select(
                PhotoProcessingSession.created_at,
                PhotoProcessingSession.session_id,
                PhotoProcessingSession.total_estimated,
                PhotoProcessingSession.validated
            ).where(
                PhotoProcessingSession.storage_location_id == session.storage_location_id,
                PhotoProcessingSession.status == 'completed'
            ).order_by(
                PhotoProcessingSession.created_at.desc()
            ).limit(20)

            history_result = await db.execute(history_query)
            history = history_result.all()

            response['storage_location_history'] = [
                {
                    'timestamp': h.created_at.isoformat(),
                    'session_id': str(h.session_id),
                    'total_plants': h.total_estimated,
                    'validated': h.validated
                }
                for h in history
            ]

    return response
```

**Performance:** < 300ms (with proper indexes and presigned URL generation)

## Performance Breakdown

**Detail view load timing:**

| Phase | Time | Details |
|-------|------|---------|
| **Database query** | 80ms | With JOINs and indexes |
| **S3 presigned URLs** | 6ms | 3 URLs × 2ms each |
| **History query** | 50ms | Last 20 sessions |
| **JSON serialization** | 20ms | Build response |
| **Network transfer** | 50ms | ~10KB payload |
| **Frontend parse** | 10ms | Parse JSON |
| **Initial render** | 100ms | React render |
| **Image load** | 1-3s | Full-resolution (network) |
| **Total (excluding image)** | ~300ms | User sees content |

## Related Diagrams

- **03_photo_gallery_view.mmd:** Gallery view that links to detail
- **04_error_recovery_reprocessing.mmd:** Error handling from detail view

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial photo detail display subflow |

---

**Notes:**
- Detail view shows comprehensive information for single photo
- Historical timeline shows all photos for storage location
- Traceability provides complete audit trail
- Download options for original, annotated, and raw data
- Image viewer supports zoom and pan for inspection
