"""
Tool for installing Python packages via pip with validation.
Reads package name from stdin as JSON, validates against trusted list,
installs it, and returns status.
"""
import json
import sys
import subprocess
import re
from pathlib import Path

# Add src to path to import package_validator
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from package_validator import validate_package
    VALIDATION_ENABLED = True
except ImportError:
    # Fallback if validator not available
    VALIDATION_ENABLED = False
    print("Warning: Package validation not available", file=sys.stderr)


def parse_package_spec(package: str):
    """
    Parse package specification into name and version.

    Examples:
        "requests" -> ("requests", None)
        "requests>=2.0.0" -> ("requests", ">=2.0.0")
        "pandas==1.5.0" -> ("pandas", "==1.5.0")

    Returns:
        Tuple of (package_name, version_spec)
    """
    # Match package name and optional version specifier
    match = re.match(r'^([a-zA-Z0-9_-]+)(.*?)$', package)
    if not match:
        return package, None

    name = match.group(1)
    version_spec = match.group(2).strip() if match.group(2) else None

    return name, version_spec


def install_package(package: str, context: str = "unknown"):
    """
    Install a Python package via pip with validation.

    Args:
        package: Package specification (e.g., "requests>=2.0.0")
        context: Context of installation (workflow_id, tool_id, etc.)

    Returns:
        Dict with installation status and details
    """
    try:
        # Parse package specification
        package_name, version_spec = parse_package_spec(package)

        # Validate package if validation is enabled
        if VALIDATION_ENABLED:
            is_valid, validation_msg = validate_package(package_name, version_spec, context)

            if not is_valid:
                return {
                    'status': 'rejected',
                    'package': package,
                    'package_name': package_name,
                    'version': version_spec,
                    'error': f"Package validation failed: {validation_msg}"
                }

        # Install package using pip
        # Use --quiet to reduce output, --no-input to avoid prompts
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--quiet', '--no-input', package],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout for installation
        )

        if result.returncode == 0:
            return {
                'status': 'installed',
                'package': package,
                'package_name': package_name,
                'version': version_spec,
                'validated': VALIDATION_ENABLED
            }
        else:
            error_output = result.stderr.strip() or result.stdout.strip()
            return {
                'status': 'failed',
                'package': package,
                'package_name': package_name,
                'version': version_spec,
                'error': error_output
            }

    except subprocess.TimeoutExpired:
        return {
            'status': 'failed',
            'package': package,
            'error': 'Installation timeout after 120 seconds'
        }
    except Exception as e:
        return {
            'status': 'failed',
            'package': package,
            'error': str(e)
        }


def install_batch(packages: list, context: str = "unknown"):
    """
    Install multiple packages in batch.

    Args:
        packages: List of package specifications
        context: Context of installation

    Returns:
        Dict with batch installation results
    """
    if VALIDATION_ENABLED:
        from package_validator import validate_packages

        # Convert to validator format
        package_specs = []
        for pkg in packages:
            name, version = parse_package_spec(pkg)
            package_specs.append({'name': name, 'version': version})

        # Validate all packages first
        all_valid, errors = validate_packages(package_specs, context)

        if not all_valid:
            return {
                'status': 'rejected',
                'packages': packages,
                'errors': errors
            }

    # Install each package
    results = []
    for pkg in packages:
        result = install_package(pkg, context)
        results.append(result)

    # Check if all succeeded
    all_success = all(r['status'] == 'installed' for r in results)

    return {
        'status': 'completed' if all_success else 'partial',
        'results': results,
        'total': len(packages),
        'installed': sum(1 for r in results if r['status'] == 'installed'),
        'failed': sum(1 for r in results if r['status'] == 'failed'),
        'rejected': sum(1 for r in results if r['status'] == 'rejected')
    }


def main():
    """Main entry point for pip install tool."""
    try:
        # Read input
        input_data = json.load(sys.stdin)

        # Support both single package and batch installation
        if 'package' in input_data:
            # Single package installation
            package = input_data.get('package', '')
            context = input_data.get('context', 'cli')

            if not package:
                print(json.dumps({
                    'status': 'failed',
                    'error': 'No package specified'
                }))
                return

            result = install_package(package, context)
            print(json.dumps(result, indent=2))

        elif 'packages' in input_data:
            # Batch installation
            packages = input_data.get('packages', [])
            context = input_data.get('context', 'cli')

            if not packages:
                print(json.dumps({
                    'status': 'failed',
                    'error': 'No packages specified'
                }))
                return

            result = install_batch(packages, context)
            print(json.dumps(result, indent=2))

        else:
            print(json.dumps({
                'status': 'failed',
                'error': 'Must specify either "package" or "packages" in input'
            }))

    except Exception as e:
        print(json.dumps({
            'status': 'failed',
            'error': str(e)
        }))


if __name__ == '__main__':
    main()
