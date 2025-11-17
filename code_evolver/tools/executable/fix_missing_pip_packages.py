#!/usr/bin/env python3
"""
Fix Missing Pip Packages Tool

Detects ModuleNotFoundError and automatically installs missing packages.
Handles common module → package name mappings (e.g., bs4 → beautifulsoup4).
"""
import json
import sys
import subprocess
import re
from typing import Dict, Any, Optional, List


# Common module → pip package mappings
MODULE_TO_PACKAGE = {
    'bs4': 'beautifulsoup4',
    'BeautifulSoup': 'beautifulsoup4',
    'cv2': 'opencv-python',
    'PIL': 'Pillow',
    'sklearn': 'scikit-learn',
    'yaml': 'pyyaml',
    'dotenv': 'python-dotenv',
    'dateutil': 'python-dateutil',
    'OpenSSL': 'pyOpenSSL',
    'psycopg2': 'psycopg2-binary',
    'MySQLdb': 'mysqlclient',
    'magic': 'python-magic',
    'git': 'GitPython',
    'wx': 'wxPython',
    'nacl': 'PyNaCl',
    'Crypto': 'pycryptodome',
    'lxml': 'lxml',
    'requests': 'requests',
    'numpy': 'numpy',
    'pandas': 'pandas',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'scipy': 'scipy',
    'torch': 'torch',
    'tensorflow': 'tensorflow',
    'keras': 'keras',
}


def detect_missing_modules(error_output: str, source_code: str = "") -> List[str]:
    """
    Detect missing modules from error output and source code.

    Args:
        error_output: Error message (stderr)
        source_code: Source code to scan for imports

    Returns:
        List of missing module names
    """
    missing_modules = []

    # Pattern 1: ModuleNotFoundError
    pattern1 = r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern1, error_output)
    missing_modules.extend(matches)

    # Pattern 2: ImportError
    pattern2 = r"ImportError: No module named ['\"]?([^'\"]+)['\"]?"
    matches = re.findall(pattern2, error_output)
    missing_modules.extend(matches)

    # Pattern 3: cannot import name
    pattern3 = r"cannot import name ['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern3, error_output)
    # These might be submodules, extract base module
    for match in matches:
        if '.' in match:
            missing_modules.append(match.split('.')[0])

    # If we have source code, extract imports to verify
    if source_code:
        import_pattern = r"(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        imports = re.findall(import_pattern, source_code)

        # Cross-reference with errors to find actual missing ones
        for imp in imports:
            # Check if this import appears in error
            if imp in error_output:
                if imp not in missing_modules:
                    missing_modules.append(imp)

    # Remove duplicates while preserving order
    seen = set()
    unique_modules = []
    for module in missing_modules:
        if module not in seen:
            seen.add(module)
            unique_modules.append(module)

    return unique_modules


def get_package_name(module_name: str) -> str:
    """
    Get pip package name for a module.

    Args:
        module_name: Python module name

    Returns:
        Pip package name
    """
    # Check if we have a known mapping
    if module_name in MODULE_TO_PACKAGE:
        return MODULE_TO_PACKAGE[module_name]

    # For most packages, module name == package name
    return module_name


def install_package(package_name: str, quiet: bool = True) -> Dict[str, Any]:
    """
    Install a pip package.

    Args:
        package_name: Name of package to install
        quiet: Suppress output

    Returns:
        Result dict with success, stdout, stderr
    """
    try:
        cmd = [sys.executable, '-m', 'pip', 'install', package_name]
        if quiet:
            cmd.append('--quiet')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Installation timed out after 120 seconds',
            'exit_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'exit_code': -1
        }


def verify_module_available(module_name: str) -> bool:
    """
    Verify that a module can be imported.

    Args:
        module_name: Module to test

    Returns:
        True if module can be imported
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def fix_missing_packages(
    error_output: str,
    source_code: str = "",
    auto_install: bool = True,
    verify_install: bool = True
) -> Dict[str, Any]:
    """
    Detect and fix missing pip packages.

    Args:
        error_output: Error message from failed execution
        source_code: Source code that failed
        auto_install: Automatically install packages
        verify_install: Verify packages after installation

    Returns:
        Result with installed packages and status
    """
    # Detect missing modules
    missing_modules = detect_missing_modules(error_output, source_code)

    if not missing_modules:
        return {
            'success': True,
            'fixed': False,
            'message': 'No missing packages detected',
            'missing_modules': [],
            'installed_packages': []
        }

    installed = []
    failed = []

    for module_name in missing_modules:
        package_name = get_package_name(module_name)

        if not auto_install:
            # Just report what would be installed
            installed.append({
                'module': module_name,
                'package': package_name,
                'installed': False,
                'message': 'Auto-install disabled'
            })
            continue

        # Try to install
        result = install_package(package_name)

        if result['success']:
            # Verify if requested
            verified = True
            if verify_install:
                verified = verify_module_available(module_name)

            installed.append({
                'module': module_name,
                'package': package_name,
                'installed': True,
                'verified': verified,
                'message': 'Installed successfully' if verified else 'Installed but verification failed'
            })
        else:
            failed.append({
                'module': module_name,
                'package': package_name,
                'installed': False,
                'error': result['stderr']
            })

    # Determine overall success
    all_success = len(failed) == 0 and len(installed) > 0

    return {
        'success': all_success,
        'fixed': all_success,
        'message': f"Installed {len([p for p in installed if p.get('installed')])} packages, {len(failed)} failed",
        'missing_modules': missing_modules,
        'installed_packages': installed,
        'failed_packages': failed,
        'fix_type': 'pip_install',
        'can_retry': True  # Code should be retested after package install
    }


def main():
    """Main entry point for tool execution."""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()

        try:
            input_data = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(json.dumps({
                'success': False,
                'error': f'Invalid JSON input: {str(e)}'
            }))
            sys.exit(1)

        # Extract parameters
        error_output = input_data.get('error_output', '')
        source_code = input_data.get('source_code', '')
        auto_install = input_data.get('auto_install', True)
        verify_install = input_data.get('verify_install', True)

        if not error_output:
            print(json.dumps({
                'success': False,
                'error': 'Missing required parameter: error_output'
            }))
            sys.exit(1)

        # Run the fix
        result = fix_missing_packages(
            error_output=error_output,
            source_code=source_code,
            auto_install=auto_install,
            verify_install=verify_install
        )

        # Output result
        print(json.dumps(result, indent=2))

        # Exit with success/failure code
        sys.exit(0 if result['success'] else 1)

    except Exception as e:
        import traceback
        print(json.dumps({
            'success': False,
            'error': f'Fatal error: {str(e)}',
            'traceback': traceback.format_exc()
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
