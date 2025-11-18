#!/usr/bin/env python3
"""Extract all tool definitions from YAML files"""

import yaml
from pathlib import Path
import json

tools_dir = Path("code_evolver/tools")
all_tools = {}

for category_dir in sorted(tools_dir.iterdir()):
    if not category_dir.is_dir():
        continue

    category = category_dir.name
    all_tools[category] = []

    for yaml_file in sorted(category_dir.glob("*.yaml")):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data:
                tool_info = {
                    "file": yaml_file.name,
                    "name": data.get("name", yaml_file.stem),
                    "type": data.get("type", "unknown"),
                    "description": data.get("description", "No description"),
                    "tags": data.get("tags", [])
                }
                all_tools[category].append(tool_info)
        except Exception as e:
            print(f"Error reading {yaml_file}: {e}")

# Output as JSON
print(json.dumps(all_tools, indent=2))
