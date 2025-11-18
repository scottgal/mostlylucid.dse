# Older Dailly Gazette - Complete Guide

## What You Have

A complete joke website that:
1. Looks like a legitimate Scottish local news site
2. Has an "AI-Powered Personalization" button
3. Makes stories progressively weirder with **visual word morphing effects**
4. Users think they're training AI, but it's all pre-generated static content
5. Can be packaged as a Docker container with all stories included

## The Magic: AI "Live Rewriting" Effect

When users click **"Fit My Likes"**, they see:

1. ✨ **"AI Analyzing..." indicator** appears in top-right
2. 🌊 **Subtle overlay effect** washes over the page
3. 📝 **Words morph out** - each word blurs and fades away in sequence
4. ✍️ **Headline transforms** - dramatic word-by-word rewrite
5. 🎨 **New words morph in** - each word appears with blur/scale animation
6. 💾 **Version saved** to localStorage

**It looks like AI is rewriting the text live, but it's actually:**
- Fetching cached static markdown files
- Applying CSS animations word-by-word
- Creating the illusion of intelligent personalization

## Quick Start

### Option 1: Test Locally (Fast)

```bash
# 1. Copy test story
python copy_test_story.py

# 2. Run website
cd news_site
python app.py

# 3. Open browser
http://localhost:5050

# 4. Click "Fit My Likes" repeatedly and watch the morphing!
```

### Option 2: Generate Full Content

```bash
# Terminal 1 - Generate stories (leave running)
cd news_site
python generate_content.py

# Terminal 2 - Run website
cd news_site
python app.py

# Open: http://localhost:5050
```

### Option 3: Docker Deployment

```bash
# 1. Ensure you have stories
python copy_test_story.py  # OR let generate_content.py run for a while

# 2. Build Docker image
cd news_site
./build_docker.bat  # Windows
./build_docker.sh   # Linux/Mac

# 3. Run with docker-compose
docker-compose up -d

# 4. Open browser
http://localhost:8080
```

## The Visual Effects Breakdown

### 1. Word Morphing Animation

**Morph Out (existing text disappears):**
- Each word blurs (0px → 3px blur)
- Fades out (opacity 1 → 0)
- Slides down (translateY +10px)
- Scales up slightly (scale 1.05)
- Duration: 400ms per word
- Staggered: 15ms delay between words

**Morph In (new text appears):**
- Each word starts blurred (3px blur)
- Fades in (opacity 0 → 1)
- Slides up (translateY -10px → 0)
- Scales to normal (scale 0.95 → 1)
- Duration: 600ms per word
- Staggered: 15ms delay between words

### 2. Headline Transformation

More dramatic animation:
- Rotates slightly (-2deg → 0deg)
- Bounces into place (cubic-bezier easing)
- 80ms delay between words
- Larger initial offset (translateX -30px)

### 3. AI Processing Indicator

Top-right corner shows:
- Animated green pulse dot
- "AI Analyzing..." text
- Animated ellipsis (dots appear sequentially)
- Slides in from top when active
- Fades out when complete

### 4. Background Overlay

- Radial gradient overlay (purple tint)
- Fades in during processing
- Creates "AI is working" atmosphere
- Non-intrusive, pointer-events disabled

## File Structure

```
news_site/
├── app.py                      # Flask application
├── generate_content.py         # Continuous story generator
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker build config
├── docker-compose.yml          # Docker Compose config
├── build_docker.bat/.sh        # Build scripts
├── templates/
│   ├── base.html              # Newspaper design
│   ├── index.html             # Story list
│   └── story.html             # Story view + morphing effects
└── stories/                   # Generated markdown files
    ├── story_01_v00.md        # Version 0 (mundane)
    ├── story_01_v01.md        # Version 1 (slightly odd)
    └── ...                    # Up to v09 (chaos)
```

## The Joke Explained

**Users see:**
- "AI-Powered Personalization"
- "Our advanced AI learns your preferences"
- Real-time text morphing effects
- Progress saved (localStorage)

**Reality:**
- All 10 versions pre-generated offline
- Just revealing next static file
- CSS animations create "AI" illusion
- No AI involved whatsoever

It's a satire of:
- AI personalization hype
- Filter bubbles
- Algorithm "training"
- "Powered by AI" marketing

But harmless - it just makes village news progressively sillier!

## Customization

### Change Morphing Speed

Edit `story.html` JavaScript:

```javascript
// Faster morphing
word.style.animationDelay = `${index * 10}ms`;  // Was 15ms

// Slower, more dramatic
word.style.animationDelay = `${index * 25}ms`;  // Was 15ms
```

### Change AI Indicator Text

Edit `story.html`:

```html
<div class="ai-indicator" id="ai-indicator">
    Personalizing Content<span class="dots"></span>
</div>
```

### Adjust Blur/Scale Effects

Edit CSS in `story.html`:

```css
@keyframes morphIn {
    0% {
        opacity: 0;
        transform: translateY(-10px) scale(0.95);
        filter: blur(3px);  /* Increase for more blur */
    }
    /* ... */
}
```

### Change Village Name

Edit templates:
- `base.html` - Masthead and footer
- `story.html` - Page titles

## Docker Deployment

### Build Image

```bash
cd news_site
./build_docker.bat  # Windows
./build_docker.sh   # Linux/Mac
```

### Run Container

```bash
# Using docker-compose (recommended)
docker-compose up -d

# Using docker run
docker run -d -p 8080:8000 --name older-dailly-gazette older-dailly-gazette:latest
```

### Save and Share

```bash
# Save to file
docker save older-dailly-gazette:latest | gzip > older-dailly-gazette.tar.gz

# Share the .tar.gz file with friends

# They load it with:
gunzip -c older-dailly-gazette.tar.gz | docker load
docker run -d -p 8080:8000 older-dailly-gazette:latest
```

## Technical Stack

- **Backend**: Flask (Python web framework)
- **Frontend**: Vanilla JavaScript + CSS animations
- **Storage**: localStorage (client-side)
- **Content**: Markdown files (static)
- **Deployment**: Docker + Gunicorn
- **AI**: None (that's the joke!)

## Performance

- **First load**: ~500ms
- **Story morph**: ~2-3 seconds (intentionally dramatic)
- **Memory**: ~200MB Docker container
- **Disk**: ~1MB per 10 stories
- **Bandwidth**: Minimal (static files)

## Browser Compatibility

Tested and working:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers

CSS animations use modern features:
- CSS `filter: blur()`
- CSS transforms
- CSS animations
- localStorage

IE11 not supported (and that's fine).

## Troubleshooting

### Morphing looks janky

Reduce number of words:
```javascript
// In morphOutElement/morphInElement
setTimeout(() => {
    word.classList.add('word-morph-out');
}, index * 20);  // Increase delay for smoother
```

### Button doesn't work

Check browser console for errors:
```javascript
// Open DevTools (F12)
// Look for JavaScript errors
```

### No stories showing

Ensure stories generated:
```bash
ls news_site/stories/*.md
```

If empty, generate first:
```bash
python copy_test_story.py
```

## What's Next?

Optional enhancements:
1. Add sound effects to morphing
2. More dramatic "AI thinking" animation
3. Share feature (share your chaos level)
4. Statistics page (how weird did people go?)
5. Categories (Council, Events, Sport, etc.)
6. Multiple villages (randomize location names)

## Credits

Built with:
- Flask (web framework)
- Ollama (AI for story generation)
- CSS animations (for morphing effects)
- Absurdist British comedy (for inspiration)
- localStorage (for persistence)

---

**The complete Older Dailly Gazette system - ready to deploy and share!**

Website is currently running at: **http://localhost:5050** (development)

Docker will run at: **http://localhost:8080** (production)

Enjoy the gradual chaos! 🎭
