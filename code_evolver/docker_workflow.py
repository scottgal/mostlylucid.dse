#!/usr/bin/env python3
"""
Docker Workflow - CLI tool for containerized workflow execution

This tool makes it dead simple to run workflows in ephemeral Docker containers.

Commands:
    build   - Build a Docker image for a workflow
    run     - Run a workflow in Docker (builds if needed)
    clean   - Clean up Docker images

Features:
- Super compact images (~10-20MB) via Nuitka compilation
- Tree-shaking: only includes tools workflow actually uses
- Ollama access via host.docker.internal
- Ephemeral execution: spin up, run, tear down

Examples:
    # Build a workflow Docker image
    python docker_workflow.py build workflows/article_writer.json

    # Run a workflow in Docker
    python docker_workflow.py run workflows/article_writer.json '{"topic": "AI"}'

    # One-shot: build and run
    python docker_workflow.py run workflows/article_writer.json '{"topic": "AI"}' --build
"""
import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from docker_workflow_builder import DockerWorkflowBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def build_workflow(args):
    """Build Docker image for a workflow"""
    logger.info("=" * 60)
    logger.info("Docker Workflow Builder")
    logger.info("=" * 60)

    workflow_path = Path(args.workflow)

    if not workflow_path.exists():
        logger.error(f"❌ Workflow not found: {workflow_path}")
        sys.exit(1)

    # Load workflow to get ID
    with open(workflow_path) as f:
        workflow = json.load(f)

    workflow_id = workflow.get('workflow_id', 'workflow')

    # Determine image name
    if args.tag:
        image_name = args.tag
    else:
        image_name = f"workflow-{workflow_id}:latest"

    # Build
    builder = DockerWorkflowBuilder(Path(args.code_evolver_root))

    # Analyze
    logger.info(f"\n📊 Analyzing workflow: {workflow_id}")
    deps = builder.analyze_workflow(workflow_path)

    logger.info(f"\n🔍 Dependencies:")
    logger.info(f"  • LLM tools: {len(deps.llm_tools)}")
    logger.info(f"  • Executable tools: {len(deps.executable_tools)}")
    logger.info(f"  • Python packages: {len(deps.pip_packages)}")

    if deps.ollama_models:
        logger.info(f"  • Ollama models: {', '.join(deps.ollama_models)}")

    # Build image
    logger.info(f"\n🔨 Building Docker image: {image_name}")
    logger.info("This may take a few minutes on first build...\n")

    output_dir = Path(args.output)

    try:
        image_name = builder.build_docker_image(
            workflow_path,
            output_dir,
            deps,
            image_name
        )

        logger.info(f"\n✅ Success! Docker image ready: {image_name}")

        # Show usage
        logger.info(f"\n📦 Usage:")
        logger.info(f"  docker run --rm --add-host host.docker.internal:host-gateway \\")
        logger.info(f"    {image_name} '{{\"input\": \"value\"}}'")

        if deps.requires_ollama:
            logger.info(f"\n⚠️  Requires Ollama on localhost:11434")
            logger.info(f"   Models: {', '.join(deps.ollama_models)}")

        return image_name

    except Exception as e:
        logger.error(f"\n❌ Build failed: {e}")
        sys.exit(1)


def run_workflow(args):
    """Run workflow in Docker container"""
    workflow_path = Path(args.workflow)

    if not workflow_path.exists():
        logger.error(f"❌ Workflow not found: {workflow_path}")
        sys.exit(1)

    # Load workflow
    with open(workflow_path) as f:
        workflow = json.load(f)

    workflow_id = workflow.get('workflow_id', 'workflow')

    # Determine image name
    if args.tag:
        image_name = args.tag
    else:
        image_name = f"workflow-{workflow_id}:latest"

    # Check if image exists or needs building
    if args.build or not _image_exists(image_name):
        logger.info(f"🔨 Building image (not found or --build specified)...\n")
        build_workflow(args)

    # Parse inputs
    if args.input_file:
        with open(args.input_file) as f:
            inputs = json.load(f)
        inputs_json = json.dumps(inputs)
    else:
        inputs_json = args.inputs

    # Run in Docker
    logger.info(f"\n🚀 Running workflow: {workflow_id}")
    logger.info(f"📦 Image: {image_name}")
    logger.info(f"📥 Inputs: {inputs_json}\n")

    docker_cmd = [
        "docker", "run",
        "--rm",  # Remove container after execution
        "--add-host", "host.docker.internal:host-gateway",  # Ollama access
        image_name,
        inputs_json
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output
        try:
            output = json.loads(result.stdout)

            if output.get('success'):
                logger.info("✅ Workflow completed successfully!\n")
                logger.info("📤 Outputs:")
                print(json.dumps(output.get('outputs', {}), indent=2))
            else:
                logger.error(f"❌ Workflow failed: {output.get('error')}")
                sys.exit(1)

        except json.JSONDecodeError:
            # Raw output
            logger.info("📤 Output:")
            print(result.stdout)

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Docker execution failed")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        sys.exit(1)


def clean_workflow(args):
    """Clean up Docker images"""
    if args.all:
        # Remove all workflow images
        logger.info("🧹 Cleaning all workflow images...")

        # List workflow images
        list_cmd = ["docker", "images", "--filter", "label=workflow.id", "--format", "{{.Repository}}:{{.Tag}}"]

        result = subprocess.run(list_cmd, capture_output=True, text=True)
        images = result.stdout.strip().split('\n')

        if not images or images == ['']:
            logger.info("No workflow images found")
            return

        logger.info(f"Found {len(images)} workflow images:")
        for img in images:
            logger.info(f"  • {img}")

        if not args.yes:
            response = input("\nDelete all? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Cancelled")
                return

        # Delete each image
        for img in images:
            subprocess.run(["docker", "rmi", img], capture_output=True)

        logger.info("✅ Cleaned up workflow images")

    else:
        # Remove specific workflow
        workflow_path = Path(args.workflow)

        with open(workflow_path) as f:
            workflow = json.load(f)

        workflow_id = workflow.get('workflow_id', 'workflow')
        image_name = f"workflow-{workflow_id}:latest"

        logger.info(f"🧹 Removing image: {image_name}")

        subprocess.run(["docker", "rmi", image_name], capture_output=True)

        logger.info("✅ Cleaned up")


def _image_exists(image_name: str) -> bool:
    """Check if Docker image exists"""
    result = subprocess.run(
        ["docker", "images", "-q", image_name],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Docker Workflow - Containerized workflow execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build a workflow
  %(prog)s build workflows/article_writer.json

  # Run a workflow
  %(prog)s run workflows/article_writer.json '{"topic": "AI"}'

  # Build and run in one command
  %(prog)s run workflows/article_writer.json '{"topic": "AI"}' --build

  # Run with input file
  %(prog)s run workflows/article_writer.json --input-file inputs.json

  # Clean up all workflow images
  %(prog)s clean --all
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build Docker image for workflow')
    build_parser.add_argument('workflow', help='Path to workflow.json')
    build_parser.add_argument('--tag', '-t', help='Docker image tag')
    build_parser.add_argument('--output', '-o', default='./docker_build', help='Build output directory')
    build_parser.add_argument('--code-evolver-root', default='.', help='Code evolver root directory')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run workflow in Docker')
    run_parser.add_argument('workflow', help='Path to workflow.json')
    run_parser.add_argument('inputs', nargs='?', default='{}', help='Workflow inputs (JSON string)')
    run_parser.add_argument('--input-file', '-f', help='Read inputs from file')
    run_parser.add_argument('--tag', '-t', help='Docker image tag')
    run_parser.add_argument('--build', '-b', action='store_true', help='Force rebuild image')
    run_parser.add_argument('--output', '-o', default='./docker_build', help='Build output directory')
    run_parser.add_argument('--code-evolver-root', default='.', help='Code evolver root directory')

    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean up Docker images')
    clean_parser.add_argument('workflow', nargs='?', help='Path to workflow.json (optional)')
    clean_parser.add_argument('--all', '-a', action='store_true', help='Clean all workflow images')
    clean_parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'build':
        build_workflow(args)
    elif args.command == 'run':
        run_workflow(args)
    elif args.command == 'clean':
        clean_workflow(args)


if __name__ == "__main__":
    main()
