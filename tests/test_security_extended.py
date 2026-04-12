"""
Tests for security middleware and utilities.
"""

from core.security import sanitize_filename, sanitize_input


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_normal_filename(self):
        """Test normal filename is unchanged."""
        assert sanitize_filename("audio.wav") == "audio.wav"
        assert sanitize_filename("recording.mp3") == "recording.mp3"

    def test_path_traversal(self):
        """Test path traversal prevention."""
        assert sanitize_filename("../../etc/passwd") == "etcpasswd"
        assert sanitize_filename("..\\..\\windows\\system32") == "windowssystem32"
        assert sanitize_filename("/etc/passwd") == "etcpasswd"

    def test_special_characters(self):
        """Test special character removal."""
        assert sanitize_filename("file:name.txt") == "filename.txt"
        assert sanitize_filename("file<name>.txt") == "filename.txt"
        assert sanitize_filename('file"name.txt') == "filename.txt"

    def test_leading_dots(self):
        """Test leading dots removal."""
        assert sanitize_filename(".hidden.wav") == "hidden.wav"
        assert sanitize_filename("...audio.mp3") == "audio.mp3"

    def test_long_filename(self):
        """Test filename length limiting."""
        long_name = "a" * 300 + ".wav"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".wav")

    def test_empty_filename(self):
        """Test empty filename handling."""
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename("   ") == "unnamed_file"
        assert sanitize_filename("...") == "unnamed_file"

    def test_whitespace_handling(self):
        """Test whitespace trimming."""
        assert sanitize_filename("  audio.wav  ") == "audio.wav"
        assert sanitize_filename(". .audio.wav") == "audio.wav"


class TestSanitizeInput:
    """Test input sanitization."""

    def test_normal_input(self):
        """Test normal text is unchanged."""
        text = "Hello, world!"
        assert sanitize_input(text) == text

    def test_null_bytes(self):
        """Test null byte removal."""
        text = "Hello\x00World"
        assert "\x00" not in sanitize_input(text)

    def test_control_characters(self):
        """Test control character removal."""
        text = "Hello\x01\x02\x03World"
        result = sanitize_input(text)
        assert "\x01" not in result
        assert "\x02" not in result
        assert "\x03" not in result

    def test_newlines_and_tabs_preserved(self):
        """Test newlines and tabs are preserved."""
        text = "Line1\nLine2\tTab"
        result = sanitize_input(text)
        assert "\n" in result
        assert "\t" in result

    def test_max_length(self):
        """Test max length truncation."""
        text = "a" * 2000
        result = sanitize_input(text, max_length=100)
        assert len(result) <= 100

    def test_empty_input(self):
        """Test empty input handling."""
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""

    def test_whitespace_stripping(self):
        """Test leading/trailing whitespace removal."""
        assert sanitize_input("  hello  ") == "hello"
        assert sanitize_input("\n\ttext\n") == "text"


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting behavior."""
        from core.security import RateLimiter

        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # First 3 requests should be allowed
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True

        # 4th request should be denied
        assert limiter.is_allowed("client1") is False

    def test_different_clients(self):
        """Test rate limiting per client."""
        from core.security import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Client 1 uses their quota
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is False

        # Client 2 should still be allowed
        assert limiter.is_allowed("client2") is True

    def test_retry_after(self):
        """Test retry-after calculation."""
        from core.security import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Use up quota
        limiter.is_allowed("client1")

        # Should get positive retry-after value
        retry_after = limiter.get_retry_after("client1")
        assert retry_after > 0

        # Unknown client should get 0
        assert limiter.get_retry_after("unknown") == 0

    def test_window_expiration(self):
        """Test rate limit window expiration."""
        import time

        from core.security import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Use quota
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        assert limiter.is_allowed("client1") is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed("client1") is True

    def test_get_retry_after_unknown_client(self):
        """Test retry-after for unknown client."""
        from core.security import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.get_retry_after("nonexistent") == 0.0
