#!/bin/bash
# Example: Generate a conversation flow diagram

echo "=========================================="
echo "Conversation Flow Example"
echo "=========================================="
echo ""

# Build conversation diagram
echo "Building conversation flow diagram..."

CONVERSATION_JSON=$(cat <<'EOF'
{
  "diagram_type": "conversation",
  "title": "Technical Support Conversation",
  "conversation": [
    {
      "role": "user",
      "content": "My application won't start. I'm getting a 'Connection refused' error."
    },
    {
      "role": "assistant",
      "content": "Let me help you troubleshoot. Can you check if the database service is running?"
    },
    {
      "role": "user",
      "content": "How do I check that?"
    },
    {
      "role": "assistant",
      "content": "Run this command: systemctl status postgresql"
    },
    {
      "role": "user",
      "content": "It says 'inactive (dead)'"
    },
    {
      "role": "assistant",
      "content": "The database is down. Let's start it: sudo systemctl start postgresql"
    },
    {
      "role": "user",
      "content": "Done! The application is working now. Thank you!"
    },
    {
      "role": "assistant",
      "content": "Great! Consider enabling auto-start: sudo systemctl enable postgresql"
    }
  ]
}
EOF
)

RESULT=$(echo "$CONVERSATION_JSON" | python code_evolver/tools/visualization/mermaid_builder.py)

if [ $? -eq 0 ]; then
    echo "✓ Conversation diagram built successfully"
    MERMAID=$(echo "$RESULT" | jq -r '.mermaid')
    echo ""
    echo "Mermaid syntax:"
    echo "----------------------------------------"
    echo "$MERMAID"
    echo "----------------------------------------"

    # Render with dark theme
    echo ""
    echo "Rendering to SVG (dark theme)..."
    RENDER_JSON=$(cat <<EOF
{
  "mermaid": $(echo "$MERMAID" | jq -Rs .),
  "format": "svg",
  "theme": "dark",
  "output_path": "/tmp/conversation_flow.svg"
}
EOF
)

    RENDER_RESULT=$(echo "$RENDER_JSON" | python code_evolver/tools/visualization/mermaid_renderer.py)

    if [ $? -eq 0 ]; then
        OUTPUT_PATH=$(echo "$RENDER_RESULT" | jq -r '.output_path')
        echo "✓ Diagram rendered successfully"
        echo "  Output: $OUTPUT_PATH"
    fi
else
    echo "✗ Failed to build diagram"
    echo "$RESULT"
    exit 1
fi

echo ""
echo "=========================================="
echo "Example completed!"
echo "=========================================="
echo ""
echo "View the diagram: xdg-open /tmp/conversation_flow.svg"
echo ""
