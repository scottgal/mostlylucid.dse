#!/usr/bin/env python3
"""
Package Recovery Tool
Automatically detects missing packages from error messages and installs them
"""
import json
import sys
import re
import subprocess
from typing import Dict, Any, List, Tuple


# Common error patterns for missing packages
ERROR_PATTERNS = {
    'python_import': [
        r"ModuleNotFoundError: No module named '([^']+)'",
        r"ImportError: No module named '([^']+)'",
        r"ImportError: cannot import name '[^']+' from '([^']+)'",
    ],
    'system_command': [
        r"([a-zA-Z0-9_-]+): command not found",
        r"bash: ([a-zA-Z0-9_-]+): command not found",
        r"sh: \d+: ([a-zA-Z0-9_-]+): not found",
    ]
}

# Package name mappings (import name -> pip package name)
PACKAGE_MAPPINGS = {
    'yaml': 'pyyaml',
    'PIL': 'pillow',
    'cv2': 'opencv-python',
    'sklearn': 'scikit-learn',
    'flask_cors': 'flask-cors',
    'dotenv': 'python-dotenv',
    'bs4': 'beautifulsoup4',
    'dateutil': 'python-dateutil',
}

# System command to package mappings (Debian/Ubuntu)
SYSTEM_PACKAGE_MAPPINGS = {
    'curl': 'curl',
    'wget': 'wget',
    'git': 'git',
    'docker': 'docker.io',
    'docker-compose': 'docker-compose',
}


def detect_missing_packages(error_output: str) -> Tuple[List[str], List[str]]:
    """
    Detect missing Python packages and system commands from error output

    Args:
        error_output: Error message or log output

    Returns:
        Tuple of (python_packages, system_commands)
    """
    python_packages = set()
    system_commands = set()

    # Detect Python import errors
    for pattern in ERROR_PATTERNS['python_import']:
        matches = re.findall(pattern, error_output, re.MULTILINE)
        for match in matches:
            # Handle nested imports (e.g., 'package.submodule')
            package_name = match.split('.')[0]
            # Map to correct pip package name if needed
            pip_package = PACKAGE_MAPPINGS.get(package_name, package_name)
            python_packages.add(pip_package)

    # Detect system command errors
    for pattern in ERROR_PATTERNS['system_command']:
        matches = re.findall(pattern, error_output, re.MULTILINE)
        for match in matches:
            system_commands.add(match)

    return list(python_packages), list(system_commands)


def install_python_packages(packages: List[str]) -> Dict[str, Any]:
    """
    Install Python packages using pip

    Args:
        packages: List of package names to install

    Returns:
        Dictionary with installation results
    """
    if not packages:
        return {'success': True, 'installed': [], 'message': 'No packages to install'}

    results = {
        'success': True,
        'installed': [],
        'failed': [],
        'output': []
    }

    for package in packages:
        try:
            print(f"Installing Python package: {package}", file=sys.stderr)
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                results['installed'].append(package)
                results['output'].append(f"✓ Installed {package}")
            else:
                results['failed'].append(package)
                results['success'] = False
                results['output'].append(f"✗ Failed to install {package}: {result.stderr}")

        except subprocess.TimeoutExpired:
            results['failed'].append(package)
            results['success'] = False
            results['output'].append(f"✗ Timeout installing {package}")
        except Exception as e:
            results['failed'].append(package)
            results['success'] = False
            results['output'].append(f"✗ Error installing {package}: {e}")

    return results


def install_system_packages(commands: List[str]) -> Dict[str, Any]:
    """
    Install system packages using apt (Debian/Ubuntu)

    Args:
        commands: List of command names that are missing

    Returns:
        Dictionary with installation results
    """
    if not commands:
        return {'success': True, 'installed': [], 'message': 'No system packages to install'}

    # Map commands to package names
    packages = []
    for cmd in commands:
        package = SYSTEM_PACKAGE_MAPPINGS.get(cmd, cmd)
        packages.append(package)

    results = {
        'success': True,
        'installed': [],
        'failed': [],
        'output': [],
        'note': 'System package installation requires sudo privileges'
    }

    # Check if we have apt (Debian/Ubuntu)
    try:
        subprocess.run(['which', 'apt'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        results['success'] = False
        results['output'].append("✗ apt not found - only Debian/Ubuntu supported for automatic system package installation")
        return results

    for package in packages:
        try:
            print(f"Installing system package: {package} (requires sudo)", file=sys.stderr)

            # Try to install without sudo first (in case running as root)
            try:
                result = subprocess.run(
                    ['apt', 'install', '-y', package],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            except PermissionError:
                # Fall back to sudo
                result = subprocess.run(
                    ['sudo', 'apt', 'install', '-y', package],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

            if result.returncode == 0:
                results['installed'].append(package)
                results['output'].append(f"✓ Installed {package}")
            else:
                results['failed'].append(package)
                results['output'].append(f"✗ Failed to install {package}")

        except subprocess.TimeoutExpired:
            results['failed'].append(package)
            results['output'].append(f"✗ Timeout installing {package}")
        except Exception as e:
            results['failed'].append(package)
            results['output'].append(f"✗ Error installing {package}: {e}")

    results['success'] = len(results['failed']) == 0

    return results


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': 'Missing error output argument'
        }))
        sys.exit(1)

    try:
        # Parse input
        input_data = json.loads(sys.argv[1])
        error_output = input_data.get('error_output', '')
        auto_install = input_data.get('auto_install', True)
        install_system = input_data.get('install_system', False)

        # Detect missing packages
        python_packages, system_commands = detect_missing_packages(error_output)

        result = {
            'success': False,
            'detected': {
                'python_packages': python_packages,
                'system_commands': system_commands
            },
            'installation_results': {}
        }

        # Install if requested
        if auto_install and python_packages:
            result['installation_results']['python'] = install_python_packages(python_packages)

        if install_system and system_commands:
            result['installation_results']['system'] = install_system_packages(system_commands)

        # Overall success
        if auto_install:
            result['success'] = all(
                r.get('success', True)
                for r in result['installation_results'].values()
            )
        else:
            result['success'] = True
            result['message'] = 'Detection complete. Set auto_install=true to install packages.'

        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({
            'error': f'Invalid JSON input: {e}'
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'error': f'Error in package recovery: {e}'
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
