# =============================================================================
# Osijek AI Guide - Lega API (FastAPI)
# Production-ready Dockerfile
# =============================================================================

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (needed for some Python packages like lxml, chromadb, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Dependencies stage (better layer caching)
# =============================================================================
FROM base as dependencies

COPY requirements.txt .

# Install only the packages needed for the API (we can trim later if wanted)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# =============================================================================
# Development target (only used when explicitly building with --target development)
# =============================================================================
FROM dependencies as development

RUN pip install watchdog  # optional for better reload

# We mount the code in docker-compose for hot reload
CMD uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000} --reload

# =============================================================================
# Production stage (LAST stage = default for Railway, Fly.io, etc.)
# =============================================================================
FROM dependencies as production

# Create non-root user for security
RUN groupadd -r lega && useradd -r -g lega lega

# Copy application code
COPY --chown=lega:lega src/ ./src/
COPY --chown=lega:lega data/ ./data/

# Ensure data subdirectories exist (will be owned by root for now)
RUN mkdir -p /app/data/user_profiles \
             /app/data/chat_history \
             /app/data/tool_usage \
             /app/data/feedback

# NOTE: Running as root for now because of Railway volume permission issues.
# We can switch back to non-root user later with a proper entrypoint.
# USER lega

# Expose the port
EXPOSE 8000

# Healthcheck - more tolerant for Railway cold starts
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Production command - respects Railway's $PORT variable
# Explicit log level + access logs for better visibility of errors in Railway
CMD uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info --access-log