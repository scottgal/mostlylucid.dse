# Docker Deployment Guide

## Prerequisites

- Docker installed
- Docker Compose installed (optional, but recommended)
- Stories generated in `stories/` directory

## Quick Start

### 1. Generate Stories First

Before building the Docker image, you need stories:

```bash
# Generate test story
cd ..
python copy_test_story.py

# OR generate full content
cd news_site
python generate_content.py
# (Press Ctrl+C after it generates 10-20 stories)
```

### 2. Build the Docker Image

**Windows:**
```bash
build_docker.bat
```

**Linux/Mac:**
```bash
chmod +x build_docker.sh
./build_docker.sh
```

**Manual build:**
```bash
docker build -t older-dailly-gazette:latest .
```

### 3. Run the Container

**Using docker-compose (recommended):**
```bash
docker-compose up -d
```

**Using docker run:**
```bash
docker run -d -p 8080:8000 --name older-dailly-gazette older-dailly-gazette:latest
```

### 4. Access the Website

Open your browser to: **http://localhost:8080**

## Docker Commands

### View logs
```bash
docker-compose logs -f
```

### Stop the container
```bash
docker-compose down
```

### Restart the container
```bash
docker-compose restart
```

### Check container status
```bash
docker ps
```

## Saving and Sharing the Image

### Save to file
```bash
docker save older-dailly-gazette:latest | gzip > older-dailly-gazette.tar.gz
```

### Load on another machine
```bash
gunzip -c older-dailly-gazette.tar.gz | docker load
```

### Push to Docker Hub (optional)
```bash
# Tag the image
docker tag older-dailly-gazette:latest yourusername/older-dailly-gazette:latest

# Push to Docker Hub
docker push yourusername/older-dailly-gazette:latest
```

## Environment Variables

You can customize the deployment with environment variables:

```yaml
# docker-compose.yml
services:
  web:
    environment:
      - FLASK_ENV=production
      - PORT=8000  # Internal port (don't change)
```

## Port Configuration

The default configuration uses:
- **Internal**: Port 8000 (inside container)
- **External**: Port 8080 (on your host)

To change the external port, edit `docker-compose.yml`:

```yaml
ports:
  - "9000:8000"  # Access via http://localhost:9000
```

## Production Deployment

For production, consider:

1. **Reverse Proxy** (Nginx/Traefik):
```nginx
server {
    listen 80;
    server_name olderdailly.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **HTTPS with Let's Encrypt**:
```bash
# Use Traefik or Caddy for automatic HTTPS
```

3. **Resource Limits**:
```yaml
# docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## Updating Stories

To update stories in a running container:

1. **Stop the container:**
   ```bash
   docker-compose down
   ```

2. **Generate new stories:**
   ```bash
   python generate_content.py
   ```

3. **Rebuild and restart:**
   ```bash
   docker-compose up -d --build
   ```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs
```

### Port already in use

Change the external port in `docker-compose.yml`:
```yaml
ports:
  - "8081:8000"  # Use different port
```

### No stories visible

Ensure stories were generated before building:
```bash
ls stories/*.md
```

If empty, generate stories first, then rebuild.

### Permission errors

On Linux, ensure proper permissions:
```bash
chmod -R 755 stories/
```

## File Structure in Container

```
/app/
├── app.py              # Flask application
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   └── story.html
└── stories/           # Story markdown files
    ├── story_01_v00.md
    ├── story_01_v01.md
    └── ...
```

## Health Check

The container includes a health check that runs every 30 seconds:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' older-dailly-gazette
```

Possible statuses:
- `starting` - Container just started
- `healthy` - Working correctly
- `unhealthy` - Failed health checks

## Performance

The container uses:
- **Gunicorn** with 4 worker processes
- **Python 3.11-slim** base image (smaller size)
- **Non-root user** for security
- **Health checks** for reliability

Expected resource usage:
- Memory: ~200-300MB
- CPU: Minimal (<5% idle, <20% under load)
- Disk: ~100MB + stories (~1MB per 10 stories)

## Security Notes

- Container runs as non-root user (`appuser`)
- No unnecessary packages installed
- Debug mode disabled in production
- Health checks enabled

## Complete Example

```bash
# 1. Generate stories
python generate_content.py
# (Let it generate 20 stories, then Ctrl+C)

# 2. Build Docker image
./build_docker.bat  # Windows
./build_docker.sh   # Linux/Mac

# 3. Start with docker-compose
docker-compose up -d

# 4. Check it's running
docker-compose ps
docker-compose logs -f

# 5. Open browser
# http://localhost:8080

# 6. To stop
docker-compose down
```

## Sharing Your Build

To share the complete website (including all stories):

```bash
# Save image to file
docker save older-dailly-gazette:latest | gzip > older-dailly-gazette.tar.gz

# Share the .tar.gz file (will be ~100-200MB)

# On recipient's machine:
gunzip -c older-dailly-gazette.tar.gz | docker load
docker run -d -p 8080:8000 older-dailly-gazette:latest
```

---

**Built with Docker for easy deployment and sharing!**
