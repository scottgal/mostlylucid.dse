# Optimize Tools Command

Analyze RAG memory patterns and suggest tool optimizations using the pattern clusterer.

## Usage

- `/optimize_tools` - Analyze all RAG artifacts for optimization opportunities
- `/optimize_tools <target>` - Apply optimization pressure to a specific function/code area

## Task

Use the pattern clusterer to:
1. Analyze RAG artifacts for recurring patterns (optionally filtered by target)
2. Identify clusters of similar operations
3. Suggest new parameterized tools that could optimize these patterns
4. Generate tool definitions for the most promising clusters
5. Provide an optimization report with potential savings

When a target is specified (e.g., `/optimize_tools monitor_api_and_sendemail`), the analysis will focus on artifacts related to that specific function or code area, applying evolutionary pressure to optimize those constraints.

## Steps

1. **Run Pattern Analysis**
   - Execute `code_evolver/src/pattern_clusterer.py` to analyze RAG memory
   - Set clustering parameters:
     - `min_cluster_size`: 3 (minimum operations to form a cluster)
     - `similarity_threshold`: 0.7 (70% similarity required)
   - Save report to `optimization_reports/`

2. **Review Results**
   - Display top 5 optimization opportunities
   - Show for each cluster:
     - Operation type
     - Number of similar operations
     - Similarity score
     - Suggested tool name
     - Extracted parameters
     - Example operations
     - Optimization potential (0-1 score)

3. **Generate Tool Definitions**
   - For clusters with optimization potential > 0.5:
     - Generate YAML tool definitions
     - Save to `tools/suggested/`
     - Include parameter mappings and examples

4. **Provide Summary**
   - Total patterns analyzed
   - Number of clusters found
   - Estimated time savings (hours/week)
   - Recommended next steps

## Output Format

```
=== Pattern Optimization Analysis ===

Analyzed: XXX RAG artifacts
Found: YY clusters
High-value opportunities: ZZ

Top Optimization Opportunities:
────────────────────────────────

1. [cluster_id] OPERATION_TYPE
   Cluster Size: XX operations
   Similarity: 0.XX
   Potential: 0.XX

   Suggested Tool: tool_name
   Parameters: [param1, param2, ...]

   Examples:
   - operation example 1
   - operation example 2
   - operation example 3

   Tool definition saved to: tools/suggested/tool_name.yaml

[Repeat for top 5 clusters]

=== Summary ===
Estimated time savings: XX hours/week
Recommended: Review and register XX suggested tools

Next steps:
1. Review generated tool definitions in tools/suggested/
2. Test suggested tools with sample inputs
3. Register approved tools using /create_tool or tools_manager.register_*()
```

## Implementation

Run this Python code:

```python
import sys
import os
from pathlib import Path

# Add code_evolver to path
sys.path.insert(0, str(Path.cwd() / "code_evolver" / "src"))

from pattern_clusterer import PatternClusterer
from rag_memory import RAGMemory
import json

# Parse arguments - get target filter if provided
# Arguments are passed after the command name (e.g., /optimize_tools monitor_api)
args = sys.argv[1:] if len(sys.argv) > 1 else []
target_filter = args[0] if args else None

# Initialize RAG and clusterer
rag = RAGMemory()
clusterer = PatternClusterer(rag)

# Run analysis
if target_filter:
    print(f"🔍 Analyzing RAG patterns with optimization pressure on '{target_filter}'...\n")
else:
    print("🔍 Analyzing RAG patterns for optimization opportunities...\n")

clusters = clusterer.analyze_patterns(target_filter=target_filter)

# Sort by optimization potential
sorted_clusters = sorted(
    clusters,
    key=lambda c: c.optimization_potential,
    reverse=True
)

# Display results
print(f"=== Pattern Optimization Analysis ===\n")
print(f"Analyzed: {len(rag.memories)} RAG artifacts")
print(f"Found: {len(clusters)} clusters")
high_value = [c for c in clusters if c.optimization_potential > 0.5]
print(f"High-value opportunities: {len(high_value)}\n")

print("Top Optimization Opportunities:")
print("─" * 60 + "\n")

# Create output directory
Path("tools/suggested").mkdir(parents=True, exist_ok=True)
Path("optimization_reports").mkdir(parents=True, exist_ok=True)

# Show top 5
for i, cluster in enumerate(sorted_clusters[:5], 1):
    print(f"{i}. [{cluster.cluster_id}] {cluster.operation_type}")
    print(f"   Cluster Size: {len(cluster.artifacts)} operations")
    print(f"   Similarity: {cluster.similarity_score:.2f}")
    print(f"   Potential: {cluster.optimization_potential:.2f}")
    print(f"   ")
    print(f"   Suggested Tool: {cluster.suggested_tool_name}")
    print(f"   Parameters: {cluster.suggested_parameters}")
    print(f"   ")
    print(f"   Examples:")
    for ex in cluster.example_operations[:3]:
        print(f"   - {ex}")

    # Generate tool definition if high value
    if cluster.optimization_potential > 0.5:
        tool_def = clusterer.generate_tool_definition(cluster)
        output_file = f"tools/suggested/{cluster.suggested_tool_name}.yaml"
        with open(output_file, 'w') as f:
            f.write(tool_def)
        print(f"   ")
        print(f"   ✅ Tool definition saved to: {output_file}")

    print()

# Save detailed report
report = clusterer.save_optimization_report(
    clusters,
    "optimization_reports/latest.json"
)

# Summary
print("\n=== Summary ===")
estimated_hours = sum(c.optimization_potential * len(c.artifacts) * 0.1 for c in high_value)
print(f"Estimated time savings: {estimated_hours:.1f} hours/week")
print(f"Recommended: Review and register {len(high_value)} suggested tools\n")

print("Next steps:")
print("1. Review generated tool definitions in tools/suggested/")
print("2. Test suggested tools with sample inputs")
print("3. Register approved tools using /create_tool or tools_manager.register_*()")
```
