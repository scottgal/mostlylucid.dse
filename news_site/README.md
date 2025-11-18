# Older Dailly Gazette - Local News Website

A joke website that looks like a legitimate Scottish local news site, but stories progressively get weirder.

## Quick Start

### 1. Generate Content (Background Process)

Leave this running to continuously generate stories:

```bash
python generate_content.py
```

This will:
- Generate stories with 50+ different mundane topics
- Each story has 10 progressive versions (mundane → chaos)
- Randomize temperature (0.90-0.95) for variety
- Save directly to `stories/` folder
- Run continuously until you press Ctrl+C

### 2. Start the Website

In a separate terminal:

```bash
python app.py
```

Then open: **http://localhost:5050**

## The "Fit My Likes" Feature

Users click the button thinking they're training an AI to personalize content. Actually:

1. All versions are pre-generated
2. Each click reveals the next level of weirdness
3. Version is saved in localStorage
4. When they return, they see their selected chaos level

## Files

```
news_site/
├── app.py                 # Flask web server
├── generate_content.py    # Background content generator
├── templates/             # HTML templates
│   ├── base.html         # Newspaper design
│   ├── index.html        # Story list
│   └── story.html        # Story + "Fit My Likes"
└── stories/              # Generated stories
    ├── story_01_v00.md   # Version 0 (mundane)
    ├── story_01_v01.md   # Version 1 (slightly odd)
    └── ...
```

## Content Generator Details

### Topics

50+ mundane local news topics:
- Council meetings
- Community events
- Transport changes
- Local business
- Schools
- Nature
- Weather
- Mild crime reports
- Heritage
- Miscellaneous village news

### Progressive Weirdness

Each story has 10 versions:
- **v00**: Completely mundane
- **v01-v03**: Slightly unusual details
- **v04-v06**: Genuinely weird elements
- **v07-v09**: Full absurdist chaos

### Model Selection

Set the model with an environment variable:

```bash
# Use a different model
export OLLAMA_MODEL="llama3:latest"
python generate_content.py

# Or on Windows
set OLLAMA_MODEL=llama3:latest
python generate_content.py
```

Default: `gemma3:4b`

## Running Both Together

Terminal 1 - Content Generator:
```bash
python generate_content.py
```

Terminal 2 - Web Server:
```bash
python app.py
```

The website will automatically pick up new stories as they're generated!

## Statistics

The content generator shows:
- Stories generated
- Success/failure rate
- Current progress
- Press Ctrl+C to see final stats

Example output:
```
[14:32:15] Generating story 5: parish council debates new parking...
[14:33:42] ✓ Story 5 complete (10 versions)
Stats: 5 success, 0 failed (100.0% success rate)
```

## Deployment

For production (not recommended, but here's how):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Requirements

```bash
pip install Flask markdown requests
```

## The Village

**Older Dailly**
- Location: South Ayrshire, Scotland
- Near: A stile (local landmark)
- Newspaper: The Older Dailly Gazette
- Est: 1867
- Circulation: 847

## Tips

1. **Generate in background**: Let `generate_content.py` run overnight for lots of stories
2. **High variety**: Random temperatures ensure no two stories feel the same
3. **Check progress**: Stories appear on website immediately when saved
4. **Stop anytime**: Ctrl+C to stop generator cleanly

## Example Story Progression

**Version 0** (Mundane):
> Older Dailly Parish Council held its monthly meeting...

**Version 5** (Getting Strange):
> ...when Mrs. Periwinkle presented photographic evidence of a scarlet rooster wearing a velvet robe...

**Version 9** (Maximum Chaos):
> ...the rooster began performing interpretive dance while the council hummed in harmony...

---

**Built for laughs. Inspired by absurdist British comedy.**
