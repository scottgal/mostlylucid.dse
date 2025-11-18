# Little Puddleton Gazette - Gradual Chaos News Site

A joke website that looks like a legitimate local news site, but stories get progressively weirder as users click "Fit My Likes".

## The Concept

The site presents mundane village news stories that **gradually escalate into absurdist chaos** filled with Monty Python, Fast Show, Mitchell & Webb, and other British comedy references.

Each story has **10 versions** (0-9):
- **Version 0**: Completely mundane (bus timetables, parking debates, etc.)
- **Version 1-2**: Slightly odd details creep in
- **Version 3-5**: Monty Python and Fast Show references appear
- **Version 6-7**: Full absurdist chaos
- **Version 8-9**: Complete madness

## How It Works

### The "Fit My Likes" Feature

When users click the **"Fit My Likes"** button:

1. The story updates to the next version (gradually weirder)
2. Their preference is saved in `localStorage` (`story-<id>-version: <number>`)
3. When they return, they see the version they "selected"
4. The joke: they're **training the algorithm** to show them progressively bizarre content

The visual effect shows the text updating in real-time, creating the illusion of AI personalization.

## Project Structure

```
news_site/
├── app.py                  # Flask application
├── templates/
│   ├── base.html          # Base template with newspaper styling
│   ├── index.html         # Story list page
│   └── story.html         # Individual story page with "Fit My Likes"
├── stories/               # Generated .md story files
│   ├── story_01_v00.md   # Story 1, version 0 (mundane)
│   ├── story_01_v01.md   # Story 1, version 1 (slightly odd)
│   └── ...
└── requirements.txt       # Python dependencies

code_evolver/
└── gradual_chaos_generator.py  # Story generation system
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python packages
pip install Flask requests markdown

# Or use requirements.txt
cd news_site
pip install -r requirements.txt
```

### 2. Ensure Ollama is Running

The generator uses Ollama for AI generation:

```bash
# Check Ollama is running
ollama list

# Should show gemma3:4b or another model
# If not, pull a model:
ollama pull gemma3:4b
```

### 3. Generate Stories

Generate the news stories with progressive weirdness:

```bash
# Generate a single story (for testing)
python code_evolver/gradual_chaos_generator.py \
  --iterations 9 \
  --topic "parish council debates parking" \
  --temperature 0.93 \
  --model "gemma3:4b" \
  --name "test_story"

# Or generate all stories for the site
python generate_news_stories.py
```

This creates 10 stories, each with 10 versions (100 files total).

### 4. Move Stories to Website

```bash
# The generate_news_stories.py script does this automatically
# But if needed manually:
mkdir -p news_site/stories
cp code_evolver/gradual_chaos_output/*.md news_site/stories/
```

### 5. Run the Website

```bash
cd news_site
python app.py
```

Open http://localhost:5000 in your browser.

## How to Use the Site

1. **Homepage**: Browse mundane local news stories
2. **Click a story**: Read the (initially) boring article
3. **Click "Fit My Likes"**: Story updates to be slightly weirder
4. **Keep clicking**: Watch chaos gradually escalate
5. **Refresh the page**: Your "preference" is remembered via localStorage
6. **Share with friends**: They start at version 0, you see your weird version

## Generator Configuration

### Temperature

Controls creativity (randomness):

```bash
--temperature 0.93  # High creativity (recommended for comedy)
--temperature 0.7   # More conservative
--temperature 1.0   # Maximum chaos
```

### Iterations

Number of progressive weirdness levels:

```bash
--iterations 4   # 5 versions (0-4) - quick test
--iterations 9   # 10 versions (0-9) - full experience
```

### Model

Which Ollama model to use:

```bash
--model "gemma3:4b"        # Fast, creative
--model "llama3:latest"    # Larger, more coherent
--model "codellama:7b"     # Alternative option
```

## Comedy Reference Escalation

The generator progressively adds:

1. **Level 1**: Unexpected Spanish Inquisition, dead parrots, cheese shops
2. **Level 2**: Ministry of Silly Walks, Knights who say Ni
3. **Level 3**: Fast Show (Competitive Dad, "Brilliant!", "Suits you sir")
4. **Level 4**: Mitchell & Webb (Numberwang, "Are we the baddies?")
5. **Level 5**: Four Yorkshiremen, IT Crowd, Black Books
6. **Level 6**: Complete mashup chaos
7. **Level 7**: Alan Partridge, Brian Blessed moments
8. **Level 8-9**: Maximum absurdist British comedy

## Customization

### Add More Topics

Edit `generate_news_stories.py`:

```python
STORY_TOPICS = [
    "parish council debates new parking restrictions",
    "annual village fete raises funds for church roof",
    # Add your mundane topics here
]
```

### Change Writer Personas

Edit `gradual_chaos_generator.py`:

```python
WRITER_PERSONAS = [
    "a retired local journalist who loves community events",
    "an enthusiastic young reporter fresh out of journalism school",
    # Add more personas
]
```

### Customize Comedy References

Edit the `ODDIFICATION_LEVELS` in `gradual_chaos_generator.py` to add different comedy references.

## File Format

Each story version is a markdown file:

```markdown
---
story_number: 1
iteration: 3
weirdness_level: 30%
generated: 2025-01-18T10:30:00
---

**Headline Goes Here**

Story content with progressive weirdness...
```

## API Endpoints

The Flask app provides:

- `GET /` - Homepage with story list
- `GET /story/<story_id>` - Individual story page
- `GET /api/story/<num>/version/<ver>` - JSON API for story versions

Example API response:

```json
{
  "success": true,
  "version": 3,
  "max_version": 9,
  "headline": "Parish Council Debates Parking (And Knights Say Ni)",
  "content": "Full markdown content..."
}
```

## Deployment

For production deployment:

```bash
# Use a production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### "No stories available"

Generate stories first:
```bash
python generate_news_stories.py
```

### Ollama connection errors

Check Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

### Stories not weird enough

Increase temperature:
```bash
--temperature 0.95
```

Or regenerate with more iterations:
```bash
--iterations 12
```

## License

MIT License - Use for your comedy projects!

## Credits

Built with:
- Flask (web framework)
- Ollama (local AI generation)
- British comedy (essential ingredient)

Inspired by the absurdist genius of:
- Monty Python
- The Fast Show
- Mitchell and Webb
- The IT Crowd
- Black Books
- And many more...

---

**Remember**: The real joke is that this is exactly how recommendation algorithms work, just with British comedy instead of cat videos.
