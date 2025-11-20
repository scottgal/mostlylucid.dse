#!/usr/bin/env python3
"""
Quick demonstration of the language converter.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "code_evolver" / "src"))

from language_converter import (
    ConversionContext,
    ConversionStrategy,
    Language,
    PythonToJavaScriptConverter
)

# Sample Python code to convert
sample_code = """
import json
import sys

def add_numbers(a, b):
    \"\"\"Add two numbers together.\"\"\"
    return a + b

def multiply_numbers(x, y):
    \"\"\"Multiply two numbers.\"\"\"
    result = x * y
    return result

def process_list(items):
    \"\"\"Process a list of items.\"\"\"
    results = []
    for item in items:
        if item > 0:
            results.append(item * 2)
    return results

def main():
    # Test the functions
    sum_result = add_numbers(5, 3)
    product = multiply_numbers(4, 6)

    data = [1, -2, 3, -4, 5]
    processed = process_list(data)

    output = {
        "sum": sum_result,
        "product": product,
        "processed": processed
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
"""

# Tool definition
tool_definition = {
    "name": "Number Processor",
    "type": "executable",
    "version": "1.0.0",
    "description": "A simple number processing tool",
    "tool_id": "number_processor_v1",
    "executable": {
        "command": "python",
        "args": ["number_processor.py"]
    }
}

# Create converter
print("Creating Python to JavaScript converter...")
converter = PythonToJavaScriptConverter()

# Create conversion context
print("Setting up conversion context...")
context = ConversionContext(
    source_language=Language.PYTHON,
    target_language=Language.JAVASCRIPT,
    tool_definition=tool_definition,
    source_code=sample_code,
    strategy=ConversionStrategy.AST_BASED
)

# Perform conversion
print("\n" + "="*60)
print("Converting Python code to JavaScript...")
print("="*60 + "\n")

result = converter.convert_code(context)

# Display results
if result.success:
    print("✓ Conversion successful!\n")

    print("="*60)
    print("CONVERTED JAVASCRIPT CODE:")
    print("="*60)
    print(result.target_code)
    print()

    if result.warnings:
        print("="*60)
        print(f"WARNINGS ({len(result.warnings)}):")
        print("="*60)
        for warning in result.warnings:
            print(f"  - {warning}")
        print()

    if result.target_definition:
        print("="*60)
        print("CONVERTED TOOL DEFINITION:")
        print("="*60)
        print(f"Command: {result.target_definition['executable']['command']}")
        print(f"Args: {result.target_definition['executable']['args']}")
        print()

    if result.package_config:
        print("="*60)
        print("PACKAGE.JSON:")
        print("="*60)
        import json
        print(json.dumps(result.package_config, indent=2))
        print()

    print("="*60)
    print("METADATA:")
    print("="*60)
    print(f"Imports found: {result.metadata.get('imports', [])}")
    print(f"Functions found: {len(result.metadata.get('functions', []))}")
    for func in result.metadata.get('functions', []):
        print(f"  - {func['name']}({', '.join(func['args'])})")
    print()

else:
    print("✗ Conversion failed!\n")
    print("="*60)
    print("ERRORS:")
    print("="*60)
    for error in result.errors:
        print(f"  - {error}")
    print()

print("="*60)
print("Demo completed!")
print("="*60)
