# Claude Code Custom Commands

This directory contains custom slash commands for managing tools and optimizing workflows.

## Available Commands

### Tool Management Commands

#### `/list_tools`
List all registered tools in the ToolsManager registry.

**Usage:**
```
/list_tools                    # List all tools
/list_tools type:llm          # Filter by type
/list_tools tag:validation    # Filter by tag
/list_tools search:email      # Semantic search
```

**Features:**
- Display tools organized by type
- Show usage statistics
- Filter by type or tags
- Semantic search using RAG

---

#### `/remove_tool <tool_id>`
Remove a tool from the registry.

**Usage:**
```
/remove_tool email_validator
```

**Features:**
- Verify tool exists before removal
- Check for dependencies (workflows using the tool)
- Show warnings if tool is in use
- Clean removal from registry

**Safety:**
- Won't delete if actively used by workflows (shows warning)
- Displays tool details before removal
- Provides recommendations after deletion

---

#### `/optimize_tools`
Analyze RAG memory patterns and suggest tool optimizations using the pattern clusterer.

**Usage:**
```
/optimize_tools
```

**Features:**
- Analyzes all RAG artifacts for recurring patterns
- Identifies clusters of similar operations
- Suggests new parameterized tools
- Generates YAML tool definitions
- Provides optimization potential scores

**Output:**
- Top 5 optimization opportunities
- Cluster analysis (size, similarity, examples)
- Auto-generated tool definitions saved to `tools/suggested/`
- Detailed report saved to `optimization_reports/latest.json`
- Estimated time savings

**Workflow:**
1. Runs pattern analysis on RAG memory
2. Clusters similar operations (70% similarity threshold)
3. Extracts common parameters
4. Suggests tool names and definitions
5. Saves high-value tools (>0.5 optimization potential)

---

#### `/create_tool`
Create a CSV pattern analyzer tool using the workflows system.

**Usage:**
```
/create_tool
```

**Features:**
- Creates a complete CSV parsing and pattern analysis tool
- Auto-detects delimiters and encodings
- Analyzes data types and distributions
- Detects data quality issues
- Generates comprehensive pattern reports

**Created Components:**
- `code_evolver/src/tools/csv_parser.py` - CSV parsing with auto-detection
- `code_evolver/src/tools/pattern_detector.py` - Pattern analysis engine
- `workflows/csv_pattern_analyzer.json` - Workflow definition
- `tests/test_csv_pattern_analyzer.py` - Test cases
- `test_data/sample.csv` - Sample data

**Pattern Detection:**
- **Numeric**: ranges, distributions, outliers, statistics
- **Categorical**: frequency, cardinality, top values
- **Temporal**: date/time format detection
- **Text**: length analysis, format detection (email, URL, phone)
- **Data Quality**: missing data, completeness score

**Registered Tool:**
- **ID:** `csv_pattern_analyzer`
- **Type:** workflow
- **Tags:** csv, parser, pattern, analysis, data-quality

---

## Command Workflow

These commands work together to create an optimization cycle:

```
1. /optimize_tools
   ↓
   Analyzes RAG patterns
   ↓
   Suggests new tools
   ↓
2. /create_tool
   ↓
   Creates suggested tool
   ↓
   Registers in ToolsManager
   ↓
3. /list_tools
   ↓
   View all registered tools
   ↓
   Monitor usage statistics
   ↓
4. /optimize_tools (again)
   ↓
   Find new patterns
   ↓
5. /remove_tool (if needed)
   ↓
   Clean up unused tools
```

## Example Usage Flow

### 1. Discover Optimization Opportunities
```bash
/optimize_tools
```
Output shows you have 5 similar "translate to X" operations.

### 2. Review Suggestions
Check `tools/suggested/` for auto-generated tool definitions:
- `translate_text.yaml`
- `data_converter.yaml`
- `format_validator.yaml`

### 3. Create High-Value Tools
```bash
/create_tool
```
Creates the CSV pattern analyzer tool as an example.

### 4. List All Tools
```bash
/list_tools
```
See your new tool alongside existing ones.

### 5. Filter and Search
```bash
/list_tools tag:csv
/list_tools type:workflow
/list_tools search:pattern
```

### 6. Monitor Usage
```bash
/list_tools
```
Check which tools are used most frequently.

### 7. Clean Up (if needed)
```bash
/remove_tool old_unused_tool
```

## Integration with Pattern Clusterer

The `/optimize_tools` command leverages the `pattern_clusterer.py` system to:

1. **Analyze RAG Memory**: Scans all stored artifacts for patterns
2. **Cluster Operations**: Groups similar operations using cosine similarity
3. **Extract Parameters**: Identifies variable parts (e.g., "translate to {language}")
4. **Calculate Potential**: Scores each cluster based on:
   - Number of similar operations (40%)
   - Similarity score (40%)
   - Number of extractable parameters (20%)
5. **Generate Tools**: Creates YAML definitions for high-value clusters

## File Structure

```
.claude/
└── commands/
    ├── README.md              # This file
    ├── list_tools.md          # List tools command
    ├── remove_tool.md         # Remove tool command
    ├── optimize_tools.md      # Optimize patterns command
    └── create_tool.md         # Create CSV analyzer tool

code_evolver/src/
├── pattern_clusterer.py       # Pattern analysis engine
├── tools_manager.py           # Tool registry
└── tools/                     # Generated tool implementations
    ├── csv_parser.py
    └── pattern_detector.py

workflows/
└── csv_pattern_analyzer.json  # Workflow definitions

tools/
├── index.json                 # Tool registry
└── suggested/                 # Auto-generated suggestions
    └── *.yaml

optimization_reports/
└── latest.json                # Pattern analysis reports
```

## Dependencies

These commands integrate with:
- **ToolsManager** (`code_evolver/src/tools_manager.py`)
- **PatternClusterer** (`code_evolver/src/pattern_clusterer.py`)
- **WorkflowSpec** (`code_evolver/src/workflow_spec.py`)
- **RAGMemory** (`code_evolver/src/rag_memory.py`)

## Best Practices

1. **Run /optimize_tools regularly** - Weekly or after major feature additions
2. **Review suggestions carefully** - Not all clusters need dedicated tools
3. **Test before registering** - Use test cases for new tools
4. **Monitor usage** - Use /list_tools to see what's actually being used
5. **Clean up periodically** - Remove unused tools to keep registry clean
6. **Tag appropriately** - Good tags make tools discoverable

## Notes

- Commands use markdown format as per Claude Code conventions
- Python code blocks are embedded for execution
- All commands integrate with existing ToolsManager infrastructure
- Pattern analysis requires existing RAG artifacts to be useful
