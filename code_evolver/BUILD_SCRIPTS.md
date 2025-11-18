# Build Scripts

## Overview

Two sets of build scripts are provided for creating standalone executables:

1. **Simple Build** - Basic executable compilation
2. **Meta Build** - The compiler compiles itself! (Ouroboros style 🐍)

## Scripts

### Windows

- `build_exe.bat` - Simple build script
- `compile_the_compiler.bat` - Meta build (self-compilation)

### Linux/Mac

- `build_exe.sh` - Simple build script
- `compile_the_compiler.sh` - Meta build (self-compilation)

---

## Quick Start

### Simple Build

**Windows:**
```cmd
build_exe.bat
```

**Linux/Mac:**
```bash
./build_exe.sh
```

**What it does:**
1. Checks/installs PyInstaller
2. Cleans previous builds
3. Builds the executable
4. Shows output location and size

**Output:**
- `dist/DiSE.exe` (Windows)
- `dist/DiSE` (Linux/Mac)
- `dist/DiSE-{platform}.zip` (distribution package)

---

## Meta Build (Compile the Compiler!)

### The Ouroboros Build 🐍

This script makes **DiSE compile itself** - a true meta moment!

**Windows:**
```cmd
compile_the_compiler.bat
```

**Linux/Mac:**
```bash
./compile_the_compiler.sh
```

**What it does:**
1. **Backup Phase**: Saves previous executable with timestamp
2. **Verification Phase**: Checks Python, dependencies, PyInstaller
3. **Self-Compilation Phase**: DiSE builds itself!
4. **Validation Phase**: Tests the new executable
5. **Celebration Phase**: Declares victory over recursion

**Special Features:**
- ✅ Automatic backups (stored in `dist/backups/`)
- ✅ Dependency verification
- ✅ Post-build validation
- ✅ Poetic achievement message

**Output:**
```
============================================
 SUCCESS! The Compiler Compiled Itself!
============================================

Output files:
  • dist/DiSE.exe
  • dist/DiSE-windows.zip
  • Previous versions: dist/backups/

The snake has eaten its own tail! 🐍
(Ouroboros moment achieved)
```

---

## What Gets Included

Both scripts automatically bundle:

- ✅ `config.yaml` - Your configuration (including LLMApi settings)
- ✅ `prompts/` - All prompt templates
- ✅ `APP_MANUAL.md` - System manual for AI self-reference
- ✅ `CLAUDE.md` - Complete system documentation
- ✅ `BUILD_SCRIPTS.md` - Build instructions
- ✅ `QUICKSTART.md` - Quick start guide
- ✅ `README.md` - Project README
- ✅ Python dependencies (via PyInstaller)
- ✅ LICENSE (if present)

**Note:** The executable uses `--onefile` mode, which creates a single .exe file that extracts to a temporary directory on each run. This ensures all bundled files are available at runtime.

---

## Requirements

**Automatically handled by scripts:**
- Python 3.8+
- PyInstaller (auto-installed if missing)

**Project dependencies** (from `requirements.txt`):
- anthropic
- ollama
- qdrant-client
- rich
- ... and more

The meta build script checks all of these and installs them if needed.

---

## Build Output Structure

```
dist/
├── DiSE.exe                # Main executable
├── DiSE-windows.zip        # Distribution package
├── DiSE-windows/           # Unpacked distribution
│   ├── DiSE.exe
│   ├── config.yaml
│   ├── prompts/
│   ├── install.bat               # Installation script
│   └── README.md
└── backups/                       # Previous versions (meta build only)
    ├── DiSE_20250118_143022.exe
    └── DiSE_20250118_150445.exe
```

---

## Troubleshooting

### "PyInstaller not found"
Script will automatically install it. If that fails:
```bash
pip install pyinstaller
```

### "Build failed"
1. Check Python version: `python --version` (need 3.8+)
2. Install dependencies: `pip install -r requirements.txt`
3. Try clean build: `python build.py --clean`

### "Executable won't run"
- Windows: Check if antivirus blocked it
- Linux/Mac: Make sure it's executable: `chmod +x dist/DiSE`

### Large executable size
This is normal! PyInstaller bundles:
- Python interpreter
- All dependencies
- Your code
- config.yaml

Typical size: 50-150 MB

---

## Advanced Usage

### Using the underlying build.py directly

```bash
# Auto-detect platform
python build.py

# Clean before building
python build.py --clean

# Skip packaging
python build.py --no-package

# Custom name
python build.py --app-name MyApp

# Specific platform
python build.py --platform windows
python build.py --platform linux
python build.py --platform macos
```

---

## Philosophy: The Meta Build

The `compile_the_compiler` script embodies a core principle of AI-assisted development:

> **A tool that can improve itself is truly self-sufficient.**

When DiSE compiles itself:
1. It demonstrates complete self-sufficiency
2. It validates that all dependencies are correct
3. It proves the build system works end-to-end
4. It creates a moment of beautiful recursion

*"I used the compiler to compile the compiler."* - Thanos, probably

---

## Quick Reference

| Task | Windows | Linux/Mac |
|------|---------|-----------|
| Simple build | `build_exe.bat` | `./build_exe.sh` |
| Meta build | `compile_the_compiler.bat` | `./compile_the_compiler.sh` |
| Output location | `dist\DiSE.exe` | `dist/DiSE` |
| Backups | `dist\backups\` | `dist/backups/` |

---

## Tips

1. **Use meta build for releases** - It validates everything
2. **Simple build for quick testing** - Faster, less verification
3. **Check backups folder** - Previous versions auto-saved
4. **config.yaml is bundled** - Any changes will be in the exe

---

*Built with ❤️ and recursion*
