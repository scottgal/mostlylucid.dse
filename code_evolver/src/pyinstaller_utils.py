"""
PyInstaller utilities for handling bundled resources.
Helps locate bundled files when running as compiled executable.
"""
import sys
from pathlib import Path
from typing import Union


def get_resource_path(relative_path: Union[str, Path]) -> Path:
    """
    Get absolute path to resource, works for dev and PyInstaller.

    When running as a PyInstaller executable, resources are extracted to
    sys._MEIPASS temporary directory. This function transparently handles
    both development (script) and production (executable) modes.

    Args:
        relative_path: Path relative to application root

    Returns:
        Absolute path to resource

    Example:
        >>> config_path = get_resource_path("config.yaml")
        >>> prompts_path = get_resource_path("prompts")
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use extracted temp directory
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script - use current working directory
        base_path = Path.cwd()

    return base_path / relative_path


def is_frozen() -> bool:
    """
    Check if running as PyInstaller executable.

    Returns:
        True if running as compiled executable, False if running as script
    """
    return getattr(sys, 'frozen', False)


def get_user_data_dir(app_name: str = "mostlylucid-dse") -> Path:
    """
    Get user-writable data directory for storing runtime files.

    When running as executable, bundled resources are read-only.
    This function returns a user-writable directory for:
    - Generated nodes
    - User-created tools
    - Logs
    - Cache

    Location by platform:
    - Windows: %APPDATA%/mostlylucid-dse
    - Linux: ~/.local/share/mostlylucid-dse
    - macOS: ~/Library/Application Support/mostlylucid-dse

    Args:
        app_name: Application name for directory

    Returns:
        Path to user data directory (creates if doesn't exist)
    """
    import platform

    system = platform.system()

    if system == "Windows":
        # %APPDATA%
        import os
        base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        data_dir = base / app_name
    elif system == "Darwin":
        # macOS: ~/Library/Application Support
        data_dir = Path.home() / 'Library' / 'Application Support' / app_name
    else:
        # Linux/Unix: ~/.local/share
        data_dir = Path.home() / '.local' / 'share' / app_name

    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_bundled_or_user_path(
    relative_path: Union[str, Path],
    writable: bool = False
) -> Path:
    """
    Get path that works for both bundled and user-modified resources.

    For read-only resources (config, prompts):
    - Use bundled location if running as executable
    - Use working directory if running as script

    For writable resources (nodes, tools, logs):
    - Use user data directory if running as executable
    - Use working directory if running as script

    Args:
        relative_path: Path relative to application root
        writable: True if resource needs write access

    Returns:
        Appropriate path for the resource

    Example:
        >>> # Read bundled config
        >>> config = get_bundled_or_user_path("config.yaml")

        >>> # Write to user directory
        >>> nodes = get_bundled_or_user_path("nodes", writable=True)
    """
    if writable and is_frozen():
        # Need write access and running as executable - use user directory
        return get_user_data_dir() / relative_path
    else:
        # Read-only or running as script - use bundled/working directory
        return get_resource_path(relative_path)


# Convenience functions
def get_config_path() -> Path:
    """Get config.yaml path (read-only bundled resource)."""
    return get_resource_path("config.yaml")


def get_prompts_path() -> Path:
    """Get prompts directory path (read-only bundled resource)."""
    return get_resource_path("prompts")


def get_tools_path() -> Path:
    """Get tools directory path (writable, may need user directory)."""
    return get_bundled_or_user_path("tools", writable=True)


def get_nodes_path() -> Path:
    """Get nodes directory path (writable, may need user directory)."""
    return get_bundled_or_user_path("nodes", writable=True)


def get_registry_path() -> Path:
    """Get registry directory path (writable, may need user directory)."""
    return get_bundled_or_user_path("registry", writable=True)


def get_rag_memory_path() -> Path:
    """Get RAG memory directory path (writable, may need user directory)."""
    return get_bundled_or_user_path("rag_memory", writable=True)
