# Create Tool Command

Create a new tool to parse CSV files and output patterns using the workflows system.

## Task

Create a comprehensive CSV pattern analyzer tool that:
1. Parses CSV files with various delimiters and encodings
2. Detects patterns in the data (numeric, categorical, temporal, etc.)
3. Outputs pattern analysis with statistics
4. Uses the workflows system for processing
5. Registers the tool in ToolsManager

## Usage

`/create_tool`

This will create a tool called `csv_pattern_analyzer` with the following capabilities:
- Parse CSV files with automatic delimiter detection
- Analyze column types and patterns
- Detect data quality issues
- Generate pattern reports
- Suggest data transformations

## Steps

1. **Create CSV Parser Function**
   - Multi-delimiter support (comma, tab, semicolon, pipe)
   - Encoding detection (UTF-8, Latin-1, etc.)
   - Header detection
   - Type inference for columns

2. **Create Pattern Detector**
   - Numeric patterns (ranges, distributions, outliers)
   - Categorical patterns (frequency, cardinality)
   - Temporal patterns (date/time formats)
   - Text patterns (length, format, regex matches)
   - Missing data patterns

3. **Create Workflow Definition**
   - Step 1: Load and parse CSV
   - Step 2: Analyze column types
   - Step 3: Detect patterns per column
   - Step 4: Generate report
   - Step 5: Suggest optimizations

4. **Register Tool**
   - Register as workflow tool in ToolsManager
   - Add appropriate tags
   - Include usage examples

5. **Create Test Cases**
   - Sample CSV files for testing
   - Expected pattern outputs

## Output Format

```
=== Creating CSV Pattern Analyzer Tool ===

📝 Step 1: Creating CSV parser function
✅ Created: code_evolver/src/tools/csv_parser.py

📊 Step 2: Creating pattern detector
✅ Created: code_evolver/src/tools/pattern_detector.py

🔄 Step 3: Creating workflow definition
✅ Created: workflows/csv_pattern_analyzer.json

📋 Step 4: Registering tool in ToolsManager
✅ Registered: csv_pattern_analyzer

🧪 Step 5: Creating test cases
✅ Created: tests/test_csv_pattern_analyzer.py
✅ Created: test_data/sample.csv

────────────────────────────────

Tool Details:
  ID: csv_pattern_analyzer
  Type: workflow
  Description: Analyzes CSV files and detects data patterns
  Tags: [csv, parser, pattern, analysis, data-quality]

Workflow Steps:
  1. parse_csv - Parse CSV file with auto-detection
  2. analyze_types - Infer column types
  3. detect_patterns - Find patterns in each column
  4. generate_report - Create analysis report
  5. suggest_optimizations - Recommend transformations

Usage Example:

  from tools_manager import ToolsManager

  manager = ToolsManager()
  tool = manager.get_tool("csv_pattern_analyzer")

  result = tool.execute({
      "csv_file": "data/my_data.csv",
      "output_format": "json"
  })

  print(result["patterns"])

────────────────────────────────

✅ CSV Pattern Analyzer tool created successfully!

Next steps:
1. Test with sample CSV: python -m pytest tests/test_csv_pattern_analyzer.py
2. Use in workflow: See examples in workflows/csv_pattern_analyzer.json
3. View tool: /list_tools tag:csv
```

## Implementation

Run this Python code:

```python
import sys
import json
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path.cwd() / "code_evolver" / "src"))

from tools_manager import ToolsManager, Tool, ToolType
from workflow_spec import WorkflowSpec, WorkflowStep

print("=== Creating CSV Pattern Analyzer Tool ===\n")

# Step 1: Create CSV Parser Function
print("📝 Step 1: Creating CSV parser function")

tools_dir = Path("code_evolver/src/tools")
tools_dir.mkdir(parents=True, exist_ok=True)

csv_parser_code = '''"""CSV Parser with auto-detection capabilities."""
import csv
import chardet
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from collections import Counter


def detect_encoding(file_path: str) -> str:
    """Detect file encoding."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'


def detect_delimiter(file_path: str, encoding: str) -> str:
    """Detect CSV delimiter."""
    with open(file_path, 'r', encoding=encoding) as f:
        first_line = f.readline()

    # Try common delimiters
    delimiters = [',', '\\t', ';', '|', ' ']
    delimiter_counts = {d: first_line.count(d) for d in delimiters}

    # Return delimiter with highest count
    return max(delimiter_counts, key=delimiter_counts.get)


def parse_csv(
    file_path: str,
    delimiter: Optional[str] = None,
    encoding: Optional[str] = None,
    has_header: bool = True
) -> Dict[str, Any]:
    """
    Parse CSV file with auto-detection.

    Args:
        file_path: Path to CSV file
        delimiter: Column delimiter (auto-detected if None)
        encoding: File encoding (auto-detected if None)
        has_header: Whether first row is header

    Returns:
        Dictionary with:
            - headers: List of column names
            - rows: List of row dictionaries
            - metadata: Parsing metadata
    """
    # Auto-detect encoding
    if encoding is None:
        encoding = detect_encoding(file_path)

    # Auto-detect delimiter
    if delimiter is None:
        delimiter = detect_delimiter(file_path, encoding)

    # Parse CSV
    rows = []
    headers = []

    with open(file_path, 'r', encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)

        if has_header:
            headers = next(reader)
        else:
            # Generate default headers
            first_row = next(reader)
            headers = [f"column_{i}" for i in range(len(first_row))]
            rows.append(dict(zip(headers, first_row)))

        for row in reader:
            if len(row) == len(headers):
                rows.append(dict(zip(headers, row)))

    return {
        "headers": headers,
        "rows": rows,
        "metadata": {
            "row_count": len(rows),
            "column_count": len(headers),
            "delimiter": delimiter,
            "encoding": encoding,
            "file_path": file_path
        }
    }
'''

parser_file = tools_dir / "csv_parser.py"
with open(parser_file, 'w') as f:
    f.write(csv_parser_code)

print(f"✅ Created: {parser_file}\n")

# Step 2: Create Pattern Detector
print("📊 Step 2: Creating pattern detector")

pattern_detector_code = '''"""Pattern detection for CSV data."""
import re
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime
import statistics


def infer_type(values: List[str]) -> str:
    """Infer column type from values."""
    non_empty = [v for v in values if v and v.strip()]

    if not non_empty:
        return "empty"

    # Try numeric
    try:
        [float(v) for v in non_empty]
        # Check if all are integers
        if all(float(v).is_integer() for v in non_empty):
            return "integer"
        return "numeric"
    except ValueError:
        pass

    # Try date/time
    date_formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"
    ]

    for fmt in date_formats:
        try:
            [datetime.strptime(v, fmt) for v in non_empty[:10]]
            return "datetime"
        except ValueError:
            continue

    # Check if boolean
    bool_values = {"true", "false", "yes", "no", "1", "0", "y", "n"}
    if all(v.lower() in bool_values for v in non_empty):
        return "boolean"

    # Default to text
    return "text"


def detect_patterns(column_name: str, values: List[str]) -> Dict[str, Any]:
    """
    Detect patterns in a column.

    Returns:
        Dictionary with pattern analysis
    """
    non_empty = [v for v in values if v and v.strip()]
    empty_count = len(values) - len(non_empty)

    col_type = infer_type(values)

    pattern = {
        "column": column_name,
        "type": col_type,
        "total_count": len(values),
        "non_empty_count": len(non_empty),
        "empty_count": empty_count,
        "missing_percentage": (empty_count / len(values) * 100) if values else 0
    }

    if not non_empty:
        return pattern

    # Type-specific patterns
    if col_type == "integer":
        int_values = [int(float(v)) for v in non_empty]
        pattern.update({
            "min": min(int_values),
            "max": max(int_values),
            "mean": statistics.mean(int_values),
            "median": statistics.median(int_values),
            "unique_count": len(set(int_values))
        })

    elif col_type == "numeric":
        float_values = [float(v) for v in non_empty]
        pattern.update({
            "min": min(float_values),
            "max": max(float_values),
            "mean": statistics.mean(float_values),
            "median": statistics.median(float_values),
            "stdev": statistics.stdev(float_values) if len(float_values) > 1 else 0
        })

    elif col_type == "text":
        pattern.update({
            "min_length": min(len(v) for v in non_empty),
            "max_length": max(len(v) for v in non_empty),
            "avg_length": sum(len(v) for v in non_empty) / len(non_empty),
            "unique_count": len(set(non_empty)),
            "cardinality": len(set(non_empty)) / len(non_empty)
        })

        # Detect common formats
        if all(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$', v) for v in non_empty[:10]):
            pattern["format"] = "email"
        elif all(re.match(r'^https?://', v) for v in non_empty[:10]):
            pattern["format"] = "url"
        elif all(re.match(r'^\\d{3}-\\d{3}-\\d{4}$', v) for v in non_empty[:10]):
            pattern["format"] = "phone"

    # Frequency analysis for categorical data
    if len(set(non_empty)) < len(non_empty) * 0.5:  # More than 50% duplicates
        counter = Counter(non_empty)
        pattern["top_values"] = counter.most_common(5)
        pattern["is_categorical"] = True

    return pattern


def analyze_csv_patterns(csv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze patterns in entire CSV.

    Args:
        csv_data: Output from csv_parser.parse_csv()

    Returns:
        Pattern analysis report
    """
    headers = csv_data["headers"]
    rows = csv_data["rows"]

    # Extract columns
    columns = {
        header: [row.get(header, "") for row in rows]
        for header in headers
    }

    # Detect patterns per column
    patterns = [
        detect_patterns(col_name, values)
        for col_name, values in columns.items()
    ]

    # Overall statistics
    total_cells = len(rows) * len(headers)
    empty_cells = sum(p["empty_count"] for p in patterns)

    # Data quality score (0-100)
    quality_score = (
        ((total_cells - empty_cells) / total_cells * 40) +  # Completeness
        (min(len(set(columns[h])) / len(rows) for h in headers) * 30) +  # Uniqueness
        (len([p for p in patterns if p["type"] != "empty"]) / len(patterns) * 30)  # Valid types
    ) if total_cells > 0 else 0

    return {
        "metadata": csv_data["metadata"],
        "patterns": patterns,
        "overall": {
            "total_cells": total_cells,
            "empty_cells": empty_cells,
            "completeness_percentage": ((total_cells - empty_cells) / total_cells * 100) if total_cells > 0 else 0,
            "data_quality_score": quality_score
        },
        "suggestions": _generate_suggestions(patterns)
    }


def _generate_suggestions(patterns: List[Dict[str, Any]]) -> List[str]:
    """Generate optimization suggestions based on patterns."""
    suggestions = []

    for p in patterns:
        # Missing data
        if p["missing_percentage"] > 20:
            suggestions.append(f"Column '{p['column']}' has {p['missing_percentage']:.1f}% missing data - consider imputation or removal")

        # Low cardinality
        if p.get("is_categorical") and p["type"] == "text":
            suggestions.append(f"Column '{p['column']}' is categorical - consider encoding or factorization")

        # High cardinality IDs
        if p.get("unique_count", 0) == p["non_empty_count"] and p["type"] in ["text", "integer"]:
            suggestions.append(f"Column '{p['column']}' appears to be a unique identifier")

    return suggestions
'''

detector_file = tools_dir / "pattern_detector.py"
with open(detector_file, 'w') as f:
    f.write(pattern_detector_code)

print(f"✅ Created: {detector_file}\n")

# Step 3: Create Workflow Definition
print("🔄 Step 3: Creating workflow definition")

workflow_def = {
    "workflow_id": "csv_pattern_analyzer",
    "description": "Analyzes CSV files and detects data patterns",
    "version": "1.0.0",
    "portable": True,
    "inputs": {
        "csv_file": {
            "type": "string",
            "description": "Path to CSV file to analyze",
            "required": True
        },
        "delimiter": {
            "type": "string",
            "description": "Column delimiter (auto-detected if not provided)",
            "required": False
        },
        "encoding": {
            "type": "string",
            "description": "File encoding (auto-detected if not provided)",
            "required": False
        }
    },
    "outputs": {
        "patterns": {
            "type": "object",
            "description": "Pattern analysis results"
        }
    },
    "steps": [
        {
            "step_id": "parse",
            "type": "python_tool",
            "description": "Parse CSV file",
            "tool": "csv_parser",
            "function": "parse_csv",
            "input_mapping": {
                "file_path": "inputs.csv_file",
                "delimiter": "inputs.delimiter",
                "encoding": "inputs.encoding"
            },
            "output_name": "parsed_data"
        },
        {
            "step_id": "analyze",
            "type": "python_tool",
            "description": "Analyze patterns",
            "tool": "pattern_detector",
            "function": "analyze_csv_patterns",
            "input_mapping": {
                "csv_data": "steps.parse.output"
            },
            "output_name": "analysis"
        }
    ],
    "tool_definitions": {
        "csv_parser": {
            "tool_id": "csv_parser",
            "name": "CSV Parser",
            "type": "python",
            "source_code": csv_parser_code,
            "requirements": ["chardet"]
        },
        "pattern_detector": {
            "tool_id": "pattern_detector",
            "name": "Pattern Detector",
            "type": "python",
            "source_code": pattern_detector_code,
            "requirements": []
        }
    }
}

workflows_dir = Path("workflows")
workflows_dir.mkdir(parents=True, exist_ok=True)

workflow_file = workflows_dir / "csv_pattern_analyzer.json"
with open(workflow_file, 'w') as f:
    json.dump(workflow_def, f, indent=2)

print(f"✅ Created: {workflow_file}\n")

# Step 4: Register Tool
print("📋 Step 4: Registering tool in ToolsManager")

manager = ToolsManager()

tool = Tool(
    tool_id="csv_pattern_analyzer",
    name="CSV Pattern Analyzer",
    tool_type=ToolType.WORKFLOW,
    description="Analyzes CSV files and detects data patterns including types, distributions, and quality issues",
    tags=["csv", "parser", "pattern", "analysis", "data-quality"],
    implementation=workflow_def,
    parameters=[
        {"name": "csv_file", "type": "string", "required": True, "description": "Path to CSV file"},
        {"name": "delimiter", "type": "string", "required": False, "description": "Column delimiter"},
        {"name": "encoding", "type": "string", "required": False, "description": "File encoding"}
    ]
)

manager.register_tool(tool)

print(f"✅ Registered: csv_pattern_analyzer\n")

# Step 5: Create Test Cases
print("🧪 Step 5: Creating test cases")

test_dir = Path("tests")
test_dir.mkdir(parents=True, exist_ok=True)

test_code = '''"""Tests for CSV Pattern Analyzer."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "code_evolver" / "src"))

from tools_manager import ToolsManager


def test_csv_pattern_analyzer():
    """Test CSV pattern analyzer tool."""
    manager = ToolsManager()
    tool = manager.get_tool("csv_pattern_analyzer")

    assert tool is not None
    assert tool.tool_id == "csv_pattern_analyzer"
    assert "csv" in tool.tags

    # Test with sample CSV
    sample_file = Path("test_data/sample.csv")
    if sample_file.exists():
        # Note: Actual execution would require workflow engine
        print(f"Tool found and ready to process {sample_file}")
'''

test_file = test_dir / "test_csv_pattern_analyzer.py"
with open(test_file, 'w') as f:
    f.write(test_code)

print(f"✅ Created: {test_file}")

# Create sample CSV
test_data_dir = Path("test_data")
test_data_dir.mkdir(parents=True, exist_ok=True)

sample_csv = """id,name,email,age,city,signup_date
1,Alice Johnson,alice@example.com,28,New York,2023-01-15
2,Bob Smith,bob@example.com,34,Los Angeles,2023-02-20
3,Charlie Brown,charlie@example.com,22,Chicago,2023-03-10
4,Diana Prince,diana@example.com,,Miami,2023-04-05
5,Eve Davis,eve@example.com,29,Seattle,2023-05-12"""

sample_file = test_data_dir / "sample.csv"
with open(sample_file, 'w') as f:
    f.write(sample_csv)

print(f"✅ Created: {sample_file}\n")

# Print summary
print("─" * 60)
print("\nTool Details:")
print(f"  ID: csv_pattern_analyzer")
print(f"  Type: workflow")
print(f"  Description: Analyzes CSV files and detects data patterns")
print(f"  Tags: {tool.tags}")
print()
print("Workflow Steps:")
print("  1. parse_csv - Parse CSV file with auto-detection")
print("  2. analyze_patterns - Find patterns in each column")
print()
print("Usage Example:\n")
print("  from tools_manager import ToolsManager")
print()
print("  manager = ToolsManager()")
print('  tool = manager.get_tool("csv_pattern_analyzer")')
print()
print("  # Note: Execution requires workflow engine")
print('  # See workflows/csv_pattern_analyzer.json for details')
print()
print("─" * 60)
print()
print("✅ CSV Pattern Analyzer tool created successfully!\n")
print("Next steps:")
print("1. Test with sample CSV: python -m pytest tests/test_csv_pattern_analyzer.py")
print("2. View tool: /list_tools tag:csv")
print("3. Use /optimize_tools to find integration opportunities")
```
