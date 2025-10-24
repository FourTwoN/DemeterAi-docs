# HOTFIX: Transform SAHI Detection Coordinates and Improve Visualization

**Created**: 2025-10-24
**Priority**: HIGH (production bug - visualization misalignment)
**Status**: IN-PROGRESS
**Complexity**: 5 points (Medium)

---

## Problem Statement

**Critical Issue**: SAHI detection coordinates stored in database are relative to segment crops (0-based), NOT relative to original full image. This causes visualization circles to appear in wrong locations.

**Root Cause**:
1. `PipelineCoordinator.process_complete_pipeline()` crops each segment before SAHI detection
2. SAHI returns detections with coordinates relative to the CROPPED image
3. These crop-relative coordinates are stored directly in database WITHOUT transformation
4. Visualization code in `ml_tasks.py` uses these coordinates directly on full image → MISALIGNMENT

**Example**:
- Original image: 4000x3000px
- Segment bbox: (1000, 500, 2000, 1500) → crop is 1000x1000px
- SAHI detects plant at (200, 300) in crop
- **WRONG**: Database stores (200, 300) → visualization draws at (200, 300) in full image
- **CORRECT**: Database should store (1200, 800) → visualization aligns perfectly

---

## Solution: Option 1 (Transform at Source)

**Decision**: Transform coordinates in `PipelineCoordinator` when storing detections

**Why**:
- Database stores absolute coordinates (source of truth)
- Visualization code remains simple
- Future analytics use correct coordinates
- No migration needed for old data (accept historical visualizations are wrong)

---

## Implementation Plan

### Part A: Coordinate Transformation (Python Expert)

**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/pipeline_coordinator.py`

**Changes Required**:

1. **After SAHI detection** (line 277-282), transform coordinates:
   ```python
   # Run SAHI detection on segment crop
   detections = await self.sahi_service.detect_in_segmento(
       image_path=segment_crop_path,
       confidence_threshold=conf_threshold_detect,
   )

   # NEW: Transform coordinates from crop-relative to full-image-absolute
   segment_bbox = segment.bbox  # (x1_norm, y1_norm, x2_norm, y2_norm)

   # Convert normalized bbox to absolute pixels
   from PIL import Image
   img = Image.open(image_path)
   img_width, img_height = img.size

   segment_x1_px = int(segment_bbox[0] * img_width)
   segment_y1_px = int(segment_bbox[1] * img_height)

   # Transform each detection's coordinates
   for det in detections:
       det.center_x_px += segment_x1_px
       det.center_y_px += segment_y1_px
       # Note: width_px and height_px remain unchanged (size not affected by offset)

   all_detections.extend(detections)
   ```

2. **Verify transformation** with logging:
   ```python
   logger.debug(
       f"[Session {session_id}] Segment {idx}: Transformed {len(detections)} detections "
       f"by offset ({segment_x1_px}, {segment_y1_px})"
   )
   ```

**Expected Result**:
- Detections stored in database have coordinates relative to original full image
- Future visualizations align perfectly
- Old data remains unchanged (accept historical inaccuracy)

---

### Part B: Visualization Improvements (Python Expert)

**File**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`

**Function**: `_generate_visualization()` (lines 1160-1475)

**Changes Required**:

1. **Replace green circles with bounding boxes** (lines 1289-1319):
   ```python
   # OLD: Draw filled circles
   # cv2.circle(overlay, (center_x, center_y), radius, color_green, -1)

   # NEW: Draw semi-transparent bounding boxes with confidence-based colors
   for det in detections:
       center_x = int(det["center_x_px"])
       center_y = int(det["center_y_px"])
       width = int(det["width_px"])
       height = int(det["height_px"])
       confidence = float(det.get("confidence", 0.0))

       # Calculate bbox corners
       x1 = int(center_x - width / 2)
       y1 = int(center_y - height / 2)
       x2 = int(center_x + width / 2)
       y2 = int(center_y + height / 2)

       # Confidence-based color (red → yellow → cyan)
       if confidence >= 0.8:
           color = (0, 255, 255)  # Cyan (high confidence)
       elif confidence >= 0.5:
           color = (0, 255, 255)  # Yellow (medium confidence)
       else:
           color = (0, 0, 255)    # Red (low confidence)

       # Draw semi-transparent bounding box
       cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)

       # Draw center dot for precision
       cv2.circle(overlay, (center_x, center_y), 3, color, -1)

   # Blend with alpha=0.4 for professional appearance
   image = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)
   ```

2. **Update legend** to reflect new visualization style:
   ```python
   # Add legend entry for visualization style
   cv2.putText(
       image,
       f"Style: Bounding boxes (confidence-colored)",
       (10, 120),
       font,
       font_scale,
       color_white,
       font_thickness,
   )
   ```

**Expected Result**:
- Bounding boxes instead of circles (more precise)
- Confidence-based color coding (visual quality indicator)
- Semi-transparent overlay (professional appearance)
- Center dots for exact detection points

---

### Part C: Integration Tests (Testing Expert)

**File**: `/home/lucasg/proyectos/DemeterDocs/tests/integration/test_pipeline_coordinator_coordinate_transform.py` (NEW)

**Test Cases**:

1. **Test coordinate transformation with known segment offset**:
   ```python
   async def test_detection_coordinates_transformed_by_segment_offset():
       """Verify SAHI detections are transformed from crop-relative to full-image-absolute."""
       # Setup: Create test image with known dimensions
       # Setup: Mock segment with known bbox (e.g., x1=1000, y1=500)
       # Setup: Mock SAHI detection at (200, 300) in crop

       # Act: Run pipeline
       result = await coordinator.process_complete_pipeline(...)

       # Assert: Detection stored at (1200, 800) in database
       assert result.detections[0]["center_x_px"] == 1200.0
       assert result.detections[0]["center_y_px"] == 800.0
   ```

2. **Test visualization aligns with detections**:
   ```python
   async def test_visualization_circles_align_with_detections():
       """Verify visualization circles are drawn at correct coordinates."""
       # Setup: Create session with known detections
       # Act: Generate visualization
       viz_path = _generate_visualization(session_id, detections, estimations)

       # Assert: Load visualization and verify circle positions
       # (Use OpenCV to detect circles and compare with detection coordinates)
   ```

3. **Test multiple segments with different offsets**:
   ```python
   async def test_multiple_segments_each_transformed_correctly():
       """Verify each segment's detections are transformed by its own offset."""
       # Setup: Image with 3 segments at different positions
       # Act: Run pipeline
       # Assert: Each segment's detections have correct absolute coordinates
   ```

**Expected Coverage**: ≥80% for coordinate transformation logic

---

## Acceptance Criteria

### Part A: Coordinate Transformation
- [x] User confirmed Option 1 (transform at source)
- [ ] `PipelineCoordinator.process_complete_pipeline()` transforms coordinates after SAHI detection
- [ ] Transformation adds segment bbox offset to `center_x_px` and `center_y_px`
- [ ] Logging added to verify transformation per segment
- [ ] Manual test with known segment shows correct absolute coordinates in database

### Part B: Visualization
- [ ] Replaced green circles with semi-transparent bounding boxes
- [ ] Confidence-based color coding implemented (red → yellow → cyan)
- [ ] Center dots added for precision
- [ ] Alpha blending set to 0.4 for professional appearance
- [ ] Legend updated to reflect new visualization style

### Part C: Testing
- [ ] Integration test verifies coordinate transformation with known offset
- [ ] Integration test verifies visualization alignment (manual inspection)
- [ ] Integration test covers multiple segments with different offsets
- [ ] All tests pass
- [ ] Coverage ≥80% for modified code

### Part D: Quality Gates
- [ ] Code review approved (Team Leader)
- [ ] No hallucinated code (all imports verified)
- [ ] Tests pass (pytest)
- [ ] Coverage ≥80%
- [ ] Manual verification with real photo shows correct alignment

---

## Files Modified

1. `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/pipeline_coordinator.py`
   - Add coordinate transformation after SAHI detection (line ~282)
   - Add segment offset calculation
   - Add transformation logging

2. `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`
   - Replace green circles with bounding boxes (line ~1289-1319)
   - Add confidence-based color coding
   - Add center dots
   - Update alpha blending
   - Update legend

3. `/home/lucasg/proyectos/DemeterDocs/tests/integration/test_pipeline_coordinator_coordinate_transform.py` (NEW)
   - Test coordinate transformation with known offset
   - Test visualization alignment
   - Test multiple segments

---

## Architecture Context

**Layer**: Service Layer (ML Processing)

**Pattern**:
- Transform data at source (PipelineCoordinator stores absolute coordinates)
- Visualization consumes absolute coordinates directly (no transform needed)

**Dependencies**:
- PipelineCoordinator → SAHI Detection Service
- ML Tasks (Celery) → Visualization generation
- Database stores absolute coordinates (source of truth)

**Performance**:
- Transformation overhead: Negligible (simple addition per detection)
- No impact on SAHI inference speed
- No impact on visualization rendering speed

---

## Testing Strategy

**Unit Tests**: Not needed (transformation is integration-level concern)

**Integration Tests**:
1. Test coordinate transformation with known segment offset
2. Test visualization alignment (manual inspection)
3. Test multiple segments (verify each offset applied correctly)

**Manual Verification**:
1. Run ML pipeline on real greenhouse photo
2. Generate visualization
3. Verify bounding boxes align with actual plants
4. Verify confidence colors are visible
5. Verify center dots are precise

---

## Rollout Plan

**Phase 1**: Implement coordinate transformation (Part A)
- Deploy to staging
- Test with known segment offsets
- Verify database coordinates are absolute

**Phase 2**: Improve visualization (Part B)
- Deploy to staging
- Generate visualizations for existing sessions
- Verify new style is professional and clear

**Phase 3**: Integration tests (Part C)
- Write tests
- Verify all tests pass
- Achieve ≥80% coverage

**Phase 4**: Production deployment
- Deploy to production
- Monitor first few sessions
- Verify visualizations align correctly

**Note**: Old visualizations remain incorrect (no migration). Accept this as technical debt.

---

## Team Leader Notes

**Spawned Specialists**:
- Python Expert #1: Coordinate transformation (Part A)
- Python Expert #2: Visualization improvements (Part B) [Can be same or parallel]
- Testing Expert: Integration tests (Part C)

**Coordination**:
- Part A and Part B can be implemented in parallel (independent changes)
- Part C depends on Parts A and B completing

**Timeline**:
- Part A: 1-2 hours (coordinate transformation + testing)
- Part B: 1-2 hours (visualization improvements + testing)
- Part C: 2 hours (integration tests)
- Total: 4-6 hours

**Next Steps**:
1. Spawn Python Expert for Part A
2. Spawn Python Expert for Part B (parallel)
3. After Parts A+B complete, spawn Testing Expert for Part C
4. Run quality gates
5. Manual verification
6. Approve completion

---

## References

- **Original Issue**: User reported misaligned visualization circles
- **Root Cause Analysis**: SAHI coordinates are crop-relative, not image-absolute
- **Decision**: User approved Option 1 (transform at source)
- **Database Schema**: `detections.center_x_px`, `detections.center_y_px` are NUMERIC(10,2)
- **Visualization Code**: `ml_tasks.py` lines 1289-1319 (circle drawing)
- **Coordinate Transformation**: Lines 266-298 in `pipeline_coordinator.py` (SAHI detection loop)
