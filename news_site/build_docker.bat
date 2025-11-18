@echo off
REM Build and package the Older Dailly Gazette Docker image (Windows)

echo ==================================
echo Older Dailly Gazette Docker Build
echo ==================================
echo.

REM Check if stories directory exists
if not exist "stories\" (
    echo ERROR: stories directory not found!
    echo.
    echo Please generate stories first:
    echo   python generate_content.py
    echo.
    echo Or copy test story:
    echo   cd ..
    echo   python copy_test_story.py
    echo.
    exit /b 1
)

REM Count story files
dir /b stories\*.md >nul 2>&1
if errorlevel 1 (
    echo ERROR: No story files found in stories directory!
    echo.
    echo Please generate stories first.
    echo.
    exit /b 1
)

for /f %%A in ('dir /b stories\*.md ^| find /c /v ""') do set STORY_COUNT=%%A
echo Found %STORY_COUNT% story files
echo.

REM Build Docker image
echo Building Docker image...
docker build -t older-dailly-gazette:latest .

echo.
echo ==================================
echo Build Complete!
echo ==================================
echo.
echo To run the container:
echo   docker run -p 8080:8000 older-dailly-gazette:latest
echo.
echo Or use docker-compose:
echo   docker-compose up -d
echo.
echo Then open: http://localhost:8080
echo.
echo To save the image:
echo   docker save older-dailly-gazette:latest | gzip ^> older-dailly-gazette.tar.gz
echo.
