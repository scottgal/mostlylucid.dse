# Older Dailly Gazette - Gradual Chaos News Generator

## What I've Built

A complete joke website system that looks like a legitimate Scottish local news site, but stories progressively get weirder as users click "Fit My Likes".

## System Components

### 1. **Gradual Chaos Generator** (`code_evolver/gradual_chaos_generator.py`)

Generates news stories with 10 progressive versions (0-9):
- **Version 0**: Completely mundane village news
- **Versions 1-3**: Slightly unusual details
- **Versions 4-6**: Genuinely weird elements
- **Versions 7-9**: Full absurdist chaos

**Key Features**:
- Different writer personas for variety
- High temperature (0.88-0.95) for creative chaos
- Each version adds ONE new odd element
- Maintains formal news tone throughout
- Inspired by absurdist UK comedy (not specific show references)

**Usage**:
```bash
python code_evolver/gradual_chaos_generator.py \
  --iterations 9 \
  --topic "village council debates parking" \
  --temperature 0.93 \
  --model "gemma3:4b" \
  --name "parking_story"
```

### 2. **Flask News Website** (`news_site/`)

A plausible-looking local news site with:
- Professional newspaper design
- Story list page with headlines and lures
- Individual story pages
- **"Fit My Likes" button** - the key feature!

**The Joke Mechanism**:
1. User clicks "Fit My Likes"
2. Story updates to next version (slightly weirder)
3. Version saved in localStorage
4. User thinks they're "training the algorithm"
5. In reality, they're just revealing pre-generated chaos

**File Structure**:
```
news_site/
├── app.py                 # Flask app
├── templates/
│   ├── base.html         # Newspaper design
│   ├── index.html        # Story list
│   └── story.html        # Story view + "Fit My Likes"
└── stories/              # Generated .md files
    ├── story_01_v00.md   # Mundane version
    ├── story_01_v01.md   # Slightly odd
    └── ...
```

### 3. **Story Generator Script** (`generate_news_stories.py`)

Batch generates multiple stories for the website:
- 10 different mundane topics
- Each with 10 progressive versions
- 100 story files total
- Automatically formatted for the website

## How to Use

### Quick Start (Test with Existing Story)

```bash
# 1. Copy the test story to website
python copy_test_story.py

# 2. Start the Flask server
cd news_site
python app.py

# 3. Open in browser
# http://localhost:5050
```

### Generate Full Content

```bash
# Generate 10 stories with 10 versions each
python generate_news_stories.py

# Start website
cd news_site
python app.py
```

### Generate Custom Story

```bash
python code_evolver/gradual_chaos_generator.py \
  --iterations 9 \
  --topic "your mundane topic here" \
  --temperature 0.93 \
  --model "gemma3:4b"
```

## The Village: Older Dailly

- **Location**: South Ayrshire, Scotland
- **Near**: A stile (local landmark)
- **Newspaper**: The Older Dailly Gazette
- **Established**: 1867
- **Circulation**: 847

## Technical Details

### Writer Personas (Randomly Selected)

Each story version uses a different writer for variety:
- Retired local journalist who loves community events
- Enthusiastic young reporter fresh out of journalism school
- Cynical veteran correspondent who's seen it all
- Poetic writer who finds beauty in everyday moments
- Practical, no-nonsense news writer who sticks to facts
- Eccentric columnist with a quirky writing style
- Former tabloid writer trying to write serious news
- Philosophical observer who sees deeper meaning

### Progressive Oddification System

Each level adds ONE new element:

1. **Level 0**: Pure mundane (parking debates, bus schedules)
2. **Level 1**: Slightly unusual but plausible detail
3. **Level 2**: Peculiar detail mentioned matter-of-factly
4. **Level 3**: Genuinely weird element as normal news
5. **Level 4**: Surreal detail (British sketch comedy inspired)
6. **Level 5**: Bizarre element - properly strange
7. **Level 6**: Completely absurd while maintaining tone
8. **Level 7**: Full absurdist territory
9. **Level 8**: Maximum nonsensical chaos

### Temperature Settings

- **0.85**: Base mundane story (still needs creativity)
- **0.88-0.93**: Progressive versions (high creativity)
- **0.95+**: Maximum chaos (if needed)

## localStorage Tracking

The website stores user "preferences":

```javascript
// Stored in browser
story-01-version: 5  // User has clicked "Fit My Likes" 5 times
story-02-version: 2  // 2 clicks on second story
```

When user returns:
- They see their selected version
- Think the site "remembers their preferences"
- Actually just revealing their chaos level

## Example Story Progression

**Version 0** (Mundane):
> "Older Dailly Parish Council held its monthly meeting last night, debating new parking restrictions around the High Street..."

**Version 3** (Getting Odd):
> "...the meeting took a decidedly odd turn when Mrs. Periwinkle presented photographic evidence of a scarlet rooster, inexplicably adorned with a miniature velvet robe, regularly perched atop the statue of Lord Bumble..."

**Version 7** (Full Chaos):
> "...someone shouted 'Right then, let's settle this with Numberwang!' and the entire council began humming the theme tune while the rooster performed what Mr. Bottomley described as 'a Ministry of Silly Walks'..."

## Files Created

```
mostlylucid.dse/
├── code_evolver/
│   ├── gradual_chaos_generator.py    # Main generator
│   └── gradual_chaos_output/         # Generated stories
│
├── news_site/
│   ├── app.py                        # Flask app
│   ├── requirements.txt              # Dependencies
│   ├── templates/
│   │   ├── base.html                 # Newspaper design
│   │   ├── index.html                # Story list
│   │   └── story.html                # Story + Fit My Likes
│   └── stories/                      # Story markdown files
│
├── generate_news_stories.py          # Batch story generator
├── copy_test_story.py                # Copy test story helper
├── NEWS_SITE_README.md               # Detailed documentation
└── SUMMARY.md                        # This file
```

## Dependencies

```bash
pip install Flask markdown requests
```

## Configuration

### Change Village Name
Edit templates: `base.html`, `story.html`

### Change Topics
Edit `MUNDANE_STARTERS` in `gradual_chaos_generator.py`

### Change Writer Styles
Edit `WRITER_PERSONAS` in `gradual_chaos_generator.py`

### Adjust Chaos Levels
Edit `ODDIFICATION_LEVELS` in `gradual_chaos_generator.py`

## Running Live

Currently running at: **http://localhost:5050**

To deploy:
```bash
pip install gunicorn
cd news_site
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## The Joke Explained

Users think they're using a modern "AI-powered personalization feature" that learns their preferences. In reality:

1. All versions are pre-generated
2. Each click just reveals the next level of weirdness
3. They're "training" nothing - just revealing chaos
4. localStorage makes it seem persistent and personalized
5. The formal news tone makes the absurdity funnier

It's a satire of:
- AI personalization hype
- "Fit to your preferences" algorithms
- Filter bubbles
- How recommendation systems actually work

But instead of radicalizing people, it just makes village news progressively sillier.

## Next Steps (Optional)

- [ ] Generate 50+ stories for full website
- [ ] Add "Reset My Preferences" button (resets to version 0)
- [ ] Add sharing feature (share your chaos level)
- [ ] Track stats (how weird did people go?)
- [ ] Add categories (Council, Events, Sport, etc.)
- [ ] Deploy to actual domain

## Test It Now

```bash
cd news_site
python app.py
```

Then open: http://localhost:5050

Click "Fit My Likes" repeatedly and watch the chaos unfold!

---

**Built with**: Flask, Ollama (gemma3:4b), Python, localStorage, and a love of absurdist British comedy.
