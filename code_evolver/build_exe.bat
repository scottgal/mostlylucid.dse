@echo off
REM ============================================================================
REM Build DiSE Executable
REM ============================================================================

echo.
echo ========================================
echo  Building DiSE Executable
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller not found!
    echo.
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        exit /b 1
    )
)

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist build (
    echo Cleaning build directory...
    rmdir /s /q build 2>nul
    if exist build (
        echo Warning: Could not fully clean build directory (files may be in use^)
    )
)
if exist dist (
    echo Cleaning dist directory...
    rmdir /s /q dist 2>nul
    if exist dist (
        echo Warning: Could not fully clean dist directory (files may be in use^)
    )
)
if exist *.spec (
    echo Cleaning spec files...
    del /q *.spec 2>nul
)

REM Build the executable
echo [2/3] Building executable...
python build.py --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    exit /b 1
)

REM Show results
echo.
echo [3/3] Build complete!
echo.
if exist "dist\DiSE.exe" (
    echo ✓ Executable: dist\DiSE.exe
    for %%I in ("dist\DiSE.exe") do echo   Size: %%~zI bytes
)
if exist "dist\DiSE-windows.zip" (
    echo ✓ Package: dist\DiSE-windows.zip
)
echo.
echo ========================================
echo  Success!
echo ========================================
echo.

pause
