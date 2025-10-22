# Data Export - Detailed Flow

## Purpose

This diagram shows the **detailed implementation flow** for exporting analytics results to Excel and
CSV formats, allowing users to download and process data externally.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, frontend developers
- **Detail**: Complete flow from export request to file download
- **Mermaid Version**: v11.3.0+

## What It Represents

The complete export flow including:

1. **Export Trigger**: User clicks export button from any analytics view
2. **Format Selection**: Choose Excel (.xlsx) or CSV (.csv)
3. **Data Preparation**: Format and structure data for export
4. **File Generation**: Create downloadable file with proper formatting
5. **Download Delivery**: Stream file to user's browser

## Supported Export Sources

### 1. Manual Filter Results

- Aggregated query results
- Charts (embedded as images in Excel)
- Summary statistics

### 2. Sales vs Stock Comparison

- Comparison table
- Discrepancies list
- Summary metrics
- Charts (embedded)

### 3. AI Analytics Results

- Query results
- AI-generated insights (as text)
- Visualizations (as SVG converted to PNG)
- SQL query (as documentation sheet)

## Export Formats

### Excel (.xlsx) Format

**Advantages**:

- Multiple sheets for different data sections
- Formatted tables with headers
- Embedded charts and visualizations
- Cell styling (colors, bold, borders)
- Formulas for calculations
- Professional appearance

**Library**: `openpyxl` or `xlsxwriter`

**File Structure**:

```
analytics_export_20251008.xlsx
├── Summary (sheet)
│   ├── Title: "DemeterAI Analytics Export"
│   ├── Export Date: 2025-10-08 14:30:00
│   ├── User: admin@demeter.com
│   ├── Query Type: Manual Filters
│   └── Summary Statistics (formatted table)
├── Data (sheet)
│   ├── Headers (bold, colored background)
│   ├── Data rows (formatted, aligned)
│   └── Totals row (if applicable)
├── Charts (sheet)
│   ├── Chart 1 (embedded image)
│   ├── Chart 2 (embedded image)
│   └── Notes
└── Metadata (sheet)
    ├── SQL Query (if applicable)
    ├── Filters Applied
    ├── Execution Time
    └── Data Freshness Info
```

**Example Code**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd

def create_excel_export(
    data: pd.DataFrame,
    summary: dict,
    charts: list[bytes],
    metadata: dict
) -> bytes:
    """
    Create formatted Excel file from analytics data

    Returns:
        Excel file as bytes
    """
    wb = Workbook()

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"

    # Title styling
    ws_summary['A1'] = "DemeterAI Analytics Export"
    ws_summary['A1'].font = Font(size=16, bold=True, color="1976D2")
    ws_summary['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Summary stats
    row = 4
    for key, value in summary.items():
        ws_summary[f'A{row}'] = key.replace('_', ' ').title()
        ws_summary[f'B{row}'] = value
        ws_summary[f'A{row}'].font = Font(bold=True)
        row += 1

    # Sheet 2: Data
    ws_data = wb.create_sheet("Data")

    # Write dataframe to sheet
    for r_idx, row in enumerate(dataframe_to_rows(data, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws_data.cell(row=r_idx, column=c_idx, value=value)

            # Header row styling
            if r_idx == 1:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="1976D2", end_color="1976D2", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

    # Auto-adjust column widths
    for column in ws_data.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws_data.column_dimensions[column_letter].width = adjusted_width

    # Sheet 3: Charts (if provided)
    if charts:
        ws_charts = wb.create_sheet("Charts")
        # Add chart images
        # (requires PIL/Pillow to convert SVG to PNG)

    # Sheet 4: Metadata
    ws_meta = wb.create_sheet("Metadata")
    row = 1
    for key, value in metadata.items():
        ws_meta[f'A{row}'] = key
        ws_meta[f'B{row}'] = str(value)
        row += 1

    # Save to BytesIO
    from io import BytesIO
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
```

### CSV Format

**Advantages**:

- Universal compatibility
- Small file size
- Easy to import into other tools
- Plain text (version control friendly)

**Limitations**:

- Single file (no multiple sheets)
- No formatting
- No embedded images
- No formulas

**Format**: UTF-8 encoded, comma-delimited

**File Structure**:

```csv
# DemeterAI Analytics Export
# Generated: 2025-10-08 14:30:00
# Query Type: Manual Filters
# User: admin@demeter.com

# Summary Statistics
total_products,150
total_stock_value,125000.50
total_sales_value,45000.25
average_quality,4.2

# Data
warehouse,product_category,quantity,value
Warehouse A,Cactus,500,2750.00
Warehouse A,Suculenta,300,1800.00
Warehouse B,Cactus,450,2475.00
```

**Example Code**:

```python
import csv
from io import StringIO

def create_csv_export(
    data: pd.DataFrame,
    summary: dict,
    metadata: dict
) -> str:
    """
    Create CSV export with metadata comments

    Returns:
        CSV as string
    """
    output = StringIO()
    writer = csv.writer(output)

    # Metadata as comments
    writer.writerow(['# DemeterAI Analytics Export'])
    writer.writerow([f'# Generated: {datetime.now().isoformat()}'])
    writer.writerow([f'# User: {metadata.get("user")}'])
    writer.writerow([])

    # Summary
    writer.writerow(['# Summary Statistics'])
    for key, value in summary.items():
        writer.writerow([key, value])
    writer.writerow([])

    # Data
    writer.writerow(['# Data'])
    # Write headers
    writer.writerow(data.columns.tolist())
    # Write rows
    for _, row in data.iterrows():
        writer.writerow(row.tolist())

    return output.getvalue()
```

## API Endpoints

### Export Analytics Results

```python
@router.post("/api/analytics/export")
async def export_analytics(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    """
    Export analytics results to Excel or CSV

    Args:
        request: Export configuration
          - format: 'xlsx' or 'csv'
          - data: Analytics results
          - summary: Summary statistics
          - metadata: Query metadata

    Returns:
        StreamingResponse with file download
    """
    # Prepare data
    df = pd.DataFrame(request.data)

    # Generate file based on format
    if request.format == 'xlsx':
        file_content = create_excel_export(
            data=df,
            summary=request.summary,
            charts=request.charts,
            metadata=request.metadata
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    else:  # csv
        file_content = create_csv_export(
            data=df,
            summary=request.summary,
            metadata=request.metadata
        )
        media_type = "text/csv"
        extension = "csv"

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demeter_analytics_{timestamp}.{extension}"

    # Stream response
    return StreamingResponse(
        BytesIO(file_content.encode() if extension == 'csv' else file_content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
```

### Export from Frontend

```javascript
// Frontend export handler
async function exportAnalytics(format) {
    try {
        // Show loading
        showExportLoading();

        // Prepare export request
        const exportData = {
            format: format,  // 'xlsx' or 'csv'
            data: currentAnalyticsResults,
            summary: currentSummary,
            charts: currentCharts,
            metadata: {
                user: currentUser.email,
                query_type: currentQueryType,
                filters: appliedFilters,
                execution_time_ms: executionTime
            }
        };

        // Call API
        const response = await fetch('/api/analytics/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(exportData)
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        // Download file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `demeter_analytics_${Date.now()}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        // Hide loading, show success
        showExportSuccess(`Downloaded ${format.toUpperCase()} file`);

    } catch (error) {
        console.error('Export error:', error);
        showExportError('Failed to export data');
    }
}
```

## Large Dataset Handling

### Pagination for Large Exports

For datasets > 100,000 rows, use chunked export:

```python
@router.post("/api/analytics/export/large")
async def export_large_dataset(
    request: LargeExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Handle large dataset export asynchronously

    Returns task ID for polling
    """
    # Create export task
    task_id = uuid4()

    # Add background task
    background_tasks.add_task(
        generate_large_export,
        task_id=task_id,
        user_id=current_user.id,
        query=request.query,
        format=request.format
    )

    # Return task ID
    return {
        "task_id": str(task_id),
        "status": "processing",
        "estimated_time_sec": 60,
        "poll_url": f"/api/analytics/export/status/{task_id}"
    }

async def generate_large_export(
    task_id: UUID,
    user_id: int,
    query: str,
    format: str
):
    """
    Background task to generate large export

    Saves file to S3, sends email when complete
    """
    try:
        # Execute query in chunks
        chunk_size = 10000
        all_data = []

        async for chunk in execute_query_chunked(query, chunk_size):
            all_data.extend(chunk)

        # Generate file
        df = pd.DataFrame(all_data)
        file_content = create_excel_export(df, {...}, [], {...})

        # Upload to S3
        s3_key = f"exports/{user_id}/{task_id}.{format}"
        await upload_to_s3(file_content, s3_key)

        # Generate signed URL (expires in 24 hours)
        download_url = await generate_s3_signed_url(s3_key, expires=86400)

        # Send email notification
        await send_email(
            to=get_user_email(user_id),
            subject="Your DemeterAI export is ready",
            body=f"Download your export: {download_url}\n\nExpires in 24 hours."
        )

        # Update task status
        await update_export_task_status(task_id, "completed", download_url)

    except Exception as e:
        # Update task status
        await update_export_task_status(task_id, "failed", str(e))
```

## Performance Optimization

### Streaming for Large Files

Instead of loading entire file in memory:

```python
from fastapi.responses import StreamingResponse

def generate_csv_stream(data_iterator):
    """
    Stream CSV data row by row
    """
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['col1', 'col2', 'col3'])
    yield output.getvalue()
    output.seek(0)
    output.truncate()

    # Rows
    for row in data_iterator:
        writer.writerow(row)
        yield output.getvalue()
        output.seek(0)
        output.truncate()

@router.get("/api/analytics/export/stream")
async def stream_export(query_id: str):
    """
    Stream export for large datasets
    """
    # Get data iterator
    data_iter = get_analytics_data_iterator(query_id)

    return StreamingResponse(
        generate_csv_stream(data_iter),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=export.csv"
        }
    )
```

## Error Handling

### Common Errors

1. **Data Too Large**
   ```json
   {
     "error": "Dataset too large for synchronous export",
     "row_count": 500000,
     "max_rows": 100000,
     "action": "Use async export endpoint: POST /api/analytics/export/large"
   }
   ```

2. **Invalid Format**
   ```json
   {
     "error": "Invalid export format",
     "format": "pdf",
     "supported": ["xlsx", "csv"]
   }
   ```

3. **Missing Data**
   ```json
   {
     "error": "No data to export",
     "action": "Run analytics query first"
   }
   ```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
