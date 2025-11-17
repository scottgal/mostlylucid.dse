# Code Evolver - Flask Web UI

An interactive web interface for the Code Evolver dynamic workflow system. Features a beautiful chat interface with real-time workflow visualization and tool assembly animations.

## Features

- 🎨 **Beautiful Modern UI** - Gradient themes, smooth animations, and responsive design
- 💬 **Chat Interface** - AI-like chat experience for natural workflow requests
- 🔄 **Real-time Visualization** - Watch workflows being built and executed in real-time
- 🔧 **Tool Discovery Animation** - See tools being discovered and assembled dynamically
- 📊 **Progress Tracking** - Visual progress bars and status indicators
- ⚡ **WebSocket Communication** - Real-time updates using Socket.IO
- 🎯 **Interactive Workflow Steps** - Watch each step execute with visual feedback

## Screenshots

The interface includes:
- **Left Panel**: Chat interface with message history
- **Right Panel**: Live workflow visualization with:
  - Tools Discovery grid (animated cards)
  - Workflow Assembly steps (numbered, animated)
  - Progress tracking

## Quick Start

### Prerequisites

- Python 3.8+
- Code Evolver project installed

### Installation

1. Install dependencies:
```bash
cd flask_web_ui
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser to:
```
http://localhost:5000
```

## Usage

1. **Start a Conversation**: Type your workflow request in the chat input
2. **Watch the Magic**: See the system:
   - Analyze your request
   - Search for relevant tools
   - Build a workflow plan
   - Execute steps in sequence
3. **Try Example Prompts**: Click the suggested prompts to get started

## Architecture

### Backend (`app.py`)
- Flask application with Socket.IO integration
- Connects to Code Evolver core components:
  - `ConfigManager` - Configuration
  - `ToolsManager` - Tool registry
  - `WorkflowBuilder` - Workflow construction
  - `TaskEvaluator` - Task analysis
- Real-time event emission for UI updates

### Frontend

**HTML** (`templates/index.html`)
- Responsive two-panel layout
- Chat interface
- Visualization panels

**CSS** (`static/css/styles.css`)
- Modern design with CSS variables
- Gradient backgrounds
- Smooth animations
- Responsive breakpoints

**JavaScript** (`static/js/app.js`)
- Socket.IO client
- Real-time UI updates
- Animation orchestration
- Message formatting

## API Endpoints

### HTTP Endpoints

- `GET /` - Main application
- `GET /api/health` - Health check
- `GET /api/tools` - List all available tools
- `GET /api/tool/<tool_id>` - Get tool details

### WebSocket Events

**Client → Server:**
- `chat_message` - Send a chat message
- `get_history` - Request chat history

**Server → Client:**
- `connected` - Connection established
- `user_message` - User message echo
- `assistant_message` - AI response
- `status` - Status update
- `workflow_step` - Workflow progress update
- `tool_discovered` - Tool found and displayed
- `workflow_step_added` - New workflow step
- `workflow_step_executing` - Step execution started
- `workflow_step_completed` - Step execution completed
- `error` - Error message

## Customization

### Changing Colors

Edit `static/css/styles.css` and modify CSS variables:

```css
:root {
    --primary: #6366f1;        /* Primary color */
    --secondary: #ec4899;      /* Secondary color */
    --success: #10b981;        /* Success color */
    /* ... more variables ... */
}
```

### Adding New Visualizations

1. Add HTML structure in `templates/index.html`
2. Add styling in `static/css/styles.css`
3. Add WebSocket event handlers in `static/js/app.js`
4. Emit events from `app.py`

### Modifying Workflow Processing

Edit the `process_user_request()` function in `app.py` to:
- Change task evaluation logic
- Modify tool selection
- Customize workflow generation
- Add new processing steps

## Development

### Running in Debug Mode

The application runs in debug mode by default:

```python
socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### Adding Features

1. **New API Endpoint**:
   - Add route in `app.py`
   - Update frontend JavaScript

2. **New Visualization**:
   - Add HTML element
   - Style in CSS
   - Add WebSocket event
   - Emit from backend

3. **New Animation**:
   - Define keyframes in CSS
   - Apply animation class
   - Trigger from JavaScript

## Troubleshooting

### Connection Issues

If the WebSocket connection fails:
1. Check that the Flask server is running
2. Verify port 5000 is not in use
3. Check browser console for errors

### Missing Tools

If tools aren't loading:
1. Verify Code Evolver is properly installed
2. Check `config.yaml` path in `app.py`
3. Ensure tools index is populated

### Styling Issues

If styles aren't loading:
1. Verify static file paths
2. Check browser console for 404 errors
3. Clear browser cache

## Performance

### Optimization Tips

1. **Reduce Animation Delays**: Decrease animation durations in CSS
2. **Limit Tool Display**: Show only top N relevant tools
3. **Throttle Events**: Add debouncing for rapid events
4. **Pagination**: Add pagination for large tool lists

## Security

### Production Deployment

Before deploying to production:

1. **Change Secret Key**:
```python
app.config['SECRET_KEY'] = 'your-secure-random-key'
```

2. **Enable HTTPS**: Use a reverse proxy (nginx, Apache)
3. **Restrict CORS**: Limit allowed origins
4. **Add Authentication**: Implement user authentication
5. **Rate Limiting**: Add rate limiting for API endpoints

## Future Enhancements

Potential features to add:
- [ ] User authentication
- [ ] Workflow history
- [ ] Export workflows
- [ ] Collaborative editing
- [ ] Workflow templates
- [ ] Performance metrics
- [ ] Dark/light theme toggle
- [ ] Mobile optimization
- [ ] Voice input
- [ ] Workflow sharing

## License

Part of the Code Evolver project.

## Credits

Built with:
- Flask
- Socket.IO
- Modern CSS3
- Vanilla JavaScript

Fonts:
- Inter (UI)
- JetBrains Mono (Code)
