# AI-Powered Analytics - Detailed Flow

## Purpose

This diagram shows the **detailed implementation flow** for AI-powered analytics, where users can ask natural language questions and receive automated insights, visualizations, and SQL analysis through LLM integration.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, AI/ML engineers, security engineers
- **Detail**: Complete flow from natural language query to AI-generated insights
- **Mermaid Version**: v11.3.0+

## What It Represents

The complete AI analytics flow including:

1. **Natural Language Input**: User types questions in plain language
2. **LLM Processing**: OpenAI-compatible API generates SQL and analysis plan
3. **Query Execution**: Safe, read-only SQL query execution
4. **Data Analysis**: LLM analyzes query results
5. **Visualization Generation**: Python code execution for custom charts
6. **Response Delivery**: Insights, recommendations, and visualizations

## Business Context

### The Problem

Traditional UI filters have limitations:
- Can't express complex analytical questions
- Limited to predefined aggregations
- Requires SQL knowledge for advanced queries
- Time-consuming to configure for one-off analyses

### The Solution

Allow users to ask questions like:
- "Show me mortality rate comparison between nave 1 and nave 2"
- "Which storage areas have the highest product concentration?"
- "Generate a heatmap of cactus distribution across all warehouses"
- "Find correlations between quality score and storage location characteristics"

The AI:
1. Understands the intent
2. Knows the database schema
3. Generates appropriate SQL
4. Analyzes results
5. Creates custom visualizations
6. Provides insights and recommendations

## Architecture

### Components

```
┌─────────────────┐
│   Frontend      │
│   (User Input)  │
└────────┬────────┘
         │
         │ Natural language query
         ▼
┌─────────────────┐
│   FastAPI       │
│   /api/ai-analytics
└────────┬────────┘
         │
         │ 1. Send query + schema + examples
         ▼
┌─────────────────┐
│  OpenAI API     │
│  (LLM)          │
│  - GPT-4o       │
│  - Function     │
│    calling      │
└────────┬────────┘
         │
         │ 2. Generated SQL + analysis plan
         ▼
┌─────────────────┐
│  SQL Validator  │
│  & Executor     │
│  (Read-only)    │
└────────┬────────┘
         │
         │ 3. Query results
         ▼
┌─────────────────┐
│  Python Sandbox │
│  (Chart Gen)    │
│  - matplotlib   │
│  - seaborn      │
│  - SVG output   │
└────────┬────────┘
         │
         │ 4. Visualization + insights
         ▼
┌─────────────────┐
│   Frontend      │
│   (Display)     │
└─────────────────┘
```

### Security Layers

1. **Read-Only Database User**
   - Dedicated PostgreSQL user with SELECT-only privileges
   - No DDL, DML (except SELECT), or admin operations
   - Connection string isolation

2. **SQL Query Validation**
   - Whitelist: Only SELECT statements
   - Blacklist: No DROP, DELETE, UPDATE, INSERT, ALTER, GRANT, etc.
   - Regex patterns for dangerous operations
   - AST parsing for deep validation

3. **Execution Sandboxing**
   - Query timeout: 30 seconds
   - Result row limit: 10,000 rows
   - Memory limit for Python sandbox
   - No file system access
   - No network access (except to database)

4. **Rate Limiting**
   - Max 10 queries per user per minute
   - Max 100 queries per user per hour
   - Max 1,000 queries per user per day

## Database Schema Exposure

### Schema Information Provided to LLM

The LLM receives a **curated schema description**, not raw DDL:

```json
{
  "tables": [
    {
      "name": "stock_batches",
      "description": "Current stock inventory by product and location",
      "columns": [
        {
          "name": "quantity_current",
          "type": "integer",
          "description": "Current quantity of plants in this batch"
        },
        {
          "name": "quality_score",
          "type": "numeric",
          "description": "Quality rating from 0-5 based on ML analysis"
        }
      ],
      "common_queries": [
        "SELECT COUNT(*) FROM stock_batches WHERE quantity_current > 0",
        "SELECT AVG(quality_score) FROM stock_batches"
      ]
    },
    {
      "name": "stock_movements",
      "description": "Historical movements: plantado, transplante, muerte, ventas",
      "columns": [...],
      "common_queries": [...]
    }
  ],
  "relationships": [
    {
      "from": "stock_batches",
      "to": "products",
      "type": "many_to_one",
      "join": "stock_batches.product_id = products.id"
    }
  ],
  "examples": [
    {
      "question": "Show total stock by warehouse",
      "sql": "SELECT w.name, SUM(sb.quantity_current) FROM ..."
    }
  ]
}
```

### Example Queries Provided

Pre-vetted example queries help guide the LLM:

```sql
-- Example 1: Stock by warehouse
SELECT
    w.name as warehouse,
    COUNT(DISTINCT sb.id) as batches,
    SUM(sb.quantity_current) as total_quantity
FROM stock_batches sb
JOIN storage_bins sbin ON sb.current_storage_bin_id = sbin.id
JOIN storage_locations sl ON sbin.storage_location_id = sl.id
JOIN storage_areas sa ON sl.storage_area_id = sa.id
JOIN warehouses w ON sa.warehouse_id = w.id
WHERE sb.quantity_current > 0
GROUP BY w.name;

-- Example 2: Mortality rate by area
SELECT
    sa.name,
    COUNT(*) FILTER (WHERE sm.movement_type = 'muerte') as deaths,
    COUNT(*) FILTER (WHERE sm.movement_type = 'foto') as initial,
    ROUND(
        COUNT(*) FILTER (WHERE sm.movement_type = 'muerte')::numeric /
        NULLIF(COUNT(*) FILTER (WHERE sm.movement_type = 'foto'), 0) * 100,
        2
    ) as mortality_rate_pct
FROM stock_movements sm
JOIN stock_batches sb ON sm.batch_id = sb.id
JOIN storage_bins sbin ON sb.current_storage_bin_id = sbin.id
JOIN storage_locations sl ON sbin.storage_location_id = sl.id
JOIN storage_areas sa ON sl.storage_area_id = sa.id
GROUP BY sa.name;
```

## LLM Integration

### Prompt Engineering

#### System Prompt

```python
SYSTEM_PROMPT = """
You are an expert PostgreSQL analyst for DemeterAI, a plant cultivation
management system. Your role is to help users analyze their cultivation
data through natural language queries.

**Your Capabilities:**
1. Generate PostgreSQL queries based on user questions
2. Analyze query results and provide insights
3. Generate Python code for data visualizations
4. Provide recommendations based on data patterns

**Database Schema:**
{schema_json}

**Example Queries:**
{example_queries}

**Critical Rules:**
1. ONLY generate SELECT queries (read-only)
2. NEVER use DELETE, UPDATE, INSERT, DROP, ALTER, GRANT, etc.
3. Always include WHERE clauses to filter inactive data
4. Limit results to 10,000 rows max
5. Use proper JOINs based on the schema relationships
6. Include comments explaining complex logic
7. Handle NULL values appropriately
8. Use meaningful column aliases

**Response Format:**
Always respond in JSON with this structure:
{
  "sql": "SELECT ... FROM ...",
  "explanation": "This query analyzes...",
  "expected_columns": ["col1", "col2"],
  "visualization_type": "bar_chart|line_chart|pie_chart|heatmap|table",
  "python_code": "import matplotlib...",
  "insights": ["insight 1", "insight 2"]
}

**Security:**
- You have read-only access
- Queries timeout after 30 seconds
- Results limited to 10,000 rows
- Your responses are validated before execution
"""
```

#### User Prompt Template

```python
USER_PROMPT_TEMPLATE = """
User Question: {user_query}

Context:
- Current date: {current_date}
- User role: {user_role}
- Available warehouses: {warehouse_list}

Please generate:
1. A PostgreSQL query to answer this question
2. An explanation of what the query does
3. Python code to visualize the results (if applicable)
4. Expected insights from the data

Remember:
- Use only SELECT statements
- Join tables as needed based on the schema
- Filter for active/current data where relevant
- Consider edge cases (NULL values, empty results)
"""
```

### OpenAI API Call

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_ai_analytics(
    user_query: str,
    schema_info: dict,
    examples: list
) -> AIAnalyticsResponse:
    """
    Call OpenAI API to generate SQL and analysis
    """
    response = await client.chat.completions.create(
        model="gpt-4o",  # or compatible model
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    schema_json=json.dumps(schema_info),
                    example_queries=format_examples(examples)
                )
            },
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    user_query=user_query,
                    current_date=datetime.now().isoformat(),
                    user_role=current_user.role,
                    warehouse_list=get_user_warehouses(current_user)
                )
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.2,  # Low temperature for consistency
        max_tokens=2000
    )

    ai_response = json.loads(response.choices[0].message.content)
    return AIAnalyticsResponse(**ai_response)
```

## SQL Validation

### Multi-Layer Validation

```python
import sqlparse
from sqlparse.sql import Token, Identifier
from sqlparse.tokens import Keyword, DML

def validate_sql_query(sql: str) -> tuple[bool, str]:
    """
    Validate SQL query for safety

    Returns:
        (is_valid, error_message)
    """
    # Layer 1: Regex blacklist
    dangerous_patterns = [
        r'\bDELETE\b',
        r'\bUPDATE\b',
        r'\bINSERT\b',
        r'\bDROP\b',
        r'\bALTER\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r'\bCREATE\b',
        r'\bTRUNCATE\b',
        r'\bEXECUTE\b',
        r';.*SELECT',  # Multiple statements
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"Forbidden operation detected: {pattern}"

    # Layer 2: Parse SQL AST
    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        return False, "Only single SELECT statement allowed"

    statement = parsed[0]

    # Layer 3: Check first token is SELECT
    first_token = statement.token_first(skip_ws=True, skip_cm=True)
    if first_token.ttype != Keyword.DML or first_token.value.upper() != 'SELECT':
        return False, "Query must start with SELECT"

    # Layer 4: Check for subqueries (optional, depends on requirements)
    # Could recursively validate subqueries

    return True, ""

# Example usage
is_valid, error = validate_sql_query(ai_generated_sql)
if not is_valid:
    raise SecurityError(f"Invalid SQL: {error}")
```

## Python Visualization Sandbox

### Sandboxed Execution

```python
import sys
from io import StringIO, BytesIO
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

def execute_visualization_code(
    python_code: str,
    data: pd.DataFrame,
    timeout: int = 10
) -> bytes:
    """
    Execute Python visualization code in sandboxed environment

    Args:
        python_code: Python code to generate chart
        data: Query results as DataFrame
        timeout: Max execution time in seconds

    Returns:
        SVG bytes of generated chart
    """
    # Create restricted globals
    safe_globals = {
        '__builtins__': {
            'range': range,
            'len': len,
            'enumerate': enumerate,
            'zip': zip,
            'max': max,
            'min': min,
            'sum': sum,
            'round': round,
        },
        'pd': pd,
        'np': np,
        'plt': plt,
        'sns': sns,
        'data': data,  # Query results
    }

    # Prepare code
    code_to_exec = f"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

{python_code}

# Save to BytesIO
from io import BytesIO
buffer = BytesIO()
plt.savefig(buffer, format='svg', bbox_inches='tight')
buffer.seek(0)
svg_bytes = buffer.read()
plt.close('all')
"""

    # Execute with timeout
    try:
        exec(code_to_exec, safe_globals)
        return safe_globals['svg_bytes']
    except Exception as e:
        raise VisualizationError(f"Failed to generate chart: {str(e)}")
```

### Example Visualization Code

LLM generates code like:

```python
# Create bar chart for stock by warehouse
fig, ax = plt.subplots(figsize=(10, 6))

# Sort by quantity
data_sorted = data.sort_values('total_quantity', ascending=False)

# Plot
ax.bar(data_sorted['warehouse'], data_sorted['total_quantity'])
ax.set_xlabel('Warehouse')
ax.set_ylabel('Total Quantity')
ax.set_title('Stock Distribution by Warehouse')
ax.tick_params(axis='x', rotation=45)

plt.tight_layout()
# Chart saved automatically by sandbox
```

## API Endpoint

```python
@router.post("/api/analytics/ai-query")
@limiter.limit("10/minute")
async def ai_powered_analytics(
    query: AIQueryRequest,
    db: AsyncSession = Depends(get_db_readonly),
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis)
) -> AIAnalyticsResponse:
    """
    Process natural language analytics query using AI

    Args:
        query: User's natural language question
        db: Read-only database session
        current_user: Authenticated user
        redis: Redis for caching

    Returns:
        SQL query, results, visualization, and insights
    """
    # Step 1: Call LLM to generate SQL + analysis
    ai_response = await generate_ai_analytics(
        user_query=query.question,
        schema_info=get_schema_info(),
        examples=get_example_queries()
    )

    # Step 2: Validate generated SQL
    is_valid, error = validate_sql_query(ai_response.sql)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"AI generated invalid SQL: {error}"
        )

    # Step 3: Execute SQL with timeout
    try:
        result = await asyncio.wait_for(
            db.execute(text(ai_response.sql)),
            timeout=30.0
        )
        rows = result.fetchall()
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Query execution timeout (> 30s)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )

    # Step 4: Convert to DataFrame
    df = pd.DataFrame(rows, columns=result.keys())

    # Step 5: Generate visualization
    svg_chart = None
    if ai_response.python_code:
        try:
            svg_chart = execute_visualization_code(
                ai_response.python_code,
                df
            )
        except Exception as e:
            # Visualization failure is non-fatal
            svg_chart = None

    # Step 6: Build response
    return AIAnalyticsResponse(
        question=query.question,
        sql_query=ai_response.sql,
        explanation=ai_response.explanation,
        data=df.to_dict('records'),
        visualization_svg=svg_chart.decode('utf-8') if svg_chart else None,
        insights=ai_response.insights,
        metadata={
            "row_count": len(df),
            "execution_time_ms": ...,
            "model": "gpt-4o"
        }
    )
```

## Performance & Cost Optimization

### Caching Strategy

```python
# Cache LLM responses for identical queries
cache_key = f"ai_analytics:{hash(user_query)}"
cached = await redis.get(cache_key)
if cached:
    return AIAnalyticsResponse.parse_raw(cached)

# ... generate response ...

# Cache for 1 hour
await redis.setex(cache_key, 3600, response.json())
```

### Cost Management

| Component | Cost | Optimization |
|-----------|------|--------------|
| OpenAI API call | ~$0.01 per query (GPT-4o) | Cache responses, use cheaper models for simple queries |
| Database query | Minimal | Use materialized views, optimize queries |
| Visualization | Minimal | Reuse common chart templates |

**Estimated cost**: $1-5 per 100 queries

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
