"""
Script to update tags index with HTTP Content Fetcher tool tags.
"""

import json
import sys
from pathlib import Path

# Paths
TAGS_INDEX = Path(__file__).parent.parent / "rag_memory" / "tags_index.json"


def update_tags_index():
    """Update tags index with HTTP Content Fetcher tags."""

    # Load existing tags index
    with open(TAGS_INDEX, 'r', encoding='utf-8') as f:
        tags_index = json.load(f)

    # Tags for HTTP Content Fetcher
    http_fetcher_tags = [
        "http",
        "fetch",
        "content-fetching",
        "web",
        "api",
        "rest",
        "api-connector",
        "http-client",
        "download",
        "upload",
        "json",
        "xml",
        "form-data",
        "authentication",
        "bearer",
        "api-key",
        "workflow-integration"
    ]

    tool_id = "tool_http_content_fetcher"

    # Add tool to each tag
    for tag in http_fetcher_tags:
        if tag not in tags_index:
            tags_index[tag] = []

        if tool_id not in tags_index[tag]:
            tags_index[tag].append(tool_id)

    # Save back to file
    with open(TAGS_INDEX, 'w', encoding='utf-8') as f:
        json.dump(tags_index, f, indent=2)

    print(f"✓ Successfully updated tags index in {TAGS_INDEX}")
    print(f"  Added tool '{tool_id}' to {len(http_fetcher_tags)} tags:")
    for tag in http_fetcher_tags[:10]:
        count = len(tags_index[tag])
        print(f"    - {tag}: {count} items")
    if len(http_fetcher_tags) > 10:
        print(f"    ... and {len(http_fetcher_tags) - 10} more tags")


if __name__ == '__main__':
    try:
        update_tags_index()
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error updating tags index: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
