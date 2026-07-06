# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Frontend builder
# Builds the React/Vite SPA and outputs compiled static assets to /frontend/dist
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy dependency manifests first for layer caching
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies (ci for reproducible builds)
RUN npm ci --prefer-offline

# Copy the rest of the frontend source
COPY frontend/ ./

# Build production bundle into ./dist
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python dependency installer (wheel cache layer)
# Installs Python packages into a virtual environment for easy copying
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS python-deps

WORKDIR /install

# Install system build dependencies needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Install into a dedicated venv so we can copy the whole env cleanly
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Final runtime image
# Lean Python image that contains:
#   - The pre-built Python virtualenv from stage 2
#   - The FastAPI backend source
#   - The compiled React SPA from stage 1 (served by FastAPI StaticFiles)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy the virtualenv from the deps stage
COPY --from=python-deps /opt/venv /opt/venv

# Copy backend source
COPY --chown=appuser:appuser backend/ ./backend/

# Copy compiled frontend assets from frontend-builder stage
# FastAPI serves them from backend/src/main.py via StaticFiles + catch-all route
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./frontend/dist

# Persistent volume mount point for configuration files
# (API keys and prompt configs are stored here via key_storage.py / prompt_storage.py)
RUN mkdir -p /app/data && chown appuser:appuser /app/data
VOLUME ["/app/data"]

# Activate virtualenv in PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data

# Switch to non-root user
USER appuser

# Expose the single service port
EXPOSE 8100

# Health-check: poll the /api/health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/api/health')" || exit 1

# Uvicorn serves the FastAPI app; workers=1 (single-user local tool)
CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]
