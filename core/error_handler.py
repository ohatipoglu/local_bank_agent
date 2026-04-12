"""
Structured error handling for the audio processing pipeline.
Provides user-friendly error messages and error categorization.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Categories of errors that can occur during audio processing."""

    STT_ERROR = "speech_to_text_error"
    AGENT_ERROR = "agent_processing_error"
    TTS_ERROR = "text_to_speech_error"
    AUDIO_VALIDATION_ERROR = "audio_validation_error"
    SESSION_ERROR = "session_error"
    AUTHENTICATION_ERROR = "authentication_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorCode(str, Enum):
    """Specific error codes within each category."""

    # STT errors
    NO_SPEECH_DETECTED = "no_speech_detected"
    AUDIO_FORMAT_UNSUPPORTED = "unsupported_audio_format"
    STT_MODEL_NOT_LOADED = "stt_model_not_loaded"
    TRANSCRIPTION_FAILED = "transcription_failed"

    # Agent errors
    AGENT_NOT_INITIALIZED = "agent_not_initialized"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    AGENT_TIMEOUT = "agent_timeout"
    INVALID_CUSTOMER_CONTEXT = "invalid_customer_context"

    # TTS errors
    ALL_ENGINES_FAILED = "all_tts_engines_failed"
    TTS_ENGINE_UNAVAILABLE = "tts_engine_unavailable"
    AUDIO_GENERATION_FAILED = "audio_generation_failed"

    # Audio validation errors
    FILE_TOO_LARGE = "file_too_large"
    INVALID_MIME_TYPE = "invalid_mime_type"
    CORRUPTED_AUDIO = "corrupted_audio"

    # Session errors
    SESSION_EXPIRED = "session_expired"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_LIMIT_REACHED = "session_limit_reached"

    # Authentication errors
    INVALID_TC_KIMLIK = "invalid_tc_kimlik"
    CUSTOMER_NOT_FOUND = "customer_not_found"
    AUTHENTICATION_REQUIRED = "authentication_required"

    # Timeout errors
    LLM_TIMEOUT = "llm_response_timeout"
    TTS_TIMEOUT = "tts_generation_timeout"
    OVERALL_TIMEOUT = "overall_processing_timeout"

    # Unknown
    INTERNAL_SERVER_ERROR = "internal_server_error"


@dataclass
class ProcessingError:
    """Structured error object for the audio processing pipeline."""

    category: ErrorCategory
    code: ErrorCode
    message_tr: str  # User-facing message in Turkish
    message_en: str  # Developer-facing message in English
    retryable: bool = True
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["category"] = self.category.value
        d["code"] = self.code.value
        return d


# ---------------------------------------------------------------------------
# Pre-defined error instances for common scenarios
# ---------------------------------------------------------------------------

# STT Errors
ERR_NO_SPEECH = ProcessingError(
    category=ErrorCategory.STT_ERROR,
    code=ErrorCode.NO_SPEECH_DETECTED,
    message_tr="Sesinizi duyamadık. Lütfen daha net konuşup tekrar deneyin.",
    message_en="No speech detected in audio",
    retryable=True,
)

ERR_STT_MODEL_NOT_LOADED = ProcessingError(
    category=ErrorCategory.STT_ERROR,
    code=ErrorCode.STT_MODEL_NOT_LOADED,
    message_tr="Konuşma tanıma modeli yüklenemedi. Lütfen sistem yöneticisine başvurun.",
    message_en="STT model not loaded",
    retryable=False,
)

ERR_TRANSCRIPTION_FAILED = ProcessingError(
    category=ErrorCategory.STT_ERROR,
    code=ErrorCode.TRANSCRIPTION_FAILED,
    message_tr="Ses metne çevrilemedi. Lütfen tekrar deneyin.",
    message_en="Transcription failed",
    retryable=True,
)

# Agent Errors
ERR_AGENT_TIMEOUT = ProcessingError(
    category=ErrorCategory.AGENT_ERROR,
    code=ErrorCode.AGENT_TIMEOUT,
    message_tr="Yanıt süresi doldu. Lütfen daha kısa bir soru sorun.",
    message_en="Agent response timeout",
    retryable=True,
)

ERR_AGENT_NOT_INITIALIZED = ProcessingError(
    category=ErrorCategory.AGENT_ERROR,
    code=ErrorCode.AGENT_NOT_INITIALIZED,
    message_tr="AI asistan başlatılamadı. Lütfen sistem yöneticisine başvurun.",
    message_en="Agent not initialized",
    retryable=False,
)

# TTS Errors
ERR_ALL_TTS_FAILED = ProcessingError(
    category=ErrorCategory.TTS_ERROR,
    code=ErrorCode.ALL_ENGINES_FAILED,
    message_tr="Ses üretilemedi. Ancak yanıt metin olarak gösterilebilir.",
    message_en="All TTS engines failed",
    retryable=True,
)

# Session Errors
ERR_SESSION_EXPIRED = ProcessingError(
    category=ErrorCategory.SESSION_ERROR,
    code=ErrorCode.SESSION_EXPIRED,
    message_tr="Oturum süresi doldu. Lütfen tekrar giriş yapın.",
    message_en="Session expired",
    retryable=True,
)

# Auth Errors
ERR_INVALID_TC = ProcessingError(
    category=ErrorCategory.AUTHENTICATION_ERROR,
    code=ErrorCode.INVALID_TC_KIMLIK,
    message_tr="Geçersiz TC Kimlik numarası. Lütfen 11 haneli numarayı kontrol edin.",
    message_en="Invalid TC Kimlik number",
    retryable=True,
)


def create_error_response(
    error: ProcessingError,
    partial_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a standardized error response for the audio processing pipeline.

    Args:
        error: ProcessingError instance
        partial_result: Optional partial results (e.g., transcription succeeded but TTS failed)

    Returns:
        Dictionary suitable for JSON response
    """
    response = {
        "status": "error",
        "error": error.to_dict(),
    }
    if partial_result:
        response["partial"] = partial_result
    return response


def create_success_response(
    user_text: str,
    ai_text: str,
    audio_base64: str = None,
    processing_times: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        user_text: Transcribed user input
        ai_text: AI agent response
        audio_base64: Base64-encoded audio (optional if TTS failed)
        processing_times: Timing breakdown for observability

    Returns:
        Dictionary suitable for JSON response
    """
    response = {
        "status": "success",
        "user_text": user_text,
        "ai_text": ai_text,
    }
    if audio_base64:
        response["audio_base64"] = audio_base64
    else:
        response["audio_available"] = False
    if processing_times:
        response["processing_times"] = processing_times
    return response
