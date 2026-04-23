"""
Tests for security module (rate limiter, input validation).
"""
import time
import pytest
from core.security import RateLimiter, validate_audio_upload
from unittest.mock import MagicMock


class TestRateLimiter:
    """Test RateLimiter sliding window algorithm."""

    def test_basic_rate_limiting(self):
        """Test basic request allowance."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False  # 4th request denied

    def test_different_clients_independent(self):
        """Test rate limiting is independent per client."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")
        assert limiter.is_allowed("client-1") is False

        # Different client should be allowed
        assert limiter.is_allowed("client-2") is True

    def test_window_expiry(self):
        """Test rate limit resets after window expires."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)

        assert limiter.is_allowed("client-1") is True
        assert limiter.is_allowed("client-1") is False

        # Wait for window to expire
        time.sleep(1.1)
        assert limiter.is_allowed("client-1") is True

    def test_retry_after(self):
        """Test retry-after calculation."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("client-1")

        retry_after = limiter.get_retry_after("client-1")
        assert retry_after > 0
        assert retry_after <= 60

    def test_retry_after_empty(self):
        """Test retry-after is 0 when no requests made."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        retry_after = limiter.get_retry_after("new-client")
        assert retry_after == 0.0


class TestValidateAudioUpload:
    """Test audio upload validation."""

    def test_valid_file(self):
        """Test valid audio file passes validation."""
        mock_file = MagicMock()
        mock_file.file = MagicMock()
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=1024 * 1024)  # 1 MB

        is_valid, error_msg = validate_audio_upload(mock_file, "audio.wav")
        assert is_valid is True
        assert error_msg == ""

    def test_file_too_large(self):
        """Test file exceeding size limit."""
        mock_file = MagicMock()
        mock_file.file = MagicMock()
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=15 * 1024 * 1024)  # 15 MB

        is_valid, error_msg = validate_audio_upload(mock_file, "audio.wav")
        assert is_valid is False
        assert "çok büyük" in error_msg

    def test_invalid_extension(self):
        """Test file with unsupported extension."""
        mock_file = MagicMock()
        mock_file.file = MagicMock()
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=1024)

        is_valid, error_msg = validate_audio_upload(mock_file, "document.pdf")
        assert is_valid is False
        assert "Desteklenmeyen dosya formatı" in error_msg

    def test_valid_extensions(self):
        """Test various valid audio extensions."""
        valid_files = ["audio.wav", "recording.webm", "voice.ogg", "sound.mp3"]

        for filename in valid_files:
            mock_file = MagicMock()
            mock_file.file = MagicMock()
            mock_file.file.seek = MagicMock()
            mock_file.file.tell = MagicMock(return_value=1024)

            is_valid, error_msg = validate_audio_upload(mock_file, filename)
            assert is_valid is True, f"Failed for {filename}"

    def test_no_filename(self):
        """Test validation when filename is None."""
        mock_file = MagicMock()
        mock_file.file = MagicMock()
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=1024)

        is_valid, error_msg = validate_audio_upload(mock_file, None)
        assert is_valid is True  # Should pass if only size check passes

    def test_file_without_extension(self):
        """Test file with no extension."""
        mock_file = MagicMock()
        mock_file.file = MagicMock()
        mock_file.file.seek = MagicMock()
        mock_file.file.tell = MagicMock(return_value=1024)

        is_valid, error_msg = validate_audio_upload(mock_file, "noextension")
        assert is_valid is False
        assert "Desteklenmeyen" in error_msg
