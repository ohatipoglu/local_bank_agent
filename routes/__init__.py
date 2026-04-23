"""
API Routes v1

Versioned API endpoints for backward compatibility.
All new endpoints should be added under /api/v1/
"""

from fastapi import APIRouter

from routes.v1 import audio, auth, health, models

api_v1_router = APIRouter(prefix="/api/v1")

# Include v1 routers
api_v1_router.include_router(audio.router, prefix="/audio", tags=["Audio Processing"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(models.router, tags=["Models"])

__all__ = ["api_v1_router"]
