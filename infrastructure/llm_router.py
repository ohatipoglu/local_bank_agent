"""
LLM Router with OpenAI fallback support.
Routes requests to Ollama (primary) or OpenAI (fallback) based on availability.
"""

import asyncio
import os
from typing import Optional

import httpx
from core.logger import get_correlated_logger


class LLMRouter:
    """
    Intelligent LLM router with automatic fallback.

    Priority:
    1. Ollama (primary, local, free)
    2. OpenAI (fallback, cloud, paid)

    Features:
    - Automatic health checking
    - Configurable timeouts
    - Graceful degradation
    - Request/response logging

    Usage:
        router = LLMRouter()
        response = await router.chat(messages, model="gemma4:26B-32K")
    """

    def __init__(self, logger=None):
        """
        Initialize LLM router.

        Args:
            logger: Loguru logger instance
        """
        self.logger = logger or get_correlated_logger()
        self.ollama_base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.ollama_timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_timeout = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
        self.openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1536"))

        self._openai_client = None
        self._async_openai_client = None

        if self.openai_api_key:
            try:
                from openai import AsyncOpenAI, OpenAI

                self._openai_client = OpenAI(
                    api_key=self.openai_api_key, timeout=self.openai_timeout
                )
                self._async_openai_client = AsyncOpenAI(
                    api_key=self.openai_api_key, timeout=self.openai_timeout
                )
                self.logger.info("OpenAI clients initialized")
            except ImportError:
                self.logger.warning(
                    "openai package not installed. Run: pip install openai"
                )
            except Exception as e:
                self.logger.error(f"OpenAI client initialization error: {e}")
        else:
            self.logger.info(
                "OpenAI API key not set. OpenAI fallback disabled. "
                "Set OPENAI_API_KEY in .env to enable."
            )

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send chat request with automatic fallback.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (optional, uses default if not specified)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response

        Returns:
            AI response text

        Raises:
            RuntimeError: If all LLM providers fail
        """
        # Try Ollama first
        try:
            self.logger.debug("Attempting Ollama...")
            response = await self._chat_ollama(
                messages,
                model=model or os.getenv("LLM_MODEL_NAME", "gemma4:26B-32K"),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.logger.info("Ollama successful")
            return response

        except Exception as ollama_error:
            self.logger.warning(f"Ollama failed: {ollama_error}")

            # Fallback to OpenAI if available
            if self._async_openai_client:
                try:
                    self.logger.debug("Falling back to OpenAI...")
                    response = await self._chat_openai(
                        messages,
                        temperature=temperature,
                        max_tokens=max_tokens or self.openai_max_tokens,
                    )
                    self.logger.info("OpenAI fallback successful")
                    return response

                except Exception as openai_error:
                    self.logger.error(f"OpenAI also failed: {openai_error}")
                    raise RuntimeError(
                        f"Both LLM providers failed. "
                        f"Ollama: {ollama_error}, OpenAI: {openai_error}"
                    )
            else:
                self.logger.error("No fallback available (OpenAI not configured)")
                raise RuntimeError(f"LLM unavailable: {ollama_error}")

    async def _chat_ollama(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """
        Chat with Ollama API asynchronously.

        Args:
            messages: Chat messages
            model: Ollama model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            AI response text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                self.ollama_timeout, connect=10.0, read=self.ollama_timeout
            )
        ) as client:
            response = await client.post(f"{self.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            if "message" not in data:
                raise RuntimeError("Invalid Ollama response format")

            return data["message"]["content"]

    async def _chat_openai(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Chat with OpenAI API asynchronously.

        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            AI response text
        """
        if not self._async_openai_client:
            raise RuntimeError("Async OpenAI client not initialized")

        response = await self._async_openai_client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not response.choices or not response.choices[0].message:
            raise RuntimeError("Invalid OpenAI response format")

        return response.choices[0].message.content

    async def is_ollama_healthy(self) -> bool:
        """
        Check if Ollama API is healthy asynchronously.

        Returns:
            True if Ollama is reachable
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def is_openai_healthy(self) -> bool:
        """
        Check if OpenAI API is healthy.

        Returns:
            True if OpenAI is reachable
        """
        if not self._openai_client:
            return False

        try:
            # Simple model list call to test connectivity
            self._openai_client.models.list()
            return True
        except Exception:
            return False

    async def get_status(self) -> dict:
        """
        Get LLM router status asynchronously.

        Returns:
            Dictionary with provider status information
        """
        ollama_healthy, openai_healthy = await asyncio.gather(
            self.is_ollama_healthy(),
            asyncio.to_thread(self.is_openai_healthy),
        )
        return {
            "primary": {
                "name": "Ollama",
                "url": self.ollama_base_url,
                "healthy": ollama_healthy,
            },
            "fallback": {
                "name": "OpenAI",
                "configured": self.openai_api_key is not None,
                "model": self.openai_model,
                "healthy": openai_healthy,
            },
        }
