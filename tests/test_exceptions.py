"""
Tests for core exceptions module.
"""
import pytest
from core.exceptions import (
    LocalBankError,
    STTError,
    STTNoSpeechDetectedError,
    STTModelLoadError,
    TTSError,
    TTSClientNotInitializedError,
    AgentError,
    AgentInitializationError,
    AgentTimeoutError,
    ServiceError,
    ServiceUnavailableError,
    AuthenticationError,
    SessionError,
    ConfigurationError,
)


class TestExceptions:
    """Test custom exception hierarchy."""

    def test_base_exception(self):
        """Test LocalBankError is base exception."""
        with pytest.raises(LocalBankError):
            raise LocalBankError("Base error")

    def test_stt_exceptions(self):
        """Test STT exception hierarchy."""
        with pytest.raises(STTError):
            raise STTError("STT failed")

        with pytest.raises(STTNoSpeechDetectedError):
            raise STTNoSpeechDetectedError("No speech")

        with pytest.raises(STTModelLoadError):
            raise STTModelLoadError("Model load failed")

        # Verify inheritance
        assert issubclass(STTNoSpeechDetectedError, STTError)
        assert issubclass(STTModelLoadError, STTError)
        assert issubclass(STTError, LocalBankError)

    def test_tts_exceptions(self):
        """Test TTS exception hierarchy."""
        with pytest.raises(TTSError):
            raise TTSError("TTS failed")

        with pytest.raises(TTSClientNotInitializedError):
            raise TTSClientNotInitializedError("Client not initialized")

        assert issubclass(TTSClientNotInitializedError, TTSError)
        assert issubclass(TTSError, LocalBankError)

    def test_agent_exceptions(self):
        """Test Agent exception hierarchy."""
        with pytest.raises(AgentError):
            raise AgentError("Agent failed")

        with pytest.raises(AgentInitializationError):
            raise AgentInitializationError("Init failed")

        with pytest.raises(AgentTimeoutError):
            raise AgentTimeoutError("Timeout")

        assert issubclass(AgentInitializationError, AgentError)
        assert issubclass(AgentTimeoutError, AgentError)
        assert issubclass(AgentError, LocalBankError)

    def test_service_exceptions(self):
        """Test Service exception hierarchy."""
        with pytest.raises(ServiceError):
            raise ServiceError("Service failed")

        with pytest.raises(ServiceUnavailableError):
            raise ServiceUnavailableError("Service down")

        assert issubclass(ServiceUnavailableError, ServiceError)
        assert issubclass(ServiceError, LocalBankError)

    def test_auth_and_session_exceptions(self):
        """Test Auth and Session exceptions."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth failed")

        with pytest.raises(SessionError):
            raise SessionError("Session expired")

        assert issubclass(AuthenticationError, LocalBankError)
        assert issubclass(SessionError, LocalBankError)

    def test_exception_message(self):
        """Test exception message preservation."""
        msg = "Detailed error message"
        exc = STTError(msg)
        assert str(exc) == msg
