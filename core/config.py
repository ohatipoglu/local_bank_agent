"""
Application configuration with environment variable support and validation.
"""
import os
from typing import Optional
from pathlib import Path


class Config:
    """
    Centralized configuration class with environment variable overrides.
    
    All sensitive credentials should be provided via environment variables
    or .env files, NEVER hardcoded in source control.
    """

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = os.getenv("APP_NAME", "Local Bank AI Agent")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # -----------------------------------------------------------------------
    # Google Cloud TTS
    # -----------------------------------------------------------------------
    # CRITICAL: Never hardcode credential paths. Use environment variable.
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )

    # Fallback path for local development (should be in .env, not committed)
    if not GOOGLE_APPLICATION_CREDENTIALS:
        _project_root = Path(__file__).parent.parent
        _credential_file = "local-bank-tts-424c208f9a50.json"
        _credential_path = _project_root / _credential_file
        if _credential_path.exists():
            GOOGLE_APPLICATION_CREDENTIALS = str(_credential_path)
        else:
            GOOGLE_APPLICATION_CREDENTIALS = None

    # -----------------------------------------------------------------------
    # LLM Settings (Ollama)
    # -----------------------------------------------------------------------
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemma4:26B-32K")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1536"))

    # -----------------------------------------------------------------------
    # STT Settings (Faster-Whisper)
    # -----------------------------------------------------------------------
    STT_MODEL_SIZE: str = os.getenv("STT_MODEL_SIZE", "large-v3")
    STT_DEVICE: str = os.getenv("STT_DEVICE", "cpu")
    STT_COMPUTE_TYPE: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "tr")

    # -----------------------------------------------------------------------
    # TTS Settings
    # -----------------------------------------------------------------------
    TTS_LANGUAGE_CODE: str = os.getenv("TTS_LANGUAGE_CODE", "tr-TR")
    TTS_VOICE_NAME: str = os.getenv("TTS_VOICE_NAME", "tr-TR-Wavenet-D")
    TTS_MAX_RETRIES: int = int(os.getenv("TTS_MAX_RETRIES", "2"))
    TTS_TIMEOUT_SECONDS: float = float(os.getenv("TTS_TIMEOUT_SECONDS", "30.0"))

    # Use local Piper TTS as fallback?
    TTS_ENABLE_PIPER_FALLBACK: bool = os.getenv("TTS_ENABLE_PIPER_FALLBACK", "true").lower() == "true"
    PIPER_MODEL_PATH: str = os.getenv(
        "PIPER_MODEL_PATH",
        str(Path(__file__).parent.parent / "models" / "tr_TR-dfki-medium.onnx")
    )

    # -----------------------------------------------------------------------
    # Security
    # -----------------------------------------------------------------------
    MAX_AUDIO_SIZE_MB: int = int(os.getenv("MAX_AUDIO_SIZE_MB", "10"))
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # -----------------------------------------------------------------------
    # Session Management
    # -----------------------------------------------------------------------
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))  # 1 hour

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_JSON_FORMAT: bool = os.getenv("LOG_JSON_FORMAT", "false").lower() == "true"

    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate critical configuration values.
        Returns a list of validation errors (empty if all valid).
        """
        errors = []

        if not cls.GOOGLE_APPLICATION_CREDENTIALS:
            errors.append(
                "GOOGLE_APPLICATION_CREDENTIALS not set. "
                "Set environment variable or place credential JSON in project root."
            )
        elif not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
            errors.append(
                f"Google credentials file not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}"
            )

        if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
            errors.append("LLM_TEMPERATURE must be between 0 and 2")

        if cls.MAX_AUDIO_SIZE_MB > 50:
            errors.append("MAX_AUDIO_SIZE_MB should not exceed 50 MB for security")

        return errors

    @classmethod
    def print_summary(cls):
        """Print configuration summary for startup verification."""
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
        print(f"  Piper Fallback: {'Enabled' if cls.TTS_ENABLE_PIPER_FALLBACK else 'Disabled'}")
        print(f"  Rate Limit: {cls.RATE_LIMIT_REQUESTS} req / {cls.RATE_LIMIT_WINDOW_SECONDS}s")
        print(f"  Max Audio: {cls.MAX_AUDIO_SIZE_MB} MB")
        print("=" * 60 + "\n")
