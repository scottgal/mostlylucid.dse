# PostgreSQL Bulk Data Storage Integration

This document describes the PostgreSQL integration for bulk data storage in DiSE (Data-Intelligent Self-Evolving) system.

## Overview

DiSE now uses a **hybrid storage architecture** that combines:

- **RAG (Qdrant Vector Database)**: For semantic search and tool discovery
- **PostgreSQL**: For bulk data storage (detailed logs, bug histories, tool ancestry, etc.)

This separation optimizes for both **semantic similarity searches** and **detailed bulk data storage**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DiSE Storage Layer                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐              ┌──────────────────┐     │
│  │   RAG (Qdrant)   │              │    PostgreSQL    │     │
│  │                  │              │                  │     │
│  │  Semantic Search │              │  Bulk Data Store │     │
│  │  - Tool Discovery│              │  - Detailed Logs │     │
│  │  - Patterns      │              │  - Bug Histories │     │
│  │  - Code Fixes    │              │  - Ancestry      │     │
│  │  - Workflows     │              │  - Perf Metrics  │     │
│  │  - Prompts       │              │  - Generated     │     │
│  │                  │              │    Tools         │     │
│  └──────────────────┘              └──────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## What Goes Where?

### RAG Storage (Semantic Search)
Store in RAG for **finding similar items**:
- ✅ **Plans**: Overseer strategies
- ✅ **Functions**: Reusable code
- ✅ **Workflows**: Complete workflows
- ✅ **Tools**: Tool definitions (for discovery)
- ✅ **Prompts**: Reusable prompts
- ✅ **Patterns**: Design patterns
- ✅ **Code Fixes**: Searchable fixes

### PostgreSQL Storage (Bulk Data)
Store in Postgres for **detailed records**:
- ✅ **Failures**: Tool failures with detailed error logs
- ✅ **Bug Reports**: Full stack traces and bug histories
- ✅ **Debug Data**: Detailed debug information
- ✅ **Performance Data**: Detailed performance metrics
- ✅ **Conversations**: Tool creation conversations/ancestry
- ✅ **Generated Tools**: Full YAML + code for generated tools

### Hybrid Storage (Both)
Store in **BOTH** for different query patterns:
- 🔄 **Performance**: RAG for similarity, Postgres for detailed metrics
- 🔄 **Evaluation**: RAG for quality scores, Postgres for full test results

---

## Configuration

### config.yaml

```yaml
database:
  enabled: true
  type: "postgres"
  host: "${POSTGRES_HOST:-localhost}"
  port: "${POSTGRES_PORT:-5432}"
  database: "${POSTGRES_DB:-dise_data}"
  user: "${POSTGRES_USER:-dise}"
  password: "${POSTGRES_PASSWORD:-dise123}"

  # Connection pooling
  min_connections: 1
  max_connections: 10

  # Storage strategy
  storage_strategy:
    # Store generated tools in database (on by default)
    store_generated_tools: true

    # Artifact types to store in Postgres bulk storage
    bulk_storage_types:
      - "failure"
      - "bug_report"
      - "debug_data"
      - "perf_data"
      - "conversation"

    # Artifact types to keep in RAG for semantic search
    rag_storage_types:
      - "plan"
      - "function"
      - "sub_workflow"
      - "workflow"
      - "tool"
      - "prompt"
      - "pattern"
      - "code_fix"

    # Store in BOTH
    hybrid_storage_types:
      - "performance"
      - "evaluation"
```

### Environment Variables

Set these in your environment or `.env` file:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dise_data
POSTGRES_USER=dise
POSTGRES_PASSWORD=dise123
```

---

## Docker Setup

### Start Services

```bash
cd code_evolver
docker-compose -f docker-compose.localdev.yml up -d
```

This starts:
- **Loki**: Log aggregation (port 3100)
- **Qdrant**: Vector database for RAG (port 6333)
- **Grafana**: Visualization (port 3000)
- **PostgreSQL**: Bulk data storage (port 5432)

### Stop Services

```bash
docker-compose -f docker-compose.localdev.yml down
```

### View Logs

```bash
docker-compose -f docker-compose.localdev.yml logs -f postgres
```

---

## Database Schema

The following tables are automatically created:

### tool_logs
Detailed log messages from tools:
```sql
CREATE TABLE tool_logs (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(255) NOT NULL,
    log_level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### tool_bugs
Bug reports with stack traces:
```sql
CREATE TABLE tool_bugs (
    id SERIAL PRIMARY KEY,
    bug_id VARCHAR(255) UNIQUE NOT NULL,
    tool_id VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    stack_trace TEXT,
    details JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);
```

### tool_ancestry
Tool lineage and relationships:
```sql
CREATE TABLE tool_ancestry (
    id SERIAL PRIMARY KEY,
    parent_tool_id VARCHAR(255) NOT NULL,
    child_tool_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### tool_performance
Performance metrics:
```sql
CREATE TABLE tool_performance (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(255) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC,
    unit VARCHAR(50),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### generated_tools
Generated tool definitions and code:
```sql
CREATE TABLE generated_tools (
    id SERIAL PRIMARY KEY,
    tool_id VARCHAR(255) UNIQUE NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_type VARCHAR(50) NOT NULL,
    tool_yaml TEXT,
    tool_code TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Tools

### 1. postgres_client

Low-level PostgreSQL client for executing queries.

**Location**: `code_evolver/tools/executable/postgres_client.yaml`

**Operations**:
- `query`: Execute SELECT queries
- `execute`: Execute non-SELECT statements (INSERT, UPDATE, DELETE, DDL)
- `insert`: Insert a record
- `update`: Update records
- `delete`: Delete records

**Example**:
```python
from tools_manager import ToolsManager

tools = ToolsManager()
result = tools.invoke_tool("postgres_client", {
    "operation": "query",
    "sql": "SELECT * FROM tool_logs WHERE tool_id = %(tool_id)s",
    "params": {"tool_id": "my_tool"}
})
```

### 2. bulk_data_store

High-level bulk data storage tool.

**Location**: `code_evolver/tools/executable/bulk_data_store.yaml`

**Operations**:
- `initialize_schema`: Create database tables
- `store_log`: Store detailed log message
- `store_bug`: Store bug report
- `store_ancestry`: Store tool ancestry
- `store_perf_data`: Store performance data
- `store_tool`: Store generated tool
- `query_logs`: Query log messages
- `query_bugs`: Query bug reports
- `get_ancestry`: Get full ancestry tree

**Example**:
```python
# Store a log message
result = tools.invoke_tool("bulk_data_store", {
    "operation": "store_log",
    "tool_id": "my_tool",
    "log_level": "error",
    "message": "Failed to execute query",
    "details": {"query": "SELECT * FROM users", "error": "Table not found"}
})

# Query logs
result = tools.invoke_tool("bulk_data_store", {
    "operation": "query_logs",
    "filters": {"tool_id": "my_tool", "log_level": "error"},
    "limit": 50
})

# Get ancestry
result = tools.invoke_tool("bulk_data_store", {
    "operation": "get_ancestry",
    "tool_id": "my_tool"
})
```

---

## Programmatic API

### DatabaseStorage Module

The `DatabaseStorage` class provides a programmatic API:

```python
from database_storage import DatabaseStorage

# Initialize
db = DatabaseStorage(config_manager=config_manager)

# Store a log
db.store_log(
    tool_id="my_tool",
    log_level="error",
    message="Something went wrong",
    details={"context": "additional info"}
)

# Store a bug
db.store_bug(
    bug_id="BUG-2024-001",
    tool_id="parser_tool",
    severity="high",
    message="Parser crashes on malformed JSON",
    stack_trace="Traceback..."
)

# Store ancestry
db.store_ancestry(
    parent_tool_id="code_optimizer_v1",
    child_tool_id="code_optimizer_v2",
    relationship_type="optimized_from",
    details={"improvement": "2x faster"}
)

# Query logs
logs = db.query_logs(
    filters={"tool_id": "my_tool", "log_level": "error"},
    limit=100
)

# Get ancestry tree
ancestry = db.get_tool_ancestry("my_tool", depth=10)
```

---

## Automatic Tool Storage

When `database.storage_strategy.store_generated_tools` is `true` (default), **all generated tools are automatically stored** in PostgreSQL.

This happens in:
- `ToolsManager.register_tool()`
- `ToolsManager.register_function()`
- `ToolsManager.register_llm()`

**Generated tools** (not from YAML files) are stored with:
- Tool ID, name, type
- Full YAML definition
- Implementation code
- Metadata

---

## Benefits

### 1. Optimized Storage
- **RAG**: Fast semantic search for similar tools/patterns
- **Postgres**: Efficient bulk data queries, complex filtering, aggregations

### 2. Reduced RAG Bloat
- Don't store detailed logs in vector database
- Keep RAG focused on semantic similarity

### 3. Rich Query Capabilities
- SQL queries for complex filtering
- Recursive queries for ancestry trees
- Aggregations for performance analytics
- Full-text search on logs and stack traces

### 4. Scalability
- Postgres handles large bulk data efficiently
- RAG stays small and fast
- Can archive old data from Postgres

### 5. Debugging & Analysis
- Full bug history with stack traces
- Detailed performance metrics over time
- Tool lineage and evolution tracking
- Comprehensive log analysis

---

## Best Practices

### 1. Use RAG for Discovery
```python
# Find similar tools
similar_tools = tools.find_similar("parse JSON data")
```

### 2. Use Postgres for Details
```python
# Get detailed error logs for a tool
logs = db.query_logs(
    filters={"tool_id": "json_parser", "log_level": "error"},
    limit=100
)
```

### 3. Use Both for Analysis
```python
# RAG: Find similar patterns
patterns = rag.find_similar("optimization strategy")

# Postgres: Get performance data
for pattern in patterns:
    perf_data = db.query_performance(
        filters={"tool_id": pattern.tool_id}
    )
```

### 4. Store Ancestry for Evolution
```python
# When creating optimized version
db.store_ancestry(
    parent_tool_id="original_tool",
    child_tool_id="optimized_tool",
    relationship_type="optimized_from",
    details={"optimization_type": "performance", "improvement": "2x faster"}
)
```

### 5. Track Bugs and Fixes
```python
# Store bug
db.store_bug(
    bug_id=f"BUG-{timestamp}",
    tool_id="my_tool",
    severity="high",
    message="Tool crashes on edge case",
    stack_trace=traceback
)

# When fixed, store the fix
rag.store_artifact(
    artifact_type=ArtifactType.CODE_FIX,
    name="Fix for edge case crash",
    content=fix_code,
    tags=["bug-fix", "my_tool"]
)
```

---

## Troubleshooting

### Connection Issues

Check if Postgres is running:
```bash
docker ps | grep postgres
```

Test connection:
```bash
docker exec -it code_evolver_postgres psql -U dise -d dise_data -c "SELECT version();"
```

### Schema Not Created

Manually initialize:
```python
from database_storage import DatabaseStorage
db = DatabaseStorage(config_manager=config_manager)
db._initialize_schema()
```

### Performance Issues

Check connection pool settings in `config.yaml`:
```yaml
database:
  min_connections: 1
  max_connections: 10
```

---

## Future Enhancements

- **Automatic archiving**: Move old data to cold storage
- **Analytics dashboard**: Grafana dashboards for Postgres data
- **Cross-database queries**: Join RAG semantic search with Postgres filters
- **Backup/restore**: Automated backup strategies
- **Replication**: Multi-region Postgres setup

---

## References

- **Tools Directory**: `code_evolver/tools/executable/`
- **Source Code**: `code_evolver/src/database_storage.py`
- **Configuration**: `code_evolver/config.yaml`
- **Docker Compose**: `code_evolver/docker-compose.localdev.yml`
