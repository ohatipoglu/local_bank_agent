"""
Custom exception types for consistent error handling across the application.
"""


class LocalBankError(Exception):
    """Base exception for all Local Bank application errors."""
    pass


class STTError(LocalBankError):
    """Speech-to-Text conversion errors."""
    pass


class STTNoSpeechDetectedError(STTError):
    """No speech detected in audio input."""
    pass


class STTModelLoadError(STTError):
    """Failed to load STT model."""
    pass


class TTSError(LocalBankError):
    """Text-to-Speech generation errors."""
    pass


class TTSClientNotInitializedError(TTSError):
    """TTS client was not properly initialized."""
    pass


class AgentError(LocalBankError):
    """AI agent processing errors."""
    pass


class AgentInitializationError(AgentError):
    """Failed to initialize agent."""
    pass


class AgentTimeoutError(AgentError):
    """Agent processing timed out."""
    pass


class ServiceError(LocalBankError):
    """Backend service operation errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Required service is not available."""
    pass


class AuthenticationError(LocalBankError):
    """Authentication/authorization errors."""
    pass


class SessionError(LocalBankError):
    """Session management errors."""
    pass


class ConfigurationError(LocalBankError):
    """Configuration loading errors."""
    pass
