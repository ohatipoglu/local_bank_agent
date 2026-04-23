"""
Application configuration with environment variable support and validation.
Uses pydantic-settings for automatic validation and type coercion.
"""

import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized configuration class with automatic validation.

    All sensitive credentials should be provided via environment variables
    or .env files, NEVER hardcoded in source control.
    """

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = "Local Bank AI Agent"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # -----------------------------------------------------------------------
    # CORS & Security
    # -----------------------------------------------------------------------
    CORS_ORIGINS: str = "*"
    API_KEY: str | None = None
    ALLOWED_HOSTS: str = "*"

    # -----------------------------------------------------------------------
    # Google Cloud TTS
    # -----------------------------------------------------------------------
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None

    # -----------------------------------------------------------------------
    # LLM Settings (Ollama)
    # -----------------------------------------------------------------------
    LLM_MODEL_NAME: str = "gemma4:26B-32K"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_TIMEOUT_SECONDS: int = 180
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1536

    # -----------------------------------------------------------------------
    # STT Settings (Faster-Whisper)
    # -----------------------------------------------------------------------
    STT_MODEL_SIZE: str = "large-v3"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_LANGUAGE: str = "tr"

    # -----------------------------------------------------------------------
    # TTS Settings
    # -----------------------------------------------------------------------
    TTS_LANGUAGE_CODE: str = "tr-TR"
    TTS_VOICE_NAME: str = "tr-TR-Wavenet-D"
    TTS_MAX_RETRIES: int = 2
    TTS_TIMEOUT_SECONDS: float = 30.0

    # Use local Piper TTS as fallback?
    TTS_ENABLE_PIPER_FALLBACK: bool = True
    PIPER_MODEL_PATH: str = "./models/tr_TR-dfki-medium.onnx"

    # Coqui XTTS v2 (local, high-quality Turkish TTS with GPU support)
    TTS_ENABLE_COQUI_FALLBACK: bool = False
    COQUI_MODEL_NAME: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    COQUI_VOICE_REF_AUDIO: str = "./models/coqui_reference.wav"
    COQUI_SPEAKER_WAV: str = ""
    COQUI_USE_GPU: bool = True

    # Edge TTS (Microsoft Edge online TTS, free, no API key)
    TTS_ENABLE_EDGE_FALLBACK: bool = True
    EDGE_TTS_VOICE: str = "tr-TR-AhmetNeural"

    # -----------------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------------
    MAX_AUDIO_SIZE_MB: int = 10
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------
    SESSION_TTL_SECONDS: int = 3600  # 1 hour

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    LOG_LEVEL: str = "DEBUG"
    LOG_JSON_FORMAT: bool = False

    # -----------------------------------------------------------------------
    # Monitoring & Metrics (Prometheus)
    # -----------------------------------------------------------------------
    ENABLE_PROMETHEUS: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v):
        if v:
            v = str(v).strip()
            if not v or v.startswith("#"):
                return None
        return v

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("LLM_TEMPERATURE must be between 0 and 2")
        return v

    @field_validator("MAX_AUDIO_SIZE_MB")
    @classmethod
    def validate_audio_size(cls, v):
        if v > 50:
            raise ValueError("MAX_AUDIO_SIZE_MB should not exceed 50 MB for security")
        if v <= 0:
            raise ValueError("MAX_AUDIO_SIZE_MB must be positive")
        return v

    @field_validator("RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW_SECONDS")
    @classmethod
    def validate_rate_limits(cls, v):
        if v <= 0:
            raise ValueError("Rate limit values must be positive")
        return v

    @field_validator("LLM_MODEL_NAME")
    @classmethod
    def validate_model_name(cls, v):
        if not v or not v.strip():
            raise ValueError("LLM_MODEL_NAME cannot be empty")
        return v.strip()

    @field_validator("LLM_BASE_URL")
    @classmethod
    def validate_base_url(cls, v):
        if not v or not v.strip():
            raise ValueError("LLM_BASE_URL cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("LLM_BASE_URL must start with http:// or https://")
        return v.strip()

    def validate_google_credentials(self) -> list[str]:
        """
        Validate Google Cloud credentials.
        Returns a list of validation errors (empty if all valid).
        """
        errors = []

        if not self.GOOGLE_APPLICATION_CREDENTIALS:
            errors.append(
                "GOOGLE_APPLICATION_CREDENTIALS not set. "
                "Set environment variable or place credential JSON in project root."
            )
        elif not os.path.exists(self.GOOGLE_APPLICATION_CREDENTIALS):
            errors.append(
                f"Google credentials file not found: {self.GOOGLE_APPLICATION_CREDENTIALS}"
            )

        return errors

    def validate_all(self) -> list[str]:
        """
        Run all validation checks including Pydantic and custom validations.
        Returns list of validation errors (empty if all valid).
        """
        errors = []

        # Pydantic validation is automatic on instantiation
        # Additional custom validations
        errors.extend(self.validate_google_credentials())

        return errors

    def print_summary(self):
        """Print configuration summary for startup verification."""
        print("\n" + "=" * 60)
        print(f"  {self.APP_NAME} - Configuration Summary")
        print("=" * 60)

        errors = self.validate_all()
        if errors:
            print("\n  ⚠️  Configuration Warnings:")
            for error in errors:
                print(f"    - {error}")
        else:
            print("\n  ✅ All critical configuration values validated.")

        print(f"\n  LLM Model: {self.LLM_MODEL_NAME}")
        print(f"  STT Model: {self.STT_MODEL_SIZE} ({self.STT_DEVICE})")
        print(f"  TTS Voice: {self.TTS_VOICE_NAME}")
        print(
            f"  Piper Fallback: {'Enabled' if self.TTS_ENABLE_PIPER_FALLBACK else 'Disabled'}"
        )
        print(
            f"  Coqui XTTS:   {'Enabled' if self.TTS_ENABLE_COQUI_FALLBACK else 'Disabled'}"
        )
        print(
            f"  Edge TTS:     {'Enabled' if self.TTS_ENABLE_EDGE_FALLBACK else 'Disabled'}"
        )
        print(
            f"  Rate Limit: {self.RATE_LIMIT_REQUESTS} req / {self.RATE_LIMIT_WINDOW_SECONDS}s"
        )
        print(f"  Max Audio: {self.MAX_AUDIO_SIZE_MB} MB")
        print(f"  API Key: {'Configured' if self.API_KEY else 'Not set'}")
        print(f"  CORS: {self.CORS_ORIGINS}")
        print("=" * 60 + "\n")


# Backward compatibility alias - creates instance on import
# This maintains compatibility with existing code that imports Config
try:
    Config = Settings()
except Exception as e:
    # Fallback for environments where pydantic-settings isn't available yet
    print(f"⚠️  Warning: pydantic-settings not available, using fallback: {e}")

    class Config:
        """Fallback configuration class without pydantic-settings."""

        APP_NAME: str = os.getenv("APP_NAME", "Local Bank AI Agent")
        DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        HOST: str = os.getenv("HOST", "0.0.0.0")
        PORT: int = int(os.getenv("PORT", "8000"))

        CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
        API_KEY: str | None = os.getenv("API_KEY")
        if API_KEY:
            API_KEY = API_KEY.strip()
            if not API_KEY or API_KEY.startswith("#"):
                API_KEY = None
        ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "*")

        GOOGLE_APPLICATION_CREDENTIALS: str | None = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

        if not GOOGLE_APPLICATION_CREDENTIALS:
            _project_root = Path(__file__).parent.parent
            _credential_file = "local-bank-tts-424c208f9a50.json"
            _credential_path = _project_root / _credential_file
            if _credential_path.exists():
                GOOGLE_APPLICATION_CREDENTIALS = str(_credential_path)

        LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemma4:26B-32K")
        LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))
        LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1536"))

        STT_MODEL_SIZE: str = os.getenv("STT_MODEL_SIZE", "large-v3")
        STT_DEVICE: str = os.getenv("STT_DEVICE", "cpu")
        STT_COMPUTE_TYPE: str = os.getenv("STT_COMPUTE_TYPE", "int8")
        STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "tr")

        TTS_LANGUAGE_CODE: str = os.getenv("TTS_LANGUAGE_CODE", "tr-TR")
        TTS_VOICE_NAME: str = os.getenv("TTS_VOICE_NAME", "tr-TR-Wavenet-D")
        TTS_MAX_RETRIES: int = int(os.getenv("TTS_MAX_RETRIES", "2"))
        TTS_TIMEOUT_SECONDS: float = float(os.getenv("TTS_TIMEOUT_SECONDS", "30.0"))
        TTS_ENABLE_PIPER_FALLBACK: bool = (
            os.getenv("TTS_ENABLE_PIPER_FALLBACK", "true").lower() == "true"
        )
        PIPER_MODEL_PATH: str = os.getenv(
            "PIPER_MODEL_PATH",
            str(Path(__file__).parent.parent / "models" / "tr_TR-dfki-medium.onnx"),
        )

        TTS_ENABLE_COQUI_FALLBACK: bool = (
            os.getenv("TTS_ENABLE_COQUI_FALLBACK", "false").lower() == "true"
        )
        COQUI_MODEL_NAME: str = os.getenv(
            "COQUI_MODEL_NAME", "tts_models/multilingual/multi-dataset/xtts_v2"
        )
        COQUI_VOICE_REF_AUDIO: str = os.getenv(
            "COQUI_VOICE_REF_AUDIO",
            str(Path(__file__).parent.parent / "models" / "coqui_reference.wav"),
        )
        COQUI_SPEAKER_WAV: str = os.getenv("COQUI_SPEAKER_WAV", "")
        COQUI_USE_GPU: bool = os.getenv("COQUI_USE_GPU", "true").lower() == "true"

        TTS_ENABLE_EDGE_FALLBACK: bool = (
            os.getenv("TTS_ENABLE_EDGE_FALLBACK", "true").lower() == "true"
        )
        EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "tr-TR-AhmetNeural")

        MAX_AUDIO_SIZE_MB: int = int(os.getenv("MAX_AUDIO_SIZE_MB", "10"))
        RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
        RATE_LIMIT_WINDOW_SECONDS: int = int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
        )

        SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

        LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
        LOG_JSON_FORMAT: bool = os.getenv("LOG_JSON_FORMAT", "false").lower() == "true"

        @classmethod
        def validate(cls) -> list[str]:
            errors = []
            if not cls.GOOGLE_APPLICATION_CREDENTIALS:
                errors.append("GOOGLE_APPLICATION_CREDENTIALS not set.")
            elif not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
                errors.append(
                    f"Google credentials file not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}"
                )
            if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
                errors.append("LLM_TEMPERATURE must be between 0 and 2")
            if cls.MAX_AUDIO_SIZE_MB > 50:
                errors.append("MAX_AUDIO_SIZE_MB should not exceed 50 MB")
            return errors

        @classmethod
        def validate_all(cls) -> list[str]:
            return cls.validate()

        @classmethod
        def print_summary(cls):
            print("\n" + "=" * 60)
            print(f"  {cls.APP_NAME} - Configuration Summary")
            print("=" * 60)
            errors = cls.validate()
            if errors:
                print("\n  ⚠️  Configuration Warnings:")
                for error in errors:
                    print(f"    - {error}")
            else:
                print("\n  ✅ All critical configuration values validated.")
            print(f"\n  LLM Model: {cls.LLM_MODEL_NAME}")
            print(f"  STT Model: {cls.STT_MODEL_SIZE} ({cls.STT_DEVICE})")
            print(f"  TTS Voice: {cls.TTS_VOICE_NAME}")
            print(
                f"  Piper Fallback: {'Enabled' if cls.TTS_ENABLE_PIPER_FALLBACK else 'Disabled'}"
            )
            print(
                f"  Coqui XTTS:   {'Enabled' if cls.TTS_ENABLE_COQUI_FALLBACK else 'Disabled'}"
            )
            print(
                f"  Edge TTS:     {'Enabled' if cls.TTS_ENABLE_EDGE_FALLBACK else 'Disabled'}"
            )
            print(
                f"  Rate Limit: {cls.RATE_LIMIT_REQUESTS} req / {cls.RATE_LIMIT_WINDOW_SECONDS}s"
            )
            print(f"  Max Audio: {cls.MAX_AUDIO_SIZE_MB} MB")
            print(f"  API Key: {'Configured' if cls.API_KEY else 'Not set'}")
            print("=" * 60 + "\n")
