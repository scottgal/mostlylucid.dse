"""
Package Validator Service
Validates pip package installation requests against trusted package allowlist.
"""

import os
import yaml
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from packaging import version
from packaging.specifiers import SpecifierSet
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PackageValidationError(Exception):
    """Raised when package validation fails"""
    pass


class PackageValidator:
    """
    Validates pip package installation requests against a trusted allowlist.

    Features:
    - Allowlist-based package approval
    - Version constraint validation
    - Security checks for blocked packages
    - Installation logging and audit trail
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the package validator.

        Args:
            config_path: Path to trusted_packages.yaml. If None, uses default location.
        """
        if config_path is None:
            # Default to trusted_packages.yaml in code_evolver directory
            config_path = Path(__file__).parent.parent / "trusted_packages.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.trusted_packages = self._parse_trusted_packages()
        self.blocked_packages = set(self.config.get('security', {}).get('blocked_packages', []))
        self.requires_approval = set(self.config.get('security', {}).get('requires_approval', []))
        self.max_packages = self.config.get('security', {}).get('max_packages_per_workflow', 10)
        self.log_enabled = self.config.get('security', {}).get('log_installations', True)
        self.log_file = self.config.get('security', {}).get('log_file', 'logs/pip_installations.log')

    def _load_config(self) -> Dict:
        """Load the trusted packages configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Trusted packages configuration not found at {self.config_path}"
            )

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        return config

    def _parse_trusted_packages(self) -> Dict[str, Dict]:
        """
        Parse trusted packages from config into a lookup dictionary.

        Returns:
            Dict mapping package name to package metadata
        """
        packages = {}

        for pkg in self.config.get('trusted_packages', []):
            name = pkg['name'].lower()  # Normalize to lowercase
            packages[name] = {
                'versions': pkg.get('versions', []),
                'purpose': pkg.get('purpose', ''),
                'categories': pkg.get('categories', [])
            }

        return packages

    def validate_package(
        self,
        package_name: str,
        version_spec: Optional[str] = None,
        context: str = "unknown"
    ) -> Tuple[bool, str]:
        """
        Validate a single package installation request.

        Args:
            package_name: Name of the package to install
            version_spec: Optional version specifier (e.g., ">=2.0.0")
            context: Context of the request (workflow_id, tool_id, etc.)

        Returns:
            Tuple of (is_valid, message)
        """
        package_name_lower = package_name.lower()

        # Check if package is blocked
        if package_name_lower in self.blocked_packages:
            msg = f"Package '{package_name}' is blocked for security reasons"
            self._log_validation(package_name, version_spec, context, False, msg)
            return False, msg

        # Check if package requires approval
        if package_name_lower in self.requires_approval:
            msg = f"Package '{package_name}' requires explicit approval"
            self._log_validation(package_name, version_spec, context, False, msg)
            return False, msg

        # Check if package is in trusted list
        if package_name_lower not in self.trusted_packages:
            msg = f"Package '{package_name}' is not in the trusted packages list"
            self._log_validation(package_name, version_spec, context, False, msg)
            return False, msg

        # Validate version constraints
        trusted_pkg = self.trusted_packages[package_name_lower]
        trusted_versions = trusted_pkg.get('versions', [])

        if version_spec and trusted_versions:
            # Check if requested version is compatible with trusted versions
            try:
                is_valid = self._validate_version_compatibility(version_spec, trusted_versions)
                if not is_valid:
                    msg = (
                        f"Version '{version_spec}' for package '{package_name}' "
                        f"does not match trusted versions: {trusted_versions}"
                    )
                    self._log_validation(package_name, version_spec, context, False, msg)
                    return False, msg
            except Exception as e:
                msg = f"Error validating version for '{package_name}': {str(e)}"
                self._log_validation(package_name, version_spec, context, False, msg)
                return False, msg

        # Package is valid
        msg = f"Package '{package_name}' validated successfully"
        self._log_validation(package_name, version_spec, context, True, msg)
        return True, msg

    def _validate_version_compatibility(
        self,
        requested_spec: str,
        trusted_specs: List[str]
    ) -> bool:
        """
        Check if requested version specifier is compatible with trusted versions.

        Args:
            requested_spec: Requested version specifier (e.g., ">=2.0.0")
            trusted_specs: List of trusted version specifiers

        Returns:
            True if compatible, False otherwise
        """
        # Parse requested specifier
        try:
            requested = SpecifierSet(requested_spec)
        except Exception:
            # If parsing fails, reject
            return False

        # Parse trusted specifiers
        trusted_set = SpecifierSet(','.join(trusted_specs))

        # Check if there's any overlap
        # For simplicity, we check if the requested spec is a subset of trusted
        # This is conservative - we could make it more permissive

        # Simple check: if requested spec matches trusted spec pattern
        for trusted_spec in trusted_specs:
            if requested_spec == trusted_spec or requested_spec in trusted_spec:
                return True

        # More complex: check if ranges overlap
        # For now, we use a simple heuristic: the requested spec should not be
        # more permissive than the trusted specs
        return str(requested) in str(trusted_set) or self._specs_overlap(requested, trusted_set)

    def _specs_overlap(self, spec1: SpecifierSet, spec2: SpecifierSet) -> bool:
        """
        Check if two version specifier sets overlap.

        This is a simplified check. For production, use packaging library's
        full intersection logic.
        """
        # Sample some common versions to see if they match both specs
        test_versions = [
            "1.0.0", "2.0.0", "3.0.0", "4.0.0", "5.0.0",
            "1.24.0", "2.31.0", "3.7.0", "10.0.0"
        ]

        for v in test_versions:
            try:
                ver = version.parse(v)
                if ver in spec1 and ver in spec2:
                    return True
            except Exception:
                continue

        return False

    def validate_batch(
        self,
        packages: List[Dict[str, str]],
        context: str = "unknown"
    ) -> Tuple[bool, List[str]]:
        """
        Validate a batch of package installation requests.

        Args:
            packages: List of dicts with 'name' and optional 'version' keys
            context: Context of the request (workflow_id, etc.)

        Returns:
            Tuple of (all_valid, list of error messages)
        """
        if len(packages) > self.max_packages:
            return False, [
                f"Too many packages requested ({len(packages)}). "
                f"Maximum allowed: {self.max_packages}"
            ]

        errors = []

        for pkg in packages:
            name = pkg.get('name')
            version_spec = pkg.get('version')

            if not name:
                errors.append("Package name is required")
                continue

            is_valid, msg = self.validate_package(name, version_spec, context)
            if not is_valid:
                errors.append(msg)

        return len(errors) == 0, errors

    def _log_validation(
        self,
        package_name: str,
        version_spec: Optional[str],
        context: str,
        success: bool,
        message: str
    ):
        """Log validation attempt for audit trail."""
        if not self.log_enabled:
            return

        try:
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().isoformat()
            version_str = version_spec if version_spec else "any"
            status = "SUCCESS" if success else "FAILED"

            log_entry = (
                f"[{timestamp}] {status} | "
                f"Package: {package_name} | "
                f"Version: {version_str} | "
                f"Context: {context} | "
                f"Message: {message}\n"
            )

            with open(self.log_file, 'a') as f:
                f.write(log_entry)

        except Exception as e:
            logger.error(f"Failed to log validation: {e}")

    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """
        Get information about a trusted package.

        Args:
            package_name: Name of the package

        Returns:
            Package metadata dict or None if not found
        """
        return self.trusted_packages.get(package_name.lower())

    def list_trusted_packages(self, category: Optional[str] = None) -> List[Dict]:
        """
        List all trusted packages, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., "web", "data")

        Returns:
            List of package metadata dicts
        """
        packages = []

        for name, info in self.trusted_packages.items():
            if category is None or category in info.get('categories', []):
                packages.append({
                    'name': name,
                    **info
                })

        return packages

    def add_trusted_package(
        self,
        name: str,
        versions: List[str],
        purpose: str,
        categories: List[str]
    ):
        """
        Add a new package to the trusted list (updates config file).

        Args:
            name: Package name
            versions: List of allowed version specifiers
            purpose: Description of package purpose
            categories: List of category tags
        """
        # Add to in-memory structure
        self.trusted_packages[name.lower()] = {
            'versions': versions,
            'purpose': purpose,
            'categories': categories
        }

        # Update config file
        self.config['trusted_packages'].append({
            'name': name,
            'versions': versions,
            'purpose': purpose,
            'categories': categories
        })

        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Added trusted package: {name}")


# Singleton instance for easy access
_validator_instance = None

def get_validator() -> PackageValidator:
    """Get the singleton PackageValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = PackageValidator()
    return _validator_instance


# Convenience functions
def validate_package(package_name: str, version_spec: Optional[str] = None, context: str = "unknown") -> Tuple[bool, str]:
    """Validate a single package. Returns (is_valid, message)."""
    return get_validator().validate_package(package_name, version_spec, context)


def validate_packages(packages: List[Dict[str, str]], context: str = "unknown") -> Tuple[bool, List[str]]:
    """Validate a batch of packages. Returns (all_valid, error_messages)."""
    return get_validator().validate_batch(packages, context)


def list_packages(category: Optional[str] = None) -> List[Dict]:
    """List all trusted packages, optionally filtered by category."""
    return get_validator().list_trusted_packages(category)
