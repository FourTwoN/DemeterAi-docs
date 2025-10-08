# Diagram 04: Error Recovery & Reprocessing

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 00_comprehensive_view.mmd
**Related Diagrams:** 03_photo_gallery_view.mmd, 01_photo_upload_initiation.mmd

## Purpose

This diagram documents the **warning state resolution and reprocessing mechanism** that allows users to fix photos in warning states and reprocess them from S3 without re-uploading. This enables graceful degradation and user-driven resolution.

**IMPORTANT:** Warning states (`completed_with_warning`) are NOT failures. Photos are processed successfully but need manual action to complete stock batch creation.

## Scope

**Input:**
- Photo with warning state (`needs_location`, `needs_config`, `needs_calibration`)
- User corrections (manual location, configuration, calibration)
- Image ID and S3 key

**Output:**
- New Celery job created from S3 original
- Updated processing session with fixes applied
- Success or new warning state

**Performance Target:**
- Warning modal load: < 100ms
- Reprocess trigger: < 200ms
- New job creation: < 500ms
- Total reprocessing time: 2-3 minutes (same as initial processing)

## Warning States (Not Errors)

### 1. needs_location

**Problem:** GPS coordinates missing or outside known cultivation areas

**Causes:**
- Photo taken indoors without GPS
- Phone GPS disabled
- EXIF data stripped
- GPS coordinates don't match any registered field/warehouse

**Resolution:**
- User manually selects storage location from dropdown
- System reprocesses with manual location override
- GPS matching skipped, uses user-provided location

### 2. needs_config

**Problem:** Storage location identified but not configured with product/packaging info

**Causes:**
- New storage location created but not configured
- Admin hasn't set up product types for this location
- Missing density calibration parameters

**Resolution:**
- Admin configures storage location (via storage location manager)
- Sets product type, packaging type, expected density
- System reprocesses with new configuration

### 3. needs_calibration

**Problem:** Density estimation requires calibration data for this product type

**Causes:**
- New product type without historical data
- Unusual packaging not seen before
- ML model confidence too low without calibration baseline

**Resolution:**
- Admin runs calibration wizard for product type
- Provides 3-5 reference photos with known counts
- System builds calibration model
- Photo reprocessed with calibration applied

## Key Components

### 1. Warning Badge Click (Gallery View) (lines 120-200)

**User interaction:**
```tsx
function PhotoCard({ photo }: { photo: Photo }) {
    // Check for warning states (completed_with_warning)
    if (photo.status === 'completed_with_warning') {
        return (
            <div className="photo-card warning">
                <img src={photo.thumbnail_url} />

                {/* Warning badge */}
                <div
                    className="warning-badge"
                    onClick={(e) => {
                        e.stopPropagation()  // Don't trigger photo detail view
                        openWarningModal(photo)
                    }}
                >
                    <span className="warning-icon">⚠</span>
                    <span className="warning-label">
                        {parseWarningType(photo.warning_type)}
                    </span>
                    <button className="btn-fix">Fix</button>
                </div>
            </div>
        )
    }

    return <div className="photo-card">...</div>
}

function parseWarningType(warningType: string): string {
    if (warningType === 'needs_location') {
        return 'Missing Location'
    } else if (warningType === 'needs_config') {
        return 'Not Configured'
    } else if (warningType === 'needs_calibration') {
        return 'Needs Calibration'
    } else {
        return 'Action Needed'
    }
}
```

### 2. Warning Modal Component (lines 240-400)

**Modal structure:**
```tsx
interface WarningModalProps {
    photo: Photo
    onClose: () => void
    onReprocess: () => void
}

function WarningModal({ photo, onClose, onReprocess }: WarningModalProps) {
    const warningType = photo.warning_type
    const [fixing, setFixing] = useState(false)
    const [fixData, setFixData] = useState<any>(null)

    return (
        <Modal isOpen onClose={onClose} size="large">
            <div className="warning-modal">
                <h2>Action Required</h2>
                <p className="warning-subtitle">Photo processed successfully but needs manual configuration</p>

                {/* Photo preview */}
                <div className="warning-photo-preview">
                    <img src={photo.thumbnail_url} alt="Warning photo" />
                </div>

                {/* Warning details */}
                <div className="warning-details">
                    <div className="warning-type">
                        <span className="warning-icon">⚠</span>
                        <strong>{errorType}</strong>
                    </div>
                    <div className="error-message">
                        {photo.error_details}
                    </div>
                    <div className="error-timestamp">
                        Failed at: {formatDateTime(photo.processing_status_updated_at)}
                    </div>
                </div>

                {/* Fix UI (depends on error type) */}
                {errorType === 'Missing Location' && (
                    <FixLocationForm
                        photo={photo}
                        onFixed={(location) => setFixData({ storage_location_id: location.id })}
                    />
                )}

                {errorType === 'Not Configured' && (
                    <FixConfigMessage
                        photo={photo}
                        onNavigateConfig={() => {
                            window.open('/admin/storage-locations', '_blank')
                        }}
                    />
                )}

                {errorType === 'Needs Calibration' && (
                    <FixCalibrationMessage
                        photo={photo}
                        onNavigateCalibration={() => {
                            window.open('/admin/calibration', '_blank')
                        }}
                    />
                )}

                {/* Action buttons */}
                <div className="error-modal-actions">
                    <button onClick={onClose} className="btn-secondary">
                        Cancel
                    </button>

                    {fixData && (
                        <button
                            onClick={() => handleReprocess(photo, fixData)}
                            className="btn-primary"
                            disabled={fixing}
                        >
                            {fixing ? 'Reprocessing...' : 'Reprocess Photo'}
                        </button>
                    )}
                </div>
            </div>
        </Modal>
    )

    async function handleReprocess(photo: Photo, fixData: any) {
        setFixing(true)

        try {
            const response = await fetch(
                `/api/v1/photos/${photo.image_id}/reprocess`,
                {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${getToken()}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        reason: `User fixed ${errorType}`,
                        ...fixData
                    })
                }
            )

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`)
            }

            const result = await response.json()

            showSuccess('Photo reprocessing started')

            // Navigate to job monitor
            navigate(`/jobs?upload_session_id=${result.upload_session_id}`)

            onClose()

        } catch (error) {
            showError(`Reprocessing failed: ${error.message}`)
        } finally {
            setFixing(false)
        }
    }
}
```

### 3. Fix Location Form (needs_location) (lines 440-560)

**Manual location selection:**
```tsx
function FixLocationForm({
    photo,
    onFixed
}: {
    photo: Photo
    onFixed: (location: StorageLocation) => void
}) {
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [selectedWarehouse, setSelectedWarehouse] = useState<number | null>(null)
    const [locations, setLocations] = useState<StorageLocation[]>([])
    const [selectedLocation, setSelectedLocation] = useState<StorageLocation | null>(null)

    useEffect(() => {
        loadWarehouses()
    }, [])

    useEffect(() => {
        if (selectedWarehouse) {
            loadLocations(selectedWarehouse)
        }
    }, [selectedWarehouse])

    async function loadWarehouses() {
        const response = await fetch('/api/v1/warehouses')
        const data = await response.json()
        setWarehouses(data.warehouses)
    }

    async function loadLocations(warehouseId: number) {
        const response = await fetch(
            `/api/v1/storage-locations?warehouse_id=${warehouseId}&status=active`
        )
        const data = await response.json()
        setLocations(data.locations)
    }

    return (
        <div className="fix-location-form">
            <h3>Select Storage Location</h3>

            <p className="help-text">
                This photo doesn't have GPS coordinates or the GPS location doesn't match
                any registered cultivation area. Please manually select where this photo
                was taken.
            </p>

            {/* Warehouse selector */}
            <div className="form-group">
                <label>Warehouse</label>
                <select
                    value={selectedWarehouse || ''}
                    onChange={(e) => setSelectedWarehouse(Number(e.target.value))}
                >
                    <option value="">Select warehouse...</option>
                    {warehouses.map(w => (
                        <option key={w.id} value={w.id}>
                            {w.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* Location selector (only if warehouse selected) */}
            {selectedWarehouse && (
                <div className="form-group">
                    <label>Storage Location</label>
                    <select
                        value={selectedLocation?.id || ''}
                        onChange={(e) => {
                            const location = locations.find(l => l.id === Number(e.target.value))
                            setSelectedLocation(location || null)
                            if (location) {
                                onFixed(location)
                            }
                        }}
                    >
                        <option value="">Select location...</option>
                        {locations.map(l => (
                            <option key={l.id} value={l.id}>
                                {l.full_path}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {/* Selected location preview */}
            {selectedLocation && (
                <div className="location-preview">
                    <strong>Selected:</strong> {selectedLocation.full_path}
                    <br />
                    <span className="text-muted">
                        {selectedLocation.product_type} - {selectedLocation.packaging_type}
                    </span>
                </div>
            )}
        </div>
    )
}
```

### 4. Fix Config Message (needs_config) (lines 600-680)

**Admin action required:**
```tsx
function FixConfigMessage({
    photo,
    onNavigateConfig
}: {
    photo: Photo
    onNavigateConfig: () => void
}) {
    return (
        <div className="fix-config-message">
            <h3>Configuration Required</h3>

            <p className="help-text">
                The storage location for this photo has been identified, but it hasn't
                been configured with product and packaging information yet.
            </p>

            <div className="config-steps">
                <h4>To fix this:</h4>
                <ol>
                    <li>Click "Configure Location" below to open the storage location manager</li>
                    <li>Set the product type (e.g., "Lettuce", "Tomato")</li>
                    <li>Set the packaging type (e.g., "Plug tray 72", "4-inch pot")</li>
                    <li>Set expected density (plants per container)</li>
                    <li>Save the configuration</li>
                    <li>Return here and click "Reprocess Photo"</li>
                </ol>
            </div>

            {photo.processing_session?.storage_location_id && (
                <div className="location-info">
                    <strong>Storage Location:</strong>{' '}
                    {photo.processing_session.storage_location_name || 'Unknown'}
                </div>
            )}

            <button
                onClick={onNavigateConfig}
                className="btn-secondary"
            >
                Configure Location →
            </button>

            <div className="note">
                <strong>Note:</strong> This requires admin permissions. If you don't have
                access, contact your administrator.
            </div>
        </div>
    )
}
```

### 5. Backend: Reprocess Endpoint (lines 720-900)

**FastAPI implementation:**
```python
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

router = APIRouter()

class ReprocessRequest(BaseModel):
    reason: str
    storage_location_id: Optional[int] = None  # Manual override

@router.post('/photos/{image_id}/reprocess')
async def reprocess_photo(
    image_id: UUID = Path(...),
    request: ReprocessRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess a failed photo from S3 original

    This skips the upload step and goes directly to ML processing,
    optionally with user-provided fixes (e.g., manual location)

    Returns:
        {
            "status": "accepted",
            "image_id": "uuid",
            "new_job_id": "celery-task-id",
            "upload_session_id": "uuid",  // For job monitoring
            "message": "Photo reprocessing started"
        }
    """

    # Get image record
    query = select(S3Image).where(
        S3Image.image_id == image_id,
        S3Image.uploaded_by_user_id == current_user.id
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(404, 'Image not found')

    # Verify S3 file still exists
    if not image.s3_key_original:
        raise HTTPException(400, 'Image not uploaded to S3 yet')

    # Generate new upload session ID (for job monitoring)
    upload_session_id = str(uuid.uuid4())

    # Create reprocessing job
    task = celery_app.send_task(
        'process_uploaded_photo',
        kwargs={
            'image_id': str(image.image_id),
            's3_key_original': image.s3_key_original,
            'upload_session_id': upload_session_id,
            'db_record_id': image.id,
            # Pass manual overrides
            'manual_storage_location_id': request.storage_location_id,
            'reprocessing': True  # Flag to indicate this is a reprocess
        },
        queue='ml_processing',
        priority=7  # Higher priority than normal uploads
    )

    # Update image status
    image.status = 'processing'
    image.error_details = None  # Clear previous error
    image.processing_status_updated_at = datetime.utcnow()
    await db.commit()

    # Store job metadata in Redis (for polling)
    import redis.asyncio as redis
    redis_client = await redis.from_url('redis://localhost:6379')

    job_data = {
        'job_id': task.id,
        'image_id': str(image.image_id),
        'filename': image.s3_key_original.split('/')[-1],
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'reprocessing': True
    }

    await redis_client.setex(
        f'upload_session:{upload_session_id}',
        86400,  # 24 hours TTL
        json.dumps({
            'upload_session_id': upload_session_id,
            'total_jobs': 1,
            'jobs': [job_data],
            'user_id': current_user.id,
            'created_at': datetime.utcnow().isoformat(),
            'reason': request.reason
        })
    )

    # Log reprocessing event
    logger.info(
        f'Reprocessing photo {image_id} - User: {current_user.id} - '
        f'Reason: {request.reason} - Job: {task.id}'
    )

    return {
        'status': 'accepted',
        'image_id': str(image.image_id),
        'new_job_id': task.id,
        'upload_session_id': upload_session_id,
        'poll_url': f'/api/v1/photos/jobs/status?upload_session_id={upload_session_id}',
        'message': 'Photo reprocessing started from S3 original'
    }
```

**Status code:** 202 Accepted (asynchronous operation)

### 6. Celery Task: Handle Reprocessing (lines 940-1080)

**Modified task to handle manual overrides:**
```python
@celery_app.task(
    name='process_uploaded_photo',
    base=CallbackTask,
    bind=True
)
def process_uploaded_photo(
    self,
    image_id: str,
    s3_key_original: str,
    upload_session_id: str,
    db_record_id: int = None,
    manual_storage_location_id: int = None,
    reprocessing: bool = False
):
    """
    Process uploaded photo with optional manual overrides

    Args:
        image_id: UUID of s3_images record
        s3_key_original: S3 key for original image
        upload_session_id: Grouping ID for batch uploads
        db_record_id: Database record ID (if already exists)
        manual_storage_location_id: User-provided location (override GPS matching)
        reprocessing: True if this is a reprocess (not initial upload)
    """

    logger.info(f'Processing photo {image_id} - Reprocessing: {reprocessing}')

    self.update_job_status(
        self.request.id,
        'processing',
        started_at=datetime.utcnow().isoformat()
    )

    try:
        # Step 1: Download from S3
        image_data = download_from_s3(s3_key_original)

        # Step 2: ML segmentation
        segmentation_result = run_segmentation(image_data)

        # Step 3: Detection
        detection_result = run_detection(segmentation_result)

        # Step 4: Location matching
        if manual_storage_location_id:
            # Use manual location (skip GPS matching)
            logger.info(f'Using manual location: {manual_storage_location_id}')
            storage_location_id = manual_storage_location_id
        else:
            # Normal GPS-based matching
            location_result = match_storage_location(detection_result)
            storage_location_id = location_result.get('storage_location_id')

        # Step 5: Check if location is configured
        if storage_location_id:
            location = get_storage_location(storage_location_id)

            if not location.product_type or not location.packaging_type:
                # Location not configured - fail with needs_config
                raise ValueError(f'needs_config: Storage location {storage_location_id} not configured')

            if not location.density_calibration_id:
                # No calibration data - fail with needs_calibration
                raise ValueError(f'needs_calibration: Product type {location.product_type} needs calibration')

        else:
            # No location identified - fail with needs_location
            raise ValueError('needs_location: GPS coordinates not found or outside cultivation area')

        # Step 6: Save processing session
        session_id = save_processing_session(
            image_id=image_id,
            storage_location_id=storage_location_id,
            detection_result=detection_result
        )

        # Step 7: Update s3_images status
        update_image_status(image_id, 'ready')

        logger.info(f'Successfully processed photo {image_id} - Session: {session_id}')

        return {
            'session_id': session_id,
            'total_detected': detection_result['total_detected'],
            'storage_location_id': storage_location_id
        }

    except ValueError as e:
        # Expected errors (needs_location, needs_config, needs_calibration)
        error_message = str(e)
        logger.warning(f'Photo {image_id} failed with recoverable error: {error_message}')

        # Update image status to failed with error details
        update_image_status(image_id, 'failed', error_details=error_message)

        # Re-raise to trigger on_failure callback
        raise

    except Exception as e:
        # Unexpected errors
        logger.error(f'Photo {image_id} failed with unexpected error: {e}', exc_info=True)

        # Update image status
        update_image_status(image_id, 'failed', error_details=f'Unexpected error: {str(e)}')

        # Re-raise
        raise
```

### 7. Reprocessing Flow Summary (lines 1120-1200)

**Complete reprocessing journey:**

1. **User sees error badge in gallery** (red/yellow indicator)
2. **User clicks "Fix" button** (opens error modal)
3. **System shows error details** (type, message, timestamp)
4. **User applies fix** (select location, or navigate to config/calibration)
5. **User clicks "Reprocess"** (triggers API call)
6. **Backend creates new Celery job** (from S3 original, with manual overrides)
7. **User navigates to job monitor** (polls for status)
8. **ML processing runs** (5-10 minutes, same as initial upload)
9. **Result appears in gallery** (success or new error state)

**Key advantages:**
- **No re-upload needed**: Uses S3 original (saves time and bandwidth)
- **Preserves original**: Original photo never modified
- **User-driven**: User decides when to fix and reprocess
- **Idempotent**: Safe to reprocess multiple times
- **Higher priority**: Reprocessing jobs get priority over new uploads

## Performance Breakdown

**Reprocessing timing:**

| Phase | Time | Details |
|-------|------|---------|
| **Error modal load** | 50ms | Render modal with error details |
| **Load location options** | 100ms | Fetch warehouses and locations |
| **User selects location** | ~30s | Human interaction time |
| **Reprocess API call** | 200ms | Create job, update DB, return 202 |
| **Job queue wait** | 0-60s | Wait for GPU worker availability |
| **ML processing** | 5-10 min | Same as initial upload |
| **Total user time** | ~30s | From error to job monitoring |

**No re-upload overhead:**
- Saves ~10-30s upload time
- Saves network bandwidth (5-20MB per photo)
- S3 download faster than user upload (~1-2s vs 5-10s)

## Error Handling

### 1. Reprocessing Fails Again

**Scenario:** User fixes location, but photo still fails (different error)

**Behavior:**
- New error details shown in gallery
- User can click "Fix" again
- Repeat until success or give up

**Limit:** No automatic limit on reprocessing attempts (manual user action required)

### 2. S3 Original Not Found

**Scenario:** S3 file deleted or corrupted

**Response:**
```python
if not verify_s3_file_exists(s3_key_original):
    raise HTTPException(400, 'Original image not found in S3. Cannot reprocess.')
```

**User sees:** "Cannot reprocess: original file not found"

### 3. Concurrent Reprocessing

**Scenario:** User clicks "Reprocess" multiple times rapidly

**Prevention:**
```tsx
const [reprocessing, setReprocessing] = useState(false)

async function handleReprocess() {
    if (reprocessing) {
        return  // Prevent duplicate requests
    }

    setReprocessing(true)
    try {
        await reprocessPhoto()
    } finally {
        setReprocessing(false)
    }
}
```

### 4. Permission Issues

**Scenario:** User tries to reprocess photo they don't own

**Backend check:**
```python
if image.uploaded_by_user_id != current_user.id:
    raise HTTPException(403, 'Forbidden')
```

## Related Diagrams

- **03_photo_gallery_view.mmd:** Gallery view where errors are displayed
- **01_photo_upload_initiation.mmd:** Original upload flow
- **02_job_monitoring_progress.mmd:** Monitoring reprocessing job

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial error recovery subflow |

---

**Notes:**
- Reprocessing uses S3 original (no re-upload needed)
- Manual overrides preserved in processing session
- Higher priority than normal uploads (faster processing)
- Idempotent and safe to retry
- Graceful degradation: partial results preserved even on error
