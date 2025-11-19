#!/usr/bin/env python3
"""
Missing Package Auto-Installer
Automatically detects and installs missing Python packages.
"""
import json
import sys
import re
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common module name -> package name mappings
PACKAGE_MAPPINGS = {
    "bs4": "beautifulsoup4",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "PyYAML",
    "dotenv": "python-dotenv",
    "requests": "requests",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "sqlalchemy": "SQLAlchemy",
    "psycopg2": "psycopg2-binary",
    "MySQLdb": "mysqlclient",
    "lxml": "lxml",
    "cryptography": "cryptography",
    "jwt": "PyJWT",
    "dateutil": "python-dateutil",
    "magic": "python-magic",
    "markdown": "Markdown",
}


def extract_module_name(error_message: str) -> str:
    """
    Extract module name from ModuleNotFoundError message.

    Args:
        error_message: Error message string

    Returns:
        Module name or empty string
    """
    # Pattern: ModuleNotFoundError: No module named 'module_name'
    pattern = r"No module named ['\"]([^'\"]+)['\"]"
    match = re.search(pattern, error_message)

    if match:
        return match.group(1)

    return ""


def get_package_name(module_name: str) -> str:
    """
    Get the pip package name for a module.

    Args:
        module_name: Python module name

    Returns:
        Package name for pip install
    """
    # Check if there's a known mapping
    if module_name in PACKAGE_MAPPINGS:
        return PACKAGE_MAPPINGS[module_name]

    # For submodules (e.g., 'requests.auth'), use base module
    base_module = module_name.split('.')[0]
    if base_module in PACKAGE_MAPPINGS:
        return PACKAGE_MAPPINGS[base_module]

    # Default: assume package name is same as module name
    return module_name


def install_package(package_name: str) -> dict:
    """
    Install a package using pip.

    Args:
        package_name: Name of package to install

    Returns:
        Dict with success status and message
    """
    pip_command = f"pip install {package_name}"

    try:
        logger.info(f"Installing package: {package_name}")

        result = subprocess.run(
            ["pip", "install", package_name],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"Successfully installed {package_name}")
            return {
                "success": True,
                "package_installed": package_name,
                "message": f"Successfully installed {package_name}",
                "pip_command": pip_command,
                "output": result.stdout
            }
        else:
            logger.error(f"Failed to install {package_name}: {result.stderr}")
            return {
                "success": False,
                "package_installed": package_name,
                "message": f"Failed to install {package_name}",
                "pip_command": pip_command,
                "error": result.stderr
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "package_installed": package_name,
            "message": f"Installation timeout for {package_name}",
            "pip_command": pip_command,
            "error": "Installation took longer than 2 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "package_installed": package_name,
            "message": f"Installation error: {str(e)}",
            "pip_command": pip_command,
            "error": str(e)
        }


def main():
    """Main entry point."""
    try:
        # Read input from stdin
        input_data = json.loads(sys.stdin.read())

        error_message = input_data.get("error_message", "")
        explicit_module = input_data.get("module_name")

        # Extract module name
        if explicit_module:
            module_name = explicit_module
        else:
            module_name = extract_module_name(error_message)

        if not module_name:
            print(json.dumps({
                "success": False,
                "message": "Could not extract module name from error message",
                "error_message": error_message
            }))
            return

        # Get package name
        package_name = get_package_name(module_name)

        logger.info(f"Module '{module_name}' -> Package '{package_name}'")

        # Install package
        result = install_package(package_name)

        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "message": f"Invalid JSON input: {str(e)}"
        }))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error in missing_package_installer: {e}", exc_info=True)
        print(json.dumps({
            "success": False,
            "message": f"Error: {str(e)}"
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
