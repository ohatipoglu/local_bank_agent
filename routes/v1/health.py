"""
Health check endpoint v1.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict


@router.get("/health", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for v1 API.

    Returns system health status including all component states.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {},
    }
