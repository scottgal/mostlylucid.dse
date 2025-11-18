#!/bin/bash
# Build and package the Older Dailly Gazette Docker image

set -e

echo "=================================="
echo "Older Dailly Gazette Docker Build"
echo "=================================="
echo ""

# Check if stories directory exists
if [ ! -d "stories" ] || [ -z "$(ls -A stories)" ]; then
    echo "ERROR: No stories found in stories/ directory!"
    echo ""
    echo "Please generate stories first:"
    echo "  python generate_content.py"
    echo ""
    echo "Or copy test story:"
    echo "  cd .."
    echo "  python copy_test_story.py"
    echo ""
    exit 1
fi

# Count stories
STORY_COUNT=$(ls -1 stories/*.md 2>/dev/null | wc -l)
echo "Found $STORY_COUNT story files"
echo ""

# Build Docker image
echo "Building Docker image..."
docker build -t older-dailly-gazette:latest .

echo ""
echo "=================================="
echo "Build Complete!"
echo "=================================="
echo ""
echo "To run the container:"
echo "  docker run -p 8000:8000 older-dailly-gazette:latest"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up -d"
echo ""
echo "Then open: http://localhost:8000"
echo ""
echo "To save the image:"
echo "  docker save older-dailly-gazette:latest | gzip > older-dailly-gazette.tar.gz"
echo ""
