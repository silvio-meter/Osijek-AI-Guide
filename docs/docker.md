# Docker Setup Guide for Lega API

This document explains how to run the Osijek AI Guide (Lega) backend using Docker.

## Prerequisites

- macOS, Linux, or Windows
- At least 4GB RAM free (recommended 8GB+ because of LLM dependencies)

## Step 1: Install Docker Desktop (macOS)

On macOS, the easiest and official way is **Docker Desktop**.

### Installation

1. Go to the official download page:
   https://www.docker.com/products/docker-desktop/

2. Download **Docker Desktop for Mac** (choose Apple Silicon / M1/M2/M3/M4 if you have a MacBook Pro with Apple chip, otherwise Intel version).

3. Open the downloaded `.dmg` file and drag Docker to your Applications folder.

4. Launch Docker Desktop from Applications (or Spotlight).

5. Follow the onboarding wizard. It may ask for permissions and to install additional tools.

6. Wait until Docker Desktop says **"Docker Desktop is running"** in the bottom left.

### Verify Installation

Open Terminal and run:

```bash
docker --version
docker compose version
```

You should see version numbers. If you get `command not found`, restart your terminal or log out/in.

---

## Step 2: Prepare Environment Variables

The API needs at least the `XAI_API_KEY`.

Create a `.env` file in the project root (if you don't have one yet):

```bash
cp .env.example .env 2>/dev/null || true
```

Or manually create `.env` with at least:

```env
XAI_API_KEY=sk-...your-key-here...

# Optional but recommended for production
JWT_SECRET_KEY=change-this-to-a-long-random-string-in-production

# Optional - only needed for live event fallback
TAVILY_API_KEY=...
```

---

## Step 3: Run with Docker Compose

From the project root:

```bash
# Build images (first time or after changes)
docker compose build --no-cache

# Start the API
docker compose up
```

The API will be available at:
- http://localhost:8000
- Swagger docs: http://localhost:8000/docs

To run in background:

```bash
docker compose up -d
```

To stop:

```bash
docker compose down
```

---

## Development vs Production

The current `docker-compose.yml` uses the `development` target by default (with `--reload`).

To switch to production image:

Edit `docker-compose.yml` and change:

```yaml
target: development
```

to

```yaml
target: production
```

Then rebuild:

```bash
docker compose build
docker compose up
```

---

## Common Issues on macOS

### "docker: command not found"

- Make sure Docker Desktop is running (look for the whale icon in the menu bar).
- Restart your terminal after installing Docker Desktop.
- On some systems you may need to add Docker to PATH manually.

### Permission errors when writing to data/

The containers run as a non-root user inside. The volume mount should still work on macOS because Docker Desktop handles permissions well.

If you see permission problems:

```bash
chmod -R 777 data/
```

(Only do this in development.)

### Slow builds

The first build can take 5–15 minutes because it installs heavy dependencies (`langchain`, `chromadb`, `lxml`, etc.).

Subsequent builds are much faster thanks to layer caching.

---

## Running Without Docker (Fallback)

If you don't want to use Docker right now, you can still run the app locally:

```bash
pip install -r requirements.txt

# Make sure .env is set
PYTHONPATH=src uvicorn src.api:app --reload --port 8000
```

---

## Next Steps

Once Docker is working, you can proceed with:

- Day 5 of Tjedan 6 (Deployment preparation)
- Setting up a real deployment target (Railway, Fly.io, VPS, etc.)

Let us know if you hit any specific error after installing Docker Desktop!