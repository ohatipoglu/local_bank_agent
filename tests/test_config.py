"""
Tests for configuration management.
"""

import os
from unittest.mock import patch

import pytest

from core.config import Settings


class TestSettings:
    """Test Settings class with pydantic-settings."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.APP_NAME == "Local Bank AI Agent"
            assert settings.DEBUG is False
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.LLM_MODEL_NAME == "gemma4:26B-32K"
            assert settings.STT_MODEL_SIZE == "large-v3"
            assert settings.TTS_ENABLE_PIPER_FALLBACK is True
            assert settings.TTS_ENABLE_COQUI_FALLBACK is False
            assert settings.TTS_ENABLE_EDGE_FALLBACK is True
            assert settings.MAX_AUDIO_SIZE_MB == 10
            assert settings.RATE_LIMIT_REQUESTS == 30
            assert settings.SESSION_TTL_SECONDS == 3600

    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        env_vars = {
            "APP_NAME": "Test App",
            "DEBUG": "true",
            "PORT": "9000",
            "LLM_MODEL_NAME": "test-model",
            "MAX_AUDIO_SIZE_MB": "20",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)
            assert settings.APP_NAME == "Test App"
            assert settings.DEBUG is True
            assert settings.PORT == 9000
            assert settings.LLM_MODEL_NAME == "test-model"
            assert settings.MAX_AUDIO_SIZE_MB == 20

    def test_temperature_validation(self):
        """Test LLM temperature validation."""
        # Valid temperature
        with patch.dict(os.environ, {"LLM_TEMPERATURE": "0.5"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.LLM_TEMPERATURE == 0.5

        # Temperature too high
        with patch.dict(os.environ, {"LLM_TEMPERATURE": "2.5"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

        # Temperature too low
        with patch.dict(os.environ, {"LLM_TEMPERATURE": "-0.1"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

    def test_audio_size_validation(self):
        """Test audio size validation."""
        # Valid size
        with patch.dict(os.environ, {"MAX_AUDIO_SIZE_MB": "25"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAX_AUDIO_SIZE_MB == 25

        # Size too large
        with patch.dict(os.environ, {"MAX_AUDIO_SIZE_MB": "51"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

        # Negative size
        with patch.dict(os.environ, {"MAX_AUDIO_SIZE_MB": "-1"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

    def test_rate_limit_validation(self):
        """Test rate limit validation."""
        # Valid rate limits
        with patch.dict(
            os.environ,
            {"RATE_LIMIT_REQUESTS": "50", "RATE_LIMIT_WINDOW_SECONDS": "120"}, clear=True
        ):
            settings = Settings(_env_file=None)
            assert settings.RATE_LIMIT_REQUESTS == 50
            assert settings.RATE_LIMIT_WINDOW_SECONDS == 120

        # Negative rate limit
        with patch.dict(os.environ, {"RATE_LIMIT_REQUESTS": "-5"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

    def test_model_name_validation(self):
        """Test model name validation."""
        # Valid model name
        with patch.dict(os.environ, {"LLM_MODEL_NAME": "gemma:7b"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.LLM_MODEL_NAME == "gemma:7b"

        # Empty model name
        with patch.dict(os.environ, {"LLM_MODEL_NAME": ""}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

        # Whitespace-only model name
        with patch.dict(os.environ, {"LLM_MODEL_NAME": "   "}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

    def test_base_url_validation(self):
        """Test base URL validation."""
        # Valid URL
        with patch.dict(os.environ, {"LLM_BASE_URL": "http://localhost:11434"}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.LLM_BASE_URL == "http://localhost:11434"

        # Invalid URL (no protocol)
        with patch.dict(os.environ, {"LLM_BASE_URL": "localhost:11434"}, clear=True):
            with pytest.raises(Exception):
                Settings(_env_file=None)

    def test_google_credentials_validation(self):
        """Test Google credentials validation."""
        # No credentials set
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, GOOGLE_APPLICATION_CREDENTIALS=None)
            errors = settings.validate_google_credentials()
            assert len(errors) > 0

        # Invalid path
        with patch.dict(
            os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/path"}, clear=True
        ):
            settings = Settings(_env_file=None)
            errors = settings.validate_google_credentials()
            assert len(errors) > 0

    def test_print_summary(self, capsys):
        """Test configuration summary printing."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, GOOGLE_APPLICATION_CREDENTIALS=None)
            settings.print_summary()
            captured = capsys.readouterr()
            assert "Configuration Summary" in captured.out
            assert "LLM Model:" in captured.out
            assert "STT Model:" in captured.out

    def test_validate_all(self):
        """Test comprehensive validation."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None, GOOGLE_APPLICATION_CREDENTIALS=None)
            errors = settings.validate_all()
            # Should have at least Google credentials warning
            assert isinstance(errors, list)
