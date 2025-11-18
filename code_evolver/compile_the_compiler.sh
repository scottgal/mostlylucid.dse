#!/bin/bash
# ============================================================================
# META BUILD: Compile the Compiler (DiSE builds itself!)
# ============================================================================

echo ""
echo "============================================"
echo " META BUILD: Compile the Compiler!"
echo " (DiSE builds itself)"
echo "============================================"
echo ""

# Backup current executable if it exists
if [ -f "dist/DiSE" ]; then
    echo "[BACKUP] Saving previous executable..."
    mkdir -p "dist/backups"
    timestamp=$(date +%Y%m%d_%H%M%S)
    cp "dist/DiSE" "dist/backups/DiSE_${timestamp}"
    echo "  Backed up to: dist/backups/DiSE_${timestamp}"
    echo ""
fi

# Check Python environment
echo "[CHECK] Verifying Python environment..."
python3 --version
if [ $? -ne 0 ]; then
    echo "[ERROR] Python not found!"
    exit 1
fi

# Check dependencies
echo "[CHECK] Checking dependencies..."
python3 -c "import anthropic, ollama, qdrant_client, rich" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARNING] Some dependencies missing. Installing..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
fi

# Check PyInstaller
echo "[CHECK] Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INSTALL] Installing PyInstaller..."
    pip install pyinstaller
fi

echo ""
echo "============================================"
echo " Phase 1: Clean Previous Builds"
echo "============================================"
echo ""

rm -rf build dist/DiSE dist/DiSE-linux dist/DiSE-linux.zip *.spec

echo "✓ Cleaned"

echo ""
echo "============================================"
echo " Phase 2: Self-Compilation"
echo "============================================"
echo ""

# Run the build
python3 build.py --clean

if [ $? -ne 0 ]; then
    echo ""
    echo "============================================"
    echo " [ERROR] Self-compilation failed!"
    echo "============================================"
    exit 1
fi

echo ""
echo "============================================"
echo " Phase 3: Post-Build Verification"
echo "============================================"
echo ""

if [ ! -f "dist/DiSE" ]; then
    echo "[ERROR] Executable not found after build!"
    exit 1
fi

# Get file size
size=$(ls -lh "dist/DiSE" | awk '{print $5}')

echo "✓ Executable created: dist/DiSE"
echo "  Size: $size"

# Test if executable is valid
echo ""
echo "[TEST] Verifying executable..."
chmod +x "dist/DiSE"
"./dist/DiSE" --help >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[WARNING] Executable test failed - may not be fully functional"
else
    echo "✓ Executable validated"
fi

echo ""
echo "============================================"
echo " SUCCESS! The Compiler Compiled Itself!"
echo "============================================"
echo ""
echo "Output files:"
echo "  • dist/DiSE"
if [ -f "dist/DiSE-linux.zip" ]; then
    echo "  • dist/DiSE-linux.zip"
fi
if [ -d "dist/backups" ]; then
    echo "  • Previous versions: dist/backups/"
fi
echo ""
echo "The snake has eaten its own tail! 🐍"
echo "(Ouroboros moment achieved)"
echo ""
