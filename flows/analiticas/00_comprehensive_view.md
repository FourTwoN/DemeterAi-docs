# Analytics System Overview - DemeterAI

## Purpose

This diagram provides an **executive-level view** of the complete DemeterAI Analytics System, showing how users can analyze cultivation data through multiple approaches: manual filtering, sales comparison, and AI-powered insights.

## Scope

- **Level**: High-level architectural overview
- **Audience**: Business analysts, technical leads, product managers
- **Detail**: Simplified flow showing major analysis paths and their interactions
- **Mermaid Version**: v11.3.0+ (using modern syntax)

## What It Represents

The diagram illustrates three main analytics approaches:

1. **Manual Filtering Analytics**: Traditional database queries with UI filters
   - Filter by warehouse, storage area, storage location
   - Filter by product (family, category), packaging
   - Filter by date ranges, states
   - Generate standard reports and visualizations

2. **Sales vs Stock Comparison**: Upload CSV files to compare actual sales with calculated stock
   - Upload monthly sales CSV files
   - Compare with stock calculated from last photo session
   - Show estimated current stock (stock - sales)
   - Maintain historical accuracy (changes only affect latest active stock)

3. **AI-Powered Analytics**: Natural language queries with LLM integration
   - OpenAI-compatible API integration
   - Read-only database access
   - Automatic SQL query generation
   - Python-based chart generation (SVG, Mermaid, or data for frontend)
   - Intelligent insight discovery

4. **Data Export**: Export all analytics results to Excel/CSV

## Key Components

### Analysis Paths

#### Path 1: Manual Filters
- **Input**: User selects filters via UI
- **Process**: Backend constructs optimized SQL queries
- **Output**: Charts, tables, aggregated metrics
- **Performance**: < 500ms for most queries (uses materialized views)

#### Path 2: Sales Comparison
- **Input**: CSV files with sales data (product, packaging, quantity)
- **Process**:
  - Parse CSV files
  - Query latest active stock from database
  - Calculate difference (stock - sales = estimated current)
  - Generate comparison reports
- **Output**: Stock vs Sales reports, variance analysis
- **Note**: Historical stock remains unchanged (only latest active stock considered)

#### Path 3: AI Analytics
- **Input**: Natural language query (e.g., "Show mortality comparison between nave 1 and 2")
- **Process**:
  - LLM receives query + database schema
  - Generates SQL query
  - Executes query (read-only)
  - Analyzes results
  - Generates visualization (Python code execution)
- **Output**: Custom charts, insights, recommendations
- **Security**: Read-only database access, query validation, execution sandboxing

### Database Tables Involved

Primary tables for analytics:
- `warehouses`, `storage_areas`, `storage_locations`, `storage_bins`
- `stock_batches`, `stock_movements`
- `products`, `product_families`, `product_categories`
- `packaging_catalog`, `price_list`
- `photo_processing_sessions`, `s3_images`

### Performance Optimization

1. **Materialized Views**: Pre-aggregated data for common queries
2. **Database Indexes**: Optimized for filtering operations
3. **Query Caching**: Redis cache for frequent analytics requests
4. **Pagination**: Large result sets paginated

### Export Capabilities

All analytics can be exported to:
- **Excel (.xlsx)**: Formatted with charts and styling
- **CSV**: Raw data for external processing
- **PDF**: Professional reports with visualizations

## Related Detailed Diagrams

For implementation-level details, see:

- **Manual Filters**: `flows/analiticas/01_manual_filters_query.mmd`
- **Sales vs Stock**: `flows/analiticas/02_sales_vs_stock_comparison.mmd`
- **AI Analytics**: `flows/analiticas/03_ai_powered_analytics.mmd`
- **Data Export**: `flows/analiticas/04_data_export.mmd`

## How It Fits in the System

The Analytics System is a **read-only analysis layer** that:

- Does NOT modify cultivation data
- Provides multiple analysis approaches for different user needs
- Enables data-driven decision making
- Supports both simple and complex analytical queries
- Maintains historical accuracy by only considering latest active stock for current estimates

## Use Cases

### Business User (Manual Filters)
- "Show me mortality rate by storage area for the last 3 months"
- "Compare product distribution across warehouses"
- "Find storage locations with low occupancy"

### Operations Manager (Sales Comparison)
- "Upload this month's sales and show me current estimated stock"
- "Compare actual sales vs projected sales from 3 months ago"
- "Identify discrepancies between sales data and stock calculations"

### Advanced Analyst (AI-Powered)
- "Show me the correlation between mortality rates and storage location characteristics"
- "Generate a heatmap of product density across all warehouses"
- "Predict which storage areas might need restocking based on historical patterns"

## Technical Highlights

### Security Considerations

**AI Analytics Isolation**:
- Read-only database user for LLM queries
- SQL query validation and sanitization
- Execution timeout limits (30s max)
- Python code sandboxing for chart generation
- Rate limiting to prevent abuse

### Data Integrity

**Historical Stock Handling**:
- Sales comparisons use snapshot methodology
- Historical data remains immutable
- Only latest active stock affected by current changes
- Time-based partitioning for efficient queries

## Usage Workflow

1. **User** selects analysis type (Manual/Sales/AI)
2. **System** presents appropriate interface
3. **User** provides input (filters/CSV/natural language)
4. **Backend** processes request:
   - Manual: Query database with filters
   - Sales: Parse CSV + compare with stock
   - AI: LLM generates query + visualization
5. **System** returns results (charts, tables, insights)
6. **User** optionally exports to Excel/CSV

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
