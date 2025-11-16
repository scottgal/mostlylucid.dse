#!/usr/bin/env python3
"""
Generate Workflow From Specification File

Quick script to generate workflows from large specification files.

Usage:
    python generate_from_spec.py spec.txt
    python generate_from_spec.py --file spec.md --max-length 15000
"""

import sys
import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Generate workflow from specification file"
    )
    parser.add_argument(
        'file_path',
        nargs='?',
        help='Path to specification file'
    )
    parser.add_argument(
        '--file', '-f',
        dest='file_path_alt',
        help='Path to specification file (alternative)'
    )
    parser.add_argument(
        '--max-length', '-m',
        type=int,
        default=10000,
        help='Maximum length for overseer summary (default: 10000)'
    )
    parser.add_argument(
        '--no-summarize',
        action='store_true',
        help='Use full spec without summarizing'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output node ID (default: auto-generated)'
    )

    args = parser.parse_args()

    # Get file path from either positional or named argument
    file_path = args.file_path or args.file_path_alt

    if not file_path:
        parser.print_help()
        print("\nError: No specification file provided")
        sys.exit(1)

    # Check file exists
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Reading specification from: {path.absolute()}")
    print(f"File size: {path.stat().st_size:,} bytes")
    print()

    # Import runtime
    sys.path.insert(0, '.')
    from node_runtime import call_tool

    # Extract spec from file
    print("Extracting and processing specification...")
    spec_result = call_tool("extract_spec_from_file", json.dumps({
        "file_path": str(path.absolute()),
        "summarize": not args.no_summarize,
        "max_length": args.max_length
    }), disable_tracking=True)

    spec_data = json.loads(spec_result)

    if not spec_data["success"]:
        print(f"Error: {spec_data['error']}")
        sys.exit(1)

    print(f"✓ Extracted {spec_data['file_size']:,} characters ({spec_data['word_count']:,} words)")

    if spec_data.get("overseer_spec"):
        overseer_len = len(spec_data["overseer_spec"])
        print(f"✓ Created overseer summary: {overseer_len:,} characters")

        if overseer_len < spec_data["file_size"]:
            reduction = (1 - overseer_len / spec_data["file_size"]) * 100
            print(f"  ({reduction:.1f}% reduction for faster processing)")
    print()

    # Show extracted sections
    if spec_data.get("sections"):
        print("Detected sections:")
        for section_name in spec_data["sections"].keys():
            print(f"  - {section_name}")
        print()

    # Get user input to confirm
    print("Specification loaded successfully!")
    print()
    print("=" * 80)
    print("OVERSEER SPEC PREVIEW")
    print("=" * 80)
    print(spec_data["overseer_spec"][:500] + "..." if len(spec_data["overseer_spec"]) > 500 else spec_data["overseer_spec"])
    print("=" * 80)
    print()

    response = input("Generate workflow from this specification? [Y/n]: ")
    if response.lower() in ['n', 'no']:
        print("Cancelled.")
        sys.exit(0)

    # Start workflow generation using chat_cli
    print("\nStarting workflow generation...")
    print("(This will use the chat_cli.py interface)")
    print()

    # Import chat CLI
    from chat_cli import ChatCLI

    # Initialize CLI
    cli = ChatCLI()

    # Use the overseer spec as the request
    user_request = spec_data["overseer_spec"]

    # Generate workflow
    print("Sending to overseer for planning...")
    cli.handle_generate(user_request)

    print("\n✓ Workflow generation complete!")
    print()

    # Show full spec availability
    if spec_data["file_size"] > len(spec_data["overseer_spec"]):
        print("Note: Full specification is available in the tool output if needed.")


if __name__ == "__main__":
    main()
