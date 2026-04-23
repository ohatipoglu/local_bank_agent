"""
Tests for LLM router with OpenAI fallback.
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

from infrastructure.llm_router import LLMRouter


@pytest.fixture
def mock_ollama_response():
    return {
        "model": "gemma4:26B-32K",
        "message": {
            "role": "assistant",
            "content": "Merhaba! Size nasıl yardımcı olabilirim?",
        },
    }


@pytest.fixture
def mock_openai_response():
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="Hello! How can I help you?"))
    ]
    return mock_response


@pytest.fixture
def messages():
    return [
        {"role": "system", "content": "You are a helpful banking assistant."},
        {"role": "user", "content": "Merhaba"},
    ]


class TestLLMRouter:
    """Test LLM router functionality."""

    def test_router_initialization_with_openai(self):
        """Test router initializes with OpenAI configured."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"), patch("openai.AsyncOpenAI"):
                router = LLMRouter()
                assert router.openai_api_key == "test-key"
                assert router._openai_client is not None
                assert router._async_openai_client is not None

    def test_router_initialization_without_openai(self):
        """Test router initializes without OpenAI."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
            router = LLMRouter()
            assert not router.openai_api_key
            assert router._openai_client is None
            assert router._async_openai_client is None

    @pytest.mark.asyncio
    @patch("infrastructure.llm_router.LLMRouter._chat_ollama")
    async def test_chat_ollama_success(self, mock_chat_ollama, messages):
        """Test successful Ollama chat."""
        mock_chat_ollama.return_value = "Test response from Ollama"

        router = LLMRouter()
        result = await router.chat(messages, model="gemma4:26B-32K")

        assert result == "Test response from Ollama"
        mock_chat_ollama.assert_called_once()

    @pytest.mark.asyncio
    @patch("infrastructure.llm_router.LLMRouter._chat_openai")
    @patch("infrastructure.llm_router.LLMRouter._chat_ollama")
    async def test_chat_fallback_to_openai(self, mock_chat_ollama, mock_chat_openai, messages):
        """Test fallback to OpenAI when Ollama fails."""
        # Ollama fails
        mock_chat_ollama.side_effect = Exception("Ollama unavailable")

        # OpenAI succeeds
        mock_chat_openai.return_value = "OpenAI response"

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"), patch("openai.AsyncOpenAI"):
                router = LLMRouter()
                result = await router.chat(messages)

                assert result == "OpenAI response"
                assert mock_chat_ollama.called
                mock_chat_openai.assert_called_once()

    @pytest.mark.asyncio
    @patch("infrastructure.llm_router.LLMRouter._chat_ollama")
    async def test_chat_ollama_failure_no_fallback(self, mock_chat_ollama, messages):
        """Test error when Ollama fails and no fallback configured."""
        mock_chat_ollama.side_effect = Exception("Ollama unavailable")

        router = LLMRouter()

        with pytest.raises(RuntimeError, match="LLM unavailable"):
            await router.chat(messages)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_is_ollama_healthy_success(self, mock_get):
        """Test Ollama health check success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        router = LLMRouter()
        result = await router.is_ollama_healthy()
        assert result is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_is_ollama_healthy_failure(self, mock_get):
        """Test Ollama health check failure."""
        mock_get.side_effect = Exception("Connection refused")

        router = LLMRouter()
        result = await router.is_ollama_healthy()
        assert result is False

    @patch("openai.OpenAI")
    @patch("openai.AsyncOpenAI")
    def test_is_openai_healthy_success(self, mock_async_openai, mock_openai):
        """Test OpenAI health check success."""
        mock_client = Mock()
        mock_client.models.list.return_value = []
        mock_openai.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            router = LLMRouter()
            assert router.is_openai_healthy() is True

    @patch("openai.OpenAI")
    @patch("openai.AsyncOpenAI")
    def test_is_openai_healthy_failure(self, mock_async_openai, mock_openai):
        """Test OpenAI health check failure."""
        mock_client = Mock()
        mock_client.models.list.side_effect = Exception("API error")
        mock_openai.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            router = LLMRouter()
            assert router.is_openai_healthy() is False

    @pytest.mark.asyncio
    @patch("infrastructure.llm_router.LLMRouter.is_ollama_healthy", new_callable=AsyncMock)
    @patch("infrastructure.llm_router.LLMRouter.is_openai_healthy")
    async def test_get_status(self, mock_is_openai_healthy, mock_is_ollama_healthy):
        """Test status endpoint."""
        mock_is_ollama_healthy.return_value = True
        mock_is_openai_healthy.return_value = True

        router = LLMRouter()
        status = await router.get_status()

        assert "primary" in status
        assert "fallback" in status
        assert status["primary"]["name"] == "Ollama"
        assert status["fallback"]["name"] == "OpenAI"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_chat_with_temperature(self, mock_post, messages):
        """Test chat with custom temperature."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"}
        }
        mock_post.return_value = mock_response

        router = LLMRouter()
        await router._chat_ollama(
            messages,
            model="gemma4:26B-32K",
            temperature=0.8,
            max_tokens=None
        )

        # Verify temperature was passed correctly
        call_args = mock_post.call_args
        assert call_args[1]["json"]["options"]["temperature"] == 0.8

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_chat_with_max_tokens(self, mock_post, messages):
        """Test chat with custom max tokens."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"}
        }
        mock_post.return_value = mock_response

        router = LLMRouter()
        await router._chat_ollama(
            messages,
            model="gemma4:26B-32K",
            temperature=0.1,
            max_tokens=500
        )

        # Verify max_tokens was passed correctly
        call_args = mock_post.call_args
        assert call_args[1]["json"]["options"]["num_predict"] == 500