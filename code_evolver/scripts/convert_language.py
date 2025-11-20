#!/usr/bin/env python3
"""
Language Converter Tool Executable

Converts tools and workflows between programming languages.
Supports Python → JavaScript conversion with test and dependency mapping.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

from language_converter import (
    ConversionContext,
    ConversionResult,
    ConversionStrategy,
    Language,
    create_converter,
)


def load_tool_definition(tool_path: str) -> Dict[str, Any]:
    """Load tool YAML definition."""
    tool_file = Path(tool_path)

    if not tool_file.exists():
        raise FileNotFoundError(f"Tool definition not found: {tool_path}")

    with open(tool_file, "r") as f:
        return yaml.safe_load(f)


def load_source_code(code_path: str) -> str:
    """Load source code file."""
    code_file = Path(code_path)

    if not code_file.exists():
        raise FileNotFoundError(f"Source code not found: {code_path}")

    with open(code_file, "r") as f:
        return f.read()


def load_tests(test_path: Optional[str]) -> Optional[str]:
    """Load test file if provided."""
    if not test_path:
        return None

    test_file = Path(test_path)

    if not test_file.exists():
        print(f"Warning: Test file not found: {test_path}", file=sys.stderr)
        return None

    with open(test_file, "r") as f:
        return f.read()


def save_conversion_result(result: ConversionResult, output_dir: str, tool_name: str):
    """Save conversion result to output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save JavaScript code
    js_file = output_path / f"{tool_name}.js"
    with open(js_file, "w") as f:
        f.write(result.target_code)

    print(f"✓ Saved JavaScript code to: {js_file}")

    # Save tests if available
    if result.target_tests:
        test_file = output_path / f"{tool_name}.test.js"
        with open(test_file, "w") as f:
            f.write(result.target_tests)
        print(f"✓ Saved Jest tests to: {test_file}")

    # Save tool definition
    if result.target_definition:
        tool_def_file = output_path / f"{tool_name}.yaml"
        with open(tool_def_file, "w") as f:
            yaml.dump(result.target_definition, f, default_flow_style=False)
        print(f"✓ Saved tool definition to: {tool_def_file}")

    # Save package.json
    if result.package_config:
        package_file = output_path / "package.json"
        with open(package_file, "w") as f:
            json.dump(result.package_config, f, indent=2)
        print(f"✓ Saved package.json to: {package_file}")

    # Save metadata
    metadata_file = output_path / "conversion_metadata.json"
    metadata = {
        "success": result.success,
        "errors": result.errors,
        "warnings": result.warnings,
        "metadata": result.metadata,
    }
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Saved conversion metadata to: {metadata_file}")


def convert_tool(
    tool_path: str,
    source_code_path: str,
    output_dir: str,
    target_language: str = "javascript",
    test_path: Optional[str] = None,
    strategy: str = "hybrid",
    use_llm: bool = False,
) -> ConversionResult:
    """
    Convert a tool from Python to target language.

    Args:
        tool_path: Path to tool YAML definition
        source_code_path: Path to Python source code
        output_dir: Output directory for converted files
        target_language: Target language (javascript, typescript)
        test_path: Optional path to test file
        strategy: Conversion strategy (ast, llm, hybrid, template)
        use_llm: Whether to use LLM for intelligent conversion

    Returns:
        ConversionResult
    """
    # Load tool definition and source code
    tool_def = load_tool_definition(tool_path)
    source_code = load_source_code(source_code_path)
    tests = load_tests(test_path) if test_path else None

    # Parse dependencies from requirements.txt or tool definition
    dependencies = []
    if "dependencies" in tool_def:
        dependencies = tool_def["dependencies"]

    # Create conversion context
    context = ConversionContext(
        source_language=Language.PYTHON,
        target_language=Language(target_language),
        tool_definition=tool_def,
        source_code=source_code,
        tests=tests,
        dependencies=dependencies,
        strategy=ConversionStrategy(strategy),
    )

    # Get LLM client if needed
    llm_client = None
    if use_llm:
        try:
            from llm_client_factory import LLMClientFactory

            llm_client = LLMClientFactory.create_client("ollama")
        except Exception as e:
            print(f"Warning: Could not initialize LLM client: {e}", file=sys.stderr)

    # Create converter and convert
    converter = create_converter(
        source_lang=Language.PYTHON,
        target_lang=Language(target_language),
        llm_client=llm_client,
    )

    result = converter.convert_code(context)

    # Save results
    tool_name = tool_def.get("name", "converted_tool").lower().replace(" ", "_")
    save_conversion_result(result, output_dir, tool_name)

    return result


def convert_workflow(
    workflow_path: str,
    output_dir: str,
    target_language: str = "javascript",
    use_llm: bool = False,
) -> Dict[str, Any]:
    """
    Convert an entire workflow to target language.

    Args:
        workflow_path: Path to workflow JSON definition
        output_dir: Output directory for converted workflow
        target_language: Target language
        use_llm: Whether to use LLM for conversion

    Returns:
        Conversion summary
    """
    workflow_file = Path(workflow_path)

    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow not found: {workflow_path}")

    # Load workflow definition
    with open(workflow_file, "r") as f:
        workflow = json.load(f)

    print(f"\n=== Converting workflow: {workflow.get('name', 'Unknown')} ===\n")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Track conversion results
    conversion_summary = {
        "workflow_name": workflow.get("name"),
        "total_steps": len(workflow.get("steps", [])),
        "converted_steps": [],
        "failed_steps": [],
        "warnings": [],
    }

    # Convert each step that references a Python tool
    for step in workflow.get("steps", []):
        step_type = step.get("step_type")
        tool_name = step.get("tool_name")

        if step_type == "PYTHON_TOOL" and tool_name:
            print(f"Converting tool: {tool_name}")

            try:
                # Find tool definition
                tool_path = find_tool_definition(tool_name)

                if tool_path:
                    # Find source code
                    source_path = find_tool_source_code(tool_name, tool_path)

                    if source_path:
                        # Convert the tool
                        result = convert_tool(
                            tool_path=tool_path,
                            source_code_path=source_path,
                            output_dir=str(output_path / tool_name),
                            target_language=target_language,
                            use_llm=use_llm,
                        )

                        if result.success:
                            conversion_summary["converted_steps"].append(
                                {
                                    "step_id": step.get("step_id"),
                                    "tool_name": tool_name,
                                    "status": "success",
                                }
                            )
                        else:
                            conversion_summary["failed_steps"].append(
                                {
                                    "step_id": step.get("step_id"),
                                    "tool_name": tool_name,
                                    "errors": result.errors,
                                }
                            )

                        conversion_summary["warnings"].extend(result.warnings)
                    else:
                        print(f"  ⚠ Source code not found for tool: {tool_name}")
                else:
                    print(f"  ⚠ Tool definition not found: {tool_name}")

            except Exception as e:
                print(f"  ✗ Error converting {tool_name}: {e}")
                conversion_summary["failed_steps"].append(
                    {
                        "step_id": step.get("step_id"),
                        "tool_name": tool_name,
                        "errors": [str(e)],
                    }
                )

    # Save workflow conversion summary
    summary_file = output_path / "workflow_conversion_summary.json"
    with open(summary_file, "w") as f:
        json.dump(conversion_summary, f, indent=2)

    print(f"\n✓ Workflow conversion summary saved to: {summary_file}")

    return conversion_summary


def find_tool_definition(tool_name: str) -> Optional[str]:
    """Find tool YAML definition by name."""
    tools_dir = Path(__file__).parent.parent / "tools"

    # Search in all subdirectories
    for yaml_file in tools_dir.rglob("*.yaml"):
        try:
            with open(yaml_file, "r") as f:
                tool_def = yaml.safe_load(f)
                if tool_def.get("name") == tool_name or tool_def.get("tool_id") == tool_name:
                    return str(yaml_file)
        except Exception:
            continue

    return None


def find_tool_source_code(tool_name: str, tool_def_path: str) -> Optional[str]:
    """Find source code for a tool."""
    tool_def_file = Path(tool_def_path)

    # Load tool definition to get executable path
    with open(tool_def_file, "r") as f:
        tool_def = yaml.safe_load(f)

    if "executable" in tool_def and "args" in tool_def["executable"]:
        args = tool_def["executable"]["args"]
        if args and len(args) > 0:
            # First arg is usually the script path
            script_path = args[0]

            # Try relative to tool definition
            relative_path = tool_def_file.parent / script_path
            if relative_path.exists():
                return str(relative_path)

            # Try relative to project root
            project_root = Path(__file__).parent.parent
            absolute_path = project_root / script_path
            if absolute_path.exists():
                return str(absolute_path)

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert tools and workflows between programming languages"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Tool conversion command
    tool_parser = subparsers.add_parser("tool", help="Convert a single tool")
    tool_parser.add_argument("--tool-def", required=True, help="Path to tool YAML definition")
    tool_parser.add_argument("--source", required=True, help="Path to source code")
    tool_parser.add_argument(
        "--output", required=True, help="Output directory for converted files"
    )
    tool_parser.add_argument(
        "--target",
        default="javascript",
        choices=["javascript", "typescript"],
        help="Target language (default: javascript)",
    )
    tool_parser.add_argument("--tests", help="Optional path to test file")
    tool_parser.add_argument(
        "--strategy",
        default="hybrid",
        choices=["ast", "llm", "hybrid", "template"],
        help="Conversion strategy (default: hybrid)",
    )
    tool_parser.add_argument(
        "--use-llm", action="store_true", help="Use LLM for intelligent conversion"
    )

    # Workflow conversion command
    workflow_parser = subparsers.add_parser("workflow", help="Convert an entire workflow")
    workflow_parser.add_argument("--workflow", required=True, help="Path to workflow JSON")
    workflow_parser.add_argument(
        "--output", required=True, help="Output directory for converted workflow"
    )
    workflow_parser.add_argument(
        "--target",
        default="javascript",
        choices=["javascript", "typescript"],
        help="Target language (default: javascript)",
    )
    workflow_parser.add_argument(
        "--use-llm", action="store_true", help="Use LLM for intelligent conversion"
    )

    args = parser.parse_args()

    if args.command == "tool":
        try:
            result = convert_tool(
                tool_path=args.tool_def,
                source_code_path=args.source,
                output_dir=args.output,
                target_language=args.target,
                test_path=args.tests,
                strategy=args.strategy,
                use_llm=args.use_llm,
            )

            if result.success:
                print("\n✓ Tool conversion completed successfully!")
                if result.warnings:
                    print(f"\n⚠ Warnings ({len(result.warnings)}):")
                    for warning in result.warnings:
                        print(f"  - {warning}")
                sys.exit(0)
            else:
                print("\n✗ Tool conversion failed!")
                print(f"\nErrors ({len(result.errors)}):")
                for error in result.errors:
                    print(f"  - {error}")
                sys.exit(1)

        except Exception as e:
            print(f"\n✗ Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "workflow":
        try:
            summary = convert_workflow(
                workflow_path=args.workflow,
                output_dir=args.output,
                target_language=args.target,
                use_llm=args.use_llm,
            )

            total = summary["total_steps"]
            converted = len(summary["converted_steps"])
            failed = len(summary["failed_steps"])

            print(f"\n=== Conversion Summary ===")
            print(f"Total steps: {total}")
            print(f"Converted: {converted}")
            print(f"Failed: {failed}")

            if summary["warnings"]:
                print(f"\nWarnings: {len(summary['warnings'])}")

            if failed == 0:
                print("\n✓ Workflow conversion completed successfully!")
                sys.exit(0)
            else:
                print("\n⚠ Workflow conversion completed with errors")
                sys.exit(1)

        except Exception as e:
            print(f"\n✗ Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
