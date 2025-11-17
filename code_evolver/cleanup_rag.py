#!/usr/bin/env python3
"""
Cleanup utility for mostlylucid DiSE RAG memory.
Removes artifacts for deleted nodes to prevent RAG bloat during testing.
"""
import sys
from pathlib import Path
from src import create_rag_memory, Registry, OllamaClient
from src.config_manager import ConfigManager

def cleanup_orphaned_artifacts(dry_run=True):
    """
    Remove RAG artifacts for nodes that no longer exist.

    Args:
        dry_run: If True, only report what would be deleted
    """
    config = ConfigManager()
    client = OllamaClient(config_manager=config)
    rag = create_rag_memory(config_manager=config, ollama_client=client)
    registry = Registry()
    
    # Get all nodes that currently exist
    existing_nodes = set()
    nodes_dir = Path(config.get("nodes.path", "./nodes"))
    
    if nodes_dir.exists():
        for node_dir in nodes_dir.iterdir():
            if node_dir.is_dir():
                existing_nodes.add(node_dir.name)
    
    print(f"Found {len(existing_nodes)} existing nodes")
    
    # Get all artifacts from RAG
    all_artifacts = rag.list_all()
    
    print(f"Found {len(all_artifacts)} artifacts in RAG")
    
    # Find orphaned artifacts (artifacts for deleted nodes)
    orphaned = []
    node_related_prefixes = ['func_', 'workflow_', 'plan_', 'tool_', 'node_']
    
    for artifact in all_artifacts:
        artifact_id = artifact.artifact_id
        
        # Check if this artifact is related to a node
        is_node_artifact = False
        node_id = None
        
        for prefix in node_related_prefixes:
            if artifact_id.startswith(prefix):
                is_node_artifact = True
                # Extract node ID (everything after prefix)
                node_id = artifact_id[len(prefix):]
                break
        
        # If it's a node artifact and the node doesn't exist, mark as orphaned
        if is_node_artifact and node_id and node_id not in existing_nodes:
            orphaned.append(artifact)
    
    print(f"\nFound {len(orphaned)} orphaned artifacts")
    
    if orphaned:
        print("\nOrphaned artifacts:")
        for artifact in orphaned[:10]:  # Show first 10
            print(f"  - {artifact.artifact_id} ({artifact.artifact_type.value})")
        if len(orphaned) > 10:
            print(f"  ... and {len(orphaned) - 10} more")
    
    if not dry_run and orphaned:
        print(f"\nDeleting {len(orphaned)} orphaned artifacts...")
        deleted_count = 0
        for artifact in orphaned:
            try:
                if rag.delete_artifact(artifact.artifact_id):
                    deleted_count += 1
            except Exception as e:
                print(f"  Error deleting {artifact.artifact_id}: {e}")
        
        print(f"Successfully deleted {deleted_count} artifacts")
    elif dry_run and orphaned:
        print("\n[DRY RUN] Would delete these artifacts. Run with --delete to actually remove them.")
    else:
        print("\nNo orphaned artifacts found. RAG is clean!")
    
    return len(orphaned)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup orphaned RAG artifacts")
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Actually delete orphaned artifacts (default is dry-run)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show RAG statistics'
    )
    
    args = parser.parse_args()
    
    if args.stats:
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = create_rag_memory(config_manager=config, ollama_client=client)
        
        print("="*70)
        print("RAG MEMORY STATISTICS")
        print("="*70)
        
        all_artifacts = rag.list_all()
        print(f"\nTotal artifacts: {len(all_artifacts)}")
        
        # Count by type
        type_counts = {}
        for artifact in all_artifacts:
            artifact_type = artifact.artifact_type.value
            type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
        
        print("\nBy type:")
        for artifact_type, count in sorted(type_counts.items()):
            print(f"  {artifact_type:20s}: {count:6d}")
        
        print("\n" + "="*70)
    
    # Run cleanup
    orphaned_count = cleanup_orphaned_artifacts(dry_run=not args.delete)

    # After cleanup, re-index tools from config so they can be found
    if args.delete and orphaned_count > 0:
        print("\nRe-indexing tools from config...")
        config = ConfigManager()
        client = OllamaClient(config_manager=config)
        rag = create_rag_memory(config_manager=config, ollama_client=client)

        # Tools are automatically indexed when ToolsManager is created
        from src.tools_manager import ToolsManager
        tools_manager = ToolsManager(
            config_manager=config,
            ollama_client=client,
            rag_memory=rag
        )

        print(f"OK Re-indexed {len(tools_manager.tools)} tools in RAG for semantic search")

    return 0 if orphaned_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
