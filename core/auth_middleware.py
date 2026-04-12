"""
Authentication middleware for API endpoint protection.
Supports API key validation and CORS configuration.
"""

import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


class APIKeySecurity(APIKeyHeader):
    """API Key authentication scheme."""

    def __init__(self, *, name: str = "X-API-Key", auto_error: bool = False):
        super().__init__(name=name, auto_error=auto_error)


# API Key configuration - try Config first, fallback to env var
try:
    from core.config import Config

    API_KEY = Config.API_KEY if hasattr(Config, "API_KEY") else os.getenv("API_KEY")
except Exception:
    API_KEY = os.getenv("API_KEY")

if not API_KEY:
    API_KEY = None  # Ensure it's None, not empty string

API_KEY_HEADER = APIKeySecurity(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str | None = Depends(API_KEY_HEADER)) -> str | None:
    """
    Validate API key from request.
    Returns None if no API key is configured or if key matches.
    """
    if not API_KEY:
        return None  # No API key configured, allow all

    if api_key == API_KEY:
        return api_key

    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def setup_cors_middleware(app, origins: list[str] | None = None):
    """
    Configure CORS middleware with allowed origins.

    Args:
        app: FastAPI application instance
        origins: List of allowed origins (default: all for development)
    """
    if origins is None:
        # Default: allow all origins for development
        origins = os.getenv("CORS_ORIGINS", "*").split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
        max_age=3600,
    )


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for protecting sensitive endpoints.
    Skips authentication for public routes (/, /docs, /static, etc.).
    """

    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
        "/api/health",
    }

    PROTECTED_PATHS = {
        "/api/logs",
        "/api/session/stats",
        "/process_audio",
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip authentication for public paths
        if path in self.PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        # For protected paths, validate API key if configured
        if path in self.PROTECTED_PATHS and API_KEY:
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={
                        "status": "error",
                        "message": "Authentication required",
                        "detail": "Valid API key must be provided in X-API-Key header",
                    },
                )

        return await call_next(request)
