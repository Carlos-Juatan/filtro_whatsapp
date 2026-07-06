"""
FastAPI application entrypoint for the Extrator e Filtro de P&R (Local) tool.

Responsibilities:
  - Instantiate the FastAPI app with metadata and lifecycle hooks.
  - Register all API routers under the /api prefix.
  - Register global exception handlers for consistent JSON error responses.
  - Mount the compiled Vite/React frontend static assets.
  - Provide a catch-all GET route to serve index.html for client-side routing.

Single-container design: FastAPI serves both the REST/WebSocket API on /api/*
and the pre-built React SPA static files, all on port 8100.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("filtro_whatsapp")

# ──────────────────────────────────────────────────────────────────────────────
# Frontend dist path (resolved relative to this file's location)
# In production Docker image, the Vite build is copied to /app/frontend/dist
# ──────────────────────────────────────────────────────────────────────────────

_HERE = Path(__file__).resolve().parent
_FRONTEND_DIST = _HERE.parent.parent.parent / "frontend" / "dist"

# ──────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown hooks)
# ──────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifecycle: startup → yield → shutdown."""
    logger.info("🚀 Filtro de P&R (Local) starting up…")
    # Future: initialize persistent storage directories here.
    yield
    logger.info("🛑 Filtro de P&R (Local) shutting down…")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI instance
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Extrator e Filtro de P&R (Local)",
    description=(
        "Local single-user tool for uploading text files, chunking them via tiktoken, "
        "processing with the OpenAI API, and exporting consolidated Q&A pairs."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────────────────────────────────────
# CORS middleware (development only – same-origin in production)
# When running `npm run dev` on :5100, it proxies /api to :8100; no CORS needed.
# This middleware is safe to keep: it only matters during local vite dev server usage.
# ──────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5100", "http://127.0.0.1:5100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Global exception handlers
# ──────────────────────────────────────────────────────────────────────────────


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Return 400 with the error message for any unhandled ValueError."""
    logger.warning("ValueError at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    """Return 404 for resource-not-found KeyErrors raised in service layer."""
    logger.warning("KeyError at %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": f"Resource not found: {exc}"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return 500 for any other unhandled exception."""
    logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Check server logs for details."},
    )


# ──────────────────────────────────────────────────────────────────────────────
# API Routers  (imported lazily to avoid import errors before sub-modules exist)
# ──────────────────────────────────────────────────────────────────────────────

def _register_routers() -> None:
    """
    Import and mount all API routers.

    Each router module lives under src/api/routes/ and exports an `APIRouter`
    named `router`.  Import errors for any individual router are caught and
    logged so the application can still start during incremental development.
    """
    router_specs = [
        # (module_path, prefix, tags)
        ("src.api.routes.keys", "/api/keys", ["API Keys"]),
        ("src.api.routes.prompts", "/api/prompts", ["Prompts"]),
    ]

    for module_path, prefix, tags in router_specs:
        try:
            import importlib

            module = importlib.import_module(module_path)
            app.include_router(module.router, prefix=prefix, tags=tags)
            logger.info("Router registered: %s → %s", module_path, prefix)
        except ModuleNotFoundError:
            logger.warning(
                "Router module '%s' not found yet – will be registered once implemented.",
                module_path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to register router '%s': %s", module_path, exc, exc_info=True)

    # WebSocket router is registered separately (no prefix duplication)
    try:
        import importlib

        ws_module = importlib.import_module("src.api.websocket")
        app.include_router(ws_module.router, tags=["Processing WebSocket"])
        logger.info("WebSocket router registered.")
    except ModuleNotFoundError:
        logger.warning("WebSocket module 'src.api.websocket' not found yet.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to register WebSocket router: %s", exc, exc_info=True)


_register_routers()


# ──────────────────────────────────────────────────────────────────────────────
# Static file serving (production build)
# ──────────────────────────────────────────────────────────────────────────────

if _FRONTEND_DIST.exists():
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        logger.info("Serving frontend assets from %s", assets_dir)


# ──────────────────────────────────────────────────────────────────────────────
# Health-check endpoint
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/api/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    """Returns 200 OK when the application is running."""
    return {"status": "ok", "version": app.version}


# ──────────────────────────────────────────────────────────────────────────────
# React SPA catch-all (must come LAST so /api/* routes are matched first)
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/{catchall:path}", include_in_schema=False)
async def serve_react_app(catchall: str) -> FileResponse:
    """
    Serve the React SPA index.html for any path not matched by an API route.
    Required for client-side routing (React Router / TanStack Router) to work
    when a user refreshes a deep link.
    """
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))

    # Fallback during development (frontend not yet built)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": (
                "Frontend build not found. "
                "Run `npm run build` inside the frontend/ directory "
                "or use the Vite dev server on port 5100."
            )
        },
    )
