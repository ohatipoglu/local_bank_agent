"""
Models endpoint v1 - List available LLM models.
"""

import httpx
from fastapi import APIRouter

from core.config import Config
from core.logger import get_correlated_logger

router = APIRouter()
log = get_correlated_logger()


@router.get("/models")
async def get_models():
    """
    List available Ollama models dynamically.

    Queries Ollama's local API for installed models.
    Falls back to configured default model if Ollama is unreachable.
    """
    try:
        timeout_val = float(Config.LLM_TIMEOUT_SECONDS) if hasattr(Config, "LLM_TIMEOUT_SECONDS") else 180.0
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_val, connect=60.0)
        ) as client:
            response = await client.get(f"{Config.LLM_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                if not models:
                    models = [Config.LLM_MODEL_NAME]
                return {"status": "success", "models": models}
            else:
                return {
                    "status": "error",
                    "message": "Ollama API'sine ulaşılamadı.",
                    "models": [Config.LLM_MODEL_NAME],
                }
    except Exception as e:
        log.error(f"Ollama Model Listesi Alınamadı: {e}")
        return {
            "status": "error",
            "message": str(e),
            "models": [Config.LLM_MODEL_NAME],
        }
