# Deployment Guide – Osijek AI Guide (Lega API)

This document explains how to deploy the Lega backend to production.

## Current State (Tjedan 6)

- The application is fully dockerized
- We have a working `Dockerfile` with separate `development` and `production` targets
- Health endpoint exists at `/health`
- SQLite is used for now (easy to migrate later)

---

## Recommended Deployment Options

| Platform     | Difficulty | Cost     | Recommendation                  | Notes |
|--------------|------------|----------|----------------------------------|-------|
| **Railway**  | Very Easy  | Low      | **Best choice for solo devs**   | Easiest experience |
| **Fly.io**   | Easy       | Low      | Very good                        | Great performance |
| **VPS**      | Medium     | Low–Med  | Good if you want full control    | DigitalOcean, Hetzner, etc. |
| Render       | Easy       | Low      | Acceptable                       | Simpler than VPS |

**Recommendation for most people:** Start with **Railway**.

---

## 1. Quickest Deployment: Railway (Recommended)

Railway is currently the easiest platform for this project.

### Steps

1. Go to [railway.app](https://railway.app) and sign in with GitHub.

2. Click **"New Project"** → **"Deploy from GitHub repo"**.

3. Connect your repository.

4. Railway will detect the `Dockerfile`.

5. Add the required environment variables:
   - `XAI_API_KEY`
   - `JWT_SECRET_KEY` (generate a strong one!)
   - `ENVIRONMENT=production`
   - `TAVILY_API_KEY` (optional)

6. After setting the variables, click **"Deploy"** (or the Redeploy button) at the top.

Railway will automatically provide the `PORT` environment variable. Our Dockerfile is configured to respect it (`${PORT:-8000}`).

**Important:** Make sure you have the latest `Dockerfile` and `railway.toml` pushed to GitHub before deploying. The production stage must be the last stage in the Dockerfile.

### After Setting Variables (Important)

Once you have added the variables:

1. Click the **Deploy** button (top right) to trigger a new build.
2. Go to the **Deployments** tab and watch the build logs.
3. When it says "Deployment is live", copy the public URL.

### Useful Railway Tips

- Always click **Deploy** after changing environment variables.
- You can add a custom domain later.
- Railway has a generous free tier for small projects.
- Check the "Logs" tab if the app doesn't start.

---

## 2. Deployment using Docker (Fly.io / VPS)

### Production Docker Image

We already support a production target:

```bash
docker build --target production -t lega-api .
```

### docker-compose for Production

See `docker-compose.prod.yml` (create one based on the example below).

### Environment Variables for Production

Always set these:

```env
ENVIRONMENT=production
JWT_SECRET_KEY=<strong-random-string>
XAI_API_KEY=<your-real-key>
TAVILY_API_KEY=<optional>
```

**Never** use the default development JWT key in production.

---

## 3. Database Strategy

### Current: SQLite (Fine for small/medium usage)

- Works great with Docker volumes
- Simple and fast to start
- Limitation: Not great for high concurrency or multiple replicas

### Recommended for Production: PostgreSQL

When you need more scale, migrate to Postgres.

**Migration path:**
1. Add a PostgreSQL service (Railway/Fly.io make this easy)
2. Change `src/database.py` to use `postgresql://...`
3. Use Alembic or manual migrations

For now (Tjedan 6), SQLite + volume is acceptable.

---

## Production Recommendations

### 1. Use the production target

In `docker-compose.prod.yml` (or your platform settings):

```yaml
services:
  api:
    build:
      context: .
      target: production
```

### 2. Run with multiple workers (when using gunicorn)

For production, consider switching from pure uvicorn to gunicorn + uvicorn workers:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api:app --bind 0.0.0.0:8000
```

Add `gunicorn` to requirements if you go this route.

### 3. Logging

Currently we use basic logging. In production you should consider:
- Structured logging
- Sending logs to a service (Railway/Fly.io have built-in log viewers)

### 4. Secrets Management

- Never commit real keys
- Use your platform's secret management
- Rotate `JWT_SECRET_KEY` if it ever leaks

---

## Example: docker-compose.prod.yml (Template)

```yaml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: lega-api-prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - XAI_API_KEY=${XAI_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY:-}
    volumes:
      - lega-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  lega-data:
```

---

## Checklist Before Going Live

- [ ] `JWT_SECRET_KEY` is strong and different from development
- [ ] `ENVIRONMENT=production`
- [ ] `XAI_API_KEY` is set
- [ ] You are using the `production` Docker target
- [ ] Database is being persisted (volume or managed DB)
- [ ] You have monitoring / logs access
- [ ] `/health` endpoint returns 200

---

## Next Steps (After Tjedan 6)

- Set up proper logging + error tracking (Sentry)
- Add rate limiting per user more aggressively in production
- Consider moving to PostgreSQL + Alembic
- Add CI/CD (GitHub Actions) for automatic deployments

---

## Need Help?

If you get stuck on a specific platform (Railway, Fly.io, etc.), paste the error here and we'll fix it together.

**Current recommended path for solo development:**
1. Deploy to Railway (fastest)
2. Later move to Fly.io or self-hosted VPS if needed

Good luck with deployment! 🚀
