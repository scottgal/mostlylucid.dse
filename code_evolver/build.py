#!/usr/bin/env python3
"""
Build script for creating standalone executables using PyInstaller.
Supports Windows, Linux, and macOS platforms.
"""
import sys
import platform
import subprocess
import shutil
import argparse
from pathlib import Path


def get_platform():
    """Detect current platform."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    else:
        return "unknown"


def clean_build_dirs():
    """Clean previous build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]

    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_path)

    # Clean spec files
    for spec_file in Path(".").glob("*.spec"):
        print(f"Removing {spec_file}...")
        spec_file.unlink()


def build_executable(platform_name: str, app_name: str = "CodeEvolver"):
    """
    Build executable for specified platform.

    Args:
        platform_name: Target platform (windows, linux, macos)
        app_name: Application name
    """
    print(f"\n{'='*60}")
    print(f"Building {app_name} for {platform_name}")
    print(f"{'='*60}\n")

    # Base PyInstaller arguments
    args = [
        "pyinstaller",
        "--name", app_name,
        "--onefile",  # Single executable
        "--clean",
        "--noconfirm",
    ]

    # Add data files
    data_files = [
        ("prompts", "prompts"),
        ("config.yaml", "."),
    ]

    for src, dest in data_files:
        if Path(src).exists():
            args.extend(["--add-data", f"{src}{';' if platform_name == 'windows' else ':'}{dest}"])

    # Platform-specific settings
    if platform_name == "windows":
        args.append("--noconsole")  # Hide console window
        # args.extend(["--icon", "icon.ico"])  # Add if icon exists

    elif platform_name == "macos":
        args.extend([
            "--windowed",
            # "--icon", "icon.icns",  # Add if icon exists
        ])

    # Entry point
    args.append("chat_cli.py")

    print("Running PyInstaller with arguments:")
    print(" ".join(args))
    print()

    try:
        result = subprocess.run(args, check=True)

        if result.returncode == 0:
            print(f"\n{'='*60}")
            print(f"✓ Build successful!")
            print(f"{'='*60}")

            # Show output location
            if platform_name == "windows":
                exe_path = Path("dist") / f"{app_name}.exe"
            elif platform_name == "macos":
                exe_path = Path("dist") / f"{app_name}.app"
            else:
                exe_path = Path("dist") / app_name

            if exe_path.exists():
                print(f"\nExecutable created: {exe_path.absolute()}")

                # Get size
                if exe_path.is_file():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"Size: {size_mb:.2f} MB")
            else:
                print(f"\nWarning: Expected executable not found at {exe_path}")

            return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with error code {e.returncode}")
        return False

    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        return False


def create_installer_script(platform_name: str):
    """Create platform-specific installer script."""
    if platform_name == "windows":
        # Create batch installer
        install_script = """@echo off
echo Installing CodeEvolver...
mkdir "%APPDATA%\\CodeEvolver"
copy CodeEvolver.exe "%APPDATA%\\CodeEvolver\\"
copy config.yaml "%APPDATA%\\CodeEvolver\\"
echo Installation complete!
echo.
echo Run from: %APPDATA%\\CodeEvolver\\CodeEvolver.exe
pause
"""
        with open("dist/install.bat", "w") as f:
            f.write(install_script)

        print("✓ Created installer: dist/install.bat")

    elif platform_name == "linux":
        # Create shell installer
        install_script = """#!/bin/bash
echo "Installing CodeEvolver..."
mkdir -p ~/.local/bin
mkdir -p ~/.config/code_evolver
cp CodeEvolver ~/.local/bin/
cp config.yaml ~/.config/code_evolver/
chmod +x ~/.local/bin/CodeEvolver
echo "Installation complete!"
echo ""
echo "Add ~/.local/bin to PATH if not already added:"
echo "  export PATH=\\"$HOME/.local/bin:\\$PATH\\""
echo ""
echo "Run with: CodeEvolver"
"""
        install_path = Path("dist/install.sh")
        with open(install_path, "w") as f:
            f.write(install_script)

        install_path.chmod(0o755)
        print("✓ Created installer: dist/install.sh")


def package_distribution(platform_name: str, app_name: str):
    """Create distribution package."""
    print(f"\nCreating distribution package...")

    dist_name = f"{app_name}-{platform_name}"
    dist_dir = Path("dist") / dist_name

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    dist_dir.mkdir(parents=True)

    # Copy executable
    if platform_name == "windows":
        exe_name = f"{app_name}.exe"
    elif platform_name == "macos":
        exe_name = f"{app_name}.app"
    else:
        exe_name = app_name

    exe_src = Path("dist") / exe_name
    if exe_src.exists():
        if exe_src.is_dir():
            shutil.copytree(exe_src, dist_dir / exe_name)
        else:
            shutil.copy(exe_src, dist_dir / exe_name)

    # Copy additional files
    files_to_copy = [
        "config.yaml",
        "README.md",
        "LICENSE",
    ]

    for file_name in files_to_copy:
        file_path = Path(file_name)
        if file_path.exists():
            shutil.copy(file_path, dist_dir / file_name)

    # Copy prompts directory
    prompts_src = Path("prompts")
    if prompts_src.exists():
        shutil.copytree(prompts_src, dist_dir / "prompts")

    # Create installer
    create_installer_script(platform_name)

    # Copy installer to distribution
    if platform_name == "windows":
        installer = Path("dist/install.bat")
        if installer.exists():
            shutil.copy(installer, dist_dir / "install.bat")
    else:
        installer = Path("dist/install.sh")
        if installer.exists():
            shutil.copy(installer, dist_dir / "install.sh")

    # Create archive
    archive_name = f"{dist_name}"
    print(f"\nCreating archive: {archive_name}")

    shutil.make_archive(
        str(Path("dist") / archive_name),
        "zip",
        str(dist_dir.parent),
        str(dist_dir.name)
    )

    print(f"✓ Distribution package created: dist/{archive_name}.zip")


def main():
    """Main build script."""
    parser = argparse.ArgumentParser(description="Build CodeEvolver executable")
    parser.add_argument(
        "--platform",
        choices=["windows", "linux", "macos", "auto"],
        default="auto",
        help="Target platform (default: auto-detect)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build for all platforms (requires cross-compilation support)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building"
    )
    parser.add_argument(
        "--no-package",
        action="store_true",
        help="Skip creating distribution package"
    )
    parser.add_argument(
        "--app-name",
        default="CodeEvolver",
        help="Application name (default: CodeEvolver)"
    )

    args = parser.parse_args()

    # Detect platform if auto
    if args.platform == "auto":
        args.platform = get_platform()

        if args.platform == "unknown":
            print("Error: Could not detect platform")
            return 1

    print("CodeEvolver Build Script")
    print(f"Target platform: {args.platform}")
    print()

    # Check if PyInstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: PyInstaller not found")
        print("Install with: pip install pyinstaller")
        return 1

    # Clean if requested
    if args.clean:
        clean_build_dirs()

    # Build for specified platform(s)
    if args.all:
        platforms = ["windows", "linux", "macos"]
        print("Warning: Building for all platforms requires cross-compilation support")
        print("This will attempt to build for: " + ", ".join(platforms))
        print()
    else:
        platforms = [args.platform]

    success = True

    for platform_name in platforms:
        if not build_executable(platform_name, args.app_name):
            success = False
            continue

        if not args.no_package:
            try:
                package_distribution(platform_name, args.app_name)
            except Exception as e:
                print(f"Warning: Failed to create distribution package: {e}")

    if success:
        print(f"\n{'='*60}")
        print("✓ All builds completed successfully!")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("✗ Some builds failed")
        print(f"{'='*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
