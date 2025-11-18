#!/bin/bash
# ============================================================================
# Build DiSE Executable (Linux/Mac)
# ============================================================================

echo ""
echo "========================================"
echo " Building DiSE Executable"
echo "========================================"
echo ""

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[ERROR] PyInstaller not found!"
    echo ""
    echo "Installing PyInstaller..."
    pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install PyInstaller"
        exit 1
    fi
fi

# Clean previous builds
echo "[1/3] Cleaning previous builds..."
rm -rf build dist *.spec

# Build the executable
echo "[2/3] Building executable..."
python3 build.py --clean

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Build failed!"
    exit 1
fi

# Show results
echo ""
echo "[3/3] Build complete!"
echo ""
if [ -f "dist/DiSE" ]; then
    echo "✓ Executable: dist/DiSE"
    ls -lh "dist/DiSE" | awk '{print "  Size:", $5}'
fi
if [ -f "dist/DiSE-linux.zip" ]; then
    echo "✓ Package: dist/DiSE-linux.zip"
fi
echo ""
echo "========================================"
echo " Success!"
echo "========================================"
echo ""
