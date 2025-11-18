#!/usr/bin/env python3
"""Generate comprehensive tools documentation from JSON"""

import json
from pathlib import Path


def get_category_description(category: str) -> str:
    """Get description for tool category"""
    descriptions = {
        "custom": "Custom integrations and external service tools",
        "debug": "Debugging, validation, and code analysis tools",
        "executable": "General-purpose executable tools for code generation and manipulation",
        "fixer": "Automatic code fixing and error correction tools",
        "llm": "LLM-powered tools for intelligent code generation and analysis",
        "mcp": "Model Context Protocol integration tools",
        "networking": "Network operations and API tools",
        "openapi": "OpenAPI/Swagger specification tools",
        "optimization": "Code optimization and performance improvement tools",
        "perf": "Performance monitoring and profiling tools"
    }
    return descriptions.get(category, "Miscellaneous tools")


with open("tools_data.json", 'r') as f:
    tools_data = json.load(f)

# Count total tools
total_tools = sum(len(tools) for tools in tools_data.values())

md = f"""# Code Evolver - Complete Tools Reference

**Total Tools: {total_tools}**
**Last Updated: 2025-11-18**

This document provides a comprehensive reference of all {total_tools} preconfigured tools available in the Code Evolver system, organized by category.

## Table of Contents

"""

# Generate TOC
for category in sorted(tools_data.keys()):
    tool_count = len(tools_data[category])
    md += f"- [{category.upper()}](#{category}) ({tool_count} tools)\n"

md += "\n---\n\n"

# Generate detailed sections
for category in sorted(tools_data.keys()):
    tools = tools_data[category]
    md += f"## {category.upper()}\n\n"
    md += f"**{len(tools)} tools** - {get_category_description(category)}\n\n"

    # Sort tools alphabetically
    for tool in sorted(tools, key=lambda t: t['name']):
        md += f"### {tool['name']}\n\n"
        md += f"**File:** `{tool['file']}`  \n"
        md += f"**Type:** `{tool['type']}`  \n\n"
        md += f"{tool['description']}\n\n"

        if tool['tags']:
            md += f"**Tags:** {', '.join(f'`{tag}`' for tag in tool['tags'])}\n\n"

        md += "---\n\n"

# Write to file
Path("TOOLS_REFERENCE.md").write_text(md, encoding='utf-8')
print(f"Generated TOOLS_REFERENCE.md with {total_tools} tools")
