#!/bin/bash
# Installation script for Mermaid diagram tools dependencies

set -e

echo "=========================================="
echo "Mermaid Diagram Tools - Dependency Installer"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Node.js is installed
echo "Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js is installed: $NODE_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Node.js is not installed"
    echo ""
    echo "Please install Node.js first:"
    echo "  - Ubuntu/Debian: sudo apt install nodejs npm"
    echo "  - macOS: brew install node"
    echo "  - Or download from: https://nodejs.org/"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if npm is installed
echo "Checking npm installation..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} npm is installed: $NPM_VERSION"
else
    echo -e "${RED}✗${NC} npm is not installed"
    echo "Please install npm along with Node.js"
    exit 1
fi

echo ""
echo "=========================================="
echo "Installing mermaid-cli..."
echo "=========================================="
echo ""

# Install mermaid-cli globally
echo "Running: npm install -g @mermaid-js/mermaid-cli"
if npm install -g @mermaid-js/mermaid-cli; then
    echo -e "${GREEN}✓${NC} mermaid-cli installed successfully"
else
    echo -e "${RED}✗${NC} Failed to install mermaid-cli"
    echo ""
    echo "If you got permission errors, try:"
    echo "  sudo npm install -g @mermaid-js/mermaid-cli"
    echo ""
    echo "Or install without sudo using nvm:"
    echo "  https://github.com/nvm-sh/nvm"
    exit 1
fi

# Verify installation
echo ""
echo "Verifying installation..."
if command -v mmdc &> /dev/null; then
    MMDC_VERSION=$(mmdc --version)
    echo -e "${GREEN}✓${NC} mmdc is available: $MMDC_VERSION"
else
    echo -e "${YELLOW}⚠${NC} mmdc command not found in PATH"
    echo "You may need to restart your terminal or add npm global bin to PATH"
fi

echo ""
echo "=========================================="
echo "Optional: Installing Playwright (fallback renderer)"
echo "=========================================="
echo ""

read -p "Install Playwright for fallback rendering? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing playwright..."
    pip install playwright

    echo "Installing Chromium browser..."
    playwright install chromium

    echo -e "${GREEN}✓${NC} Playwright installed successfully"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "You can now use the Mermaid diagram tools:"
echo ""
echo "  • Mermaid Builder: code_evolver/tools/visualization/mermaid_builder.py"
echo "  • Mermaid Renderer: code_evolver/tools/visualization/mermaid_renderer.py"
echo ""
echo "Run the examples:"
echo "  bash code_evolver/tools/visualization/examples/flowchart_example.sh"
echo ""
echo "Read the documentation:"
echo "  cat code_evolver/tools/visualization/README.md"
echo ""
