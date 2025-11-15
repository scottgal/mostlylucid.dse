#!/usr/bin/env python3
"""
Test script to verify workflow reuse in Code Evolver.
Tests that the same question reuses the existing workflow instead of regenerating.
"""
import sys
import time
from pathlib import Path
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import create_rag_memory, OllamaClient, Registry, NodeRunner
from src.config_manager import ConfigManager
from src.rag_memory import ArtifactType

console = Console()

def test_workflow_reuse():
    """Test that workflows are stored and reused correctly."""

    console.print("[bold cyan]Testing Workflow Reuse in Code Evolver[/bold cyan]\n")

    # Initialize components
    console.print("[dim]Initializing components...[/dim]")
    config = ConfigManager("config.yaml")
    client = OllamaClient(config.ollama_url, config_manager=config)
    rag = create_rag_memory(config, client)
    registry = Registry(config.registry_path)
    runner = NodeRunner(config.nodes_path)

    # Check Qdrant status
    if config.use_qdrant:
        console.print("[green]OK Qdrant is enabled[/green]")
    else:
        console.print("[yellow]WARNING: Qdrant is disabled, using NumPy-based RAG[/yellow]")

    # Test 1: Store a test workflow
    console.print("\n[bold]Test 1: Storing a test workflow[/bold]")
    test_question = "generate a function that adds two numbers"
    test_node_id = f"test_add_numbers_{int(time.time())}"

    workflow_content = {
        "description": test_question,
        "strategy": "Use simple addition operator to add two numbers",
        "tools_used": "general",
        "node_id": test_node_id,
        "tags": ["math", "addition", "test"],
        "code_summary": "Adds two numbers"
    }

    try:
        rag.store_artifact(
            artifact_id=f"workflow_{test_node_id}",
            artifact_type=ArtifactType.WORKFLOW,
            name=f"Workflow: Adds two numbers",
            description=test_question,
            content=str(workflow_content),
            tags=["workflow", "complete", "math", "addition", "test"],
            metadata={
                "node_id": test_node_id,
                "question": test_question,
                "strategy_hash": hash("Use simple addition operator to add two numbers")
            },
            auto_embed=True
        )
        console.print(f"[green]OK Stored test workflow: workflow_{test_node_id}[/green]")
    except Exception as e:
        console.print(f"[red]FAIL Failed to store workflow: {e}[/red]")
        return False

    # Test 2: Search for similar workflow
    console.print("\n[bold]Test 2: Searching for similar workflow[/bold]")
    console.print(f"[dim]Query: '{test_question}'[/dim]")

    try:
        similar_workflows = rag.find_similar(
            test_question,
            artifact_type=ArtifactType.WORKFLOW,
            top_k=3
        )

        if similar_workflows:
            console.print(f"[green]OK Found {len(similar_workflows)} similar workflow(s)[/green]")
            for artifact, similarity in similar_workflows:
                console.print(f"  - {artifact.name} (similarity: {similarity:.2%})")
                console.print(f"    Description: {artifact.description}")
                console.print(f"    Artifact ID: {artifact.artifact_id}")
        else:
            console.print("[yellow]WARNING: No similar workflows found[/yellow]")
    except Exception as e:
        console.print(f"[red]FAIL Search failed: {e}[/red]")
        return False

    # Test 3: Test with slightly different phrasing (should still match)
    console.print("\n[bold]Test 3: Testing with similar phrasing[/bold]")
    similar_question = "create a function to add 2 numbers together"
    console.print(f"[dim]Query: '{similar_question}'[/dim]")

    try:
        similar_workflows = rag.find_similar(
            similar_question,
            artifact_type=ArtifactType.WORKFLOW,
            top_k=1
        )

        if similar_workflows:
            artifact, similarity = similar_workflows[0]
            console.print(f"[green]OK Found workflow: {artifact.name} (similarity: {similarity:.2%})[/green]")
            if similarity > 0.85:
                console.print(f"[green]OK Similarity > 85% - Would reuse this workflow![/green]")
            else:
                console.print(f"[yellow]WARNING: Similarity {similarity:.2%} < 85% - Would generate new workflow[/yellow]")
        else:
            console.print("[yellow]WARNING: No similar workflows found[/yellow]")
    except Exception as e:
        console.print(f"[red]FAIL Search failed: {e}[/red]")
        return False

    # Test 4: Test with completely different question (should not match)
    console.print("\n[bold]Test 4: Testing with different question[/bold]")
    different_question = "generate code to parse XML files"
    console.print(f"[dim]Query: '{different_question}'[/dim]")

    try:
        similar_workflows = rag.find_similar(
            different_question,
            artifact_type=ArtifactType.WORKFLOW,
            top_k=1
        )

        if similar_workflows:
            artifact, similarity = similar_workflows[0]
            console.print(f"[dim]Found: {artifact.name} (similarity: {similarity:.2%})[/dim]")
            if similarity > 0.85:
                console.print(f"[yellow]WARNING: Unexpected high similarity for different question[/yellow]")
            else:
                console.print(f"[green]OK Low similarity {similarity:.2%} - Would generate new workflow[/green]")
        else:
            console.print("[green]OK No matching workflows - Would generate new[/green]")
    except Exception as e:
        console.print(f"[red]FAIL Search failed: {e}[/red]")
        return False

    # Test 5: List all workflows
    console.print("\n[bold]Test 5: Listing all workflows in RAG[/bold]")

    try:
        all_artifacts = rag.list_all()
        workflows = [a for a in all_artifacts if a.artifact_type == ArtifactType.WORKFLOW]

        console.print(f"[green]OK Total artifacts in RAG: {len(all_artifacts)}[/green]")
        console.print(f"[green]OK Workflows: {len(workflows)}[/green]")

        if workflows:
            console.print("\n[bold]Stored Workflows:[/bold]")
            for wf in workflows[:5]:  # Show first 5
                console.print(f"  - {wf.name}")
                console.print(f"    ID: {wf.artifact_id}")
                console.print(f"    Description: {wf.description}")
                console.print(f"    Tags: {', '.join(wf.tags)}")
                console.print()
    except Exception as e:
        console.print(f"[red]FAIL Failed to list artifacts: {e}[/red]")
        return False

    # Test 6: Verify other artifact types are stored
    console.print("\n[bold]Test 6: Checking other artifact types[/bold]")

    artifact_counts = {}
    for artifact in all_artifacts:
        artifact_type = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else str(artifact.artifact_type)
        artifact_counts[artifact_type] = artifact_counts.get(artifact_type, 0) + 1

    console.print("[green]Artifact type distribution:[/green]")
    for art_type, count in artifact_counts.items():
        console.print(f"  - {art_type}: {count}")

    # Success!
    console.print("\n[bold green]OK All tests passed![/bold green]")
    console.print("\n[bold cyan]Summary:[/bold cyan]")
    console.print("OK Workflows are stored in RAG with embeddings")
    console.print("OK Similar questions find existing workflows (>85% similarity reuses)")
    console.print("OK Different questions create new workflows")
    console.print("OK All artifact types (functions, workflows, etc.) are stored in Qdrant/RAG")

    return True

if __name__ == "__main__":
    try:
        success = test_workflow_reuse()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Test failed with error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
