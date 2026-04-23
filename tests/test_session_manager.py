"""
Tests for session management module.
"""
import time
import pytest
from core.session_manager import SessionManager, SessionState
from core.exceptions import SessionError, AuthenticationError


class TestSessionState:
    """Test SessionState dataclass."""

    def test_create_session(self):
        """Test session creation with defaults."""
        session = SessionState(session_id="test-123")
        assert session.session_id == "test-123"
        assert session.customer_id is None
        assert session.is_authenticated is False
        assert session.conversation_context == {}

    def test_session_expiry(self):
        """Test session expiration check."""
        session = SessionState(session_id="test-123")
        assert not session.is_expired(ttl_seconds=3600)

        # Manually set old timestamp
        session.last_accessed = time.time() - 7200
        assert session.is_expired(ttl_seconds=3600)

    def test_session_touch(self):
        """Test session touch updates timestamp."""
        session = SessionState(session_id="test-123")
        old_time = session.last_accessed
        time.sleep(0.1)
        session.touch()
        assert session.last_accessed > old_time


class TestSessionManager:
    """Test SessionManager operations."""

    @pytest.fixture
    def manager(self):
        """Create a fresh session manager."""
        return SessionManager(ttl_seconds=60, max_sessions=10)

    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create_session("sess-1")
        assert session.session_id == "sess-1"
        assert not session.is_authenticated

    def test_get_session(self, manager):
        """Test retrieving a session."""
        manager.create_session("sess-1")
        session = manager.get_session("sess-1")
        assert session is not None
        assert session.session_id == "sess-1"

    def test_get_nonexistent_session(self, manager):
        """Test retrieving a session that doesn't exist."""
        session = manager.get_session("does-not-exist")
        assert session is None

    def test_delete_session(self, manager):
        """Test deleting a session."""
        manager.create_session("sess-1")
        assert manager.delete_session("sess-1") is True
        assert manager.get_session("sess-1") is None

    def test_delete_nonexistent_session(self, manager):
        """Test deleting a session that doesn't exist."""
        assert manager.delete_session("does-not-exist") is False

    def test_session_max_limit(self):
        """Test maximum session limit enforcement."""
        manager = SessionManager(ttl_seconds=60, max_sessions=2)
        manager.create_session("sess-1")
        manager.create_session("sess-2")

        with pytest.raises(SessionError, match="Maximum session limit reached"):
            manager.create_session("sess-3")

    def test_session_expiry_cleanup(self, manager):
        """Test expired session automatic cleanup."""
        session = manager.create_session("sess-1")
        # Manually expire it
        session.last_accessed = time.time() - 120

        # Get should return None and clean up
        result = manager.get_session("sess-1")
        assert result is None

    def test_authenticate_session(self, manager, test_customer_id):
        """Test authenticating a session with customer ID."""
        manager.create_session("sess-1")
        result = manager.authenticate_session("sess-1", test_customer_id)
        assert result is True

        session = manager.get_session("sess-1")
        assert session.is_authenticated is True
        assert session.customer_id == test_customer_id

    def test_authenticate_invalid_session(self, manager, test_customer_id):
        """Test authenticating a non-existent session."""
        with pytest.raises(SessionError, match="Session not found"):
            manager.authenticate_session("nonexistent", test_customer_id)

    def test_authenticate_invalid_customer_id(self, manager):
        """Test authenticating with invalid customer ID."""
        manager.create_session("sess-1")

        # Too short
        with pytest.raises(AuthenticationError):
            manager.authenticate_session("sess-1", "123")

        # Non-numeric
        with pytest.raises(AuthenticationError):
            manager.authenticate_session("sess-1", "abcdefghijk")

    def test_update_context(self, manager):
        """Test updating conversation context."""
        manager.create_session("sess-1")
        manager.update_context("sess-1", "last_intent", "balance_inquiry")
        
        value = manager.get_context("sess-1", "last_intent")
        assert value == "balance_inquiry"

    def test_get_context_default(self, manager):
        """Test getting context with default value."""
        manager.create_session("sess-1")
        value = manager.get_context("sess-1", "missing_key", "default_value")
        assert value == "default_value"

    def test_get_stats(self, manager, test_customer_id):
        """Test session statistics."""
        manager.create_session("sess-1")
        manager.create_session("sess-2")
        manager.authenticate_session("sess-1", test_customer_id)

        stats = manager.get_stats()
        assert stats["active_sessions"] == 2
        assert stats["authenticated_sessions"] == 1
        assert stats["max_sessions"] == 10
        assert stats["ttl_seconds"] == 60
