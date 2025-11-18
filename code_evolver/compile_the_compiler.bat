@echo off
REM ============================================================================
REM META BUILD: Compile the Compiler (DiSE builds itself!)
REM ============================================================================

echo.
echo ============================================
echo  META BUILD: Compile the Compiler!
echo  (DiSE builds itself)
echo ============================================
echo.

REM Backup current executable if it exists
if exist "dist\DiSE.exe" (
    echo [BACKUP] Saving previous executable...
    if not exist "dist\backups" mkdir "dist\backups"
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
    for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
    copy "dist\DiSE.exe" "dist\backups\DiSE_%mydate%_%mytime%.exe" >nul
    echo   Backed up to: dist\backups\DiSE_%mydate%_%mytime%.exe
    echo.
)

REM Check Python environment
echo [CHECK] Verifying Python environment...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found!
    exit /b 1
)

REM Check dependencies
echo [CHECK] Checking dependencies...
python -c "import anthropic, ollama, qdrant_client, rich" 2>nul
if errorlevel 1 (
    echo [WARNING] Some dependencies missing. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        exit /b 1
    )
)

REM Check PyInstaller
echo [CHECK] Checking PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INSTALL] Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo ============================================
echo  Phase 1: Clean Previous Builds
echo ============================================
echo.

if exist build (
    echo Cleaning build directory...
    rmdir /s /q build 2>nul
    if exist build (
        echo Warning: Could not fully clean build directory ^(files may be in use^)
    )
)
if exist dist\DiSE.exe (
    echo Cleaning DiSE.exe...
    del /q dist\DiSE.exe 2>nul
    if exist dist\DiSE.exe (
        echo Warning: Could not delete DiSE.exe ^(file may be in use^)
    )
)
if exist dist\DiSE-windows (
    echo Cleaning DiSE-windows directory...
    rmdir /s /q dist\DiSE-windows 2>nul
    if exist dist\DiSE-windows (
        echo Warning: Could not fully clean DiSE-windows directory ^(files may be in use^)
    )
)
if exist dist\DiSE-windows.zip (
    echo Cleaning DiSE-windows.zip...
    del /q dist\DiSE-windows.zip 2>nul
)
if exist *.spec (
    echo Cleaning spec files...
    del /q *.spec 2>nul
)

echo ✓ Cleaned

echo.
echo ============================================
echo  Phase 2: Self-Compilation
echo ============================================
echo.

REM Run the build
python build.py --clean

if errorlevel 1 (
    echo.
    echo ============================================
    echo  [ERROR] Self-compilation failed!
    echo ============================================
    exit /b 1
)

echo.
echo ============================================
echo  Phase 3: Post-Build Verification
echo ============================================
echo.

if not exist "dist\DiSE.exe" (
    echo [ERROR] Executable not found after build!
    exit /b 1
)

REM Get file size
for %%I in ("dist\DiSE.exe") do (
    set size=%%~zI
    set /a size_mb=%%~zI/1024/1024
)

echo ✓ Executable created: dist\DiSE.exe
echo   Size: %size_mb% MB

REM Test if executable is valid
echo.
echo [TEST] Verifying executable...
"dist\DiSE.exe" --help >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Executable test failed - may not be fully functional
) else (
    echo ✓ Executable validated
)

echo.
echo ============================================
echo  SUCCESS! The Compiler Compiled Itself!
echo ============================================
echo.
echo Output files:
echo   • dist\DiSE.exe
if exist "dist\DiSE-windows.zip" (
    echo   • dist\DiSE-windows.zip
)
if exist "dist\backups" (
    echo   • Previous versions: dist\backups\
)
echo.
echo The snake has eaten its own tail! 🐍
echo (Ouroboros moment achieved)
echo.

pause
