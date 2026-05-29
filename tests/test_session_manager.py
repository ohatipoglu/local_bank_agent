"""
Tests for session management module.
"""
import time

import pytest

import os
import shutil
import tempfile
from core.exceptions import AuthenticationError, SessionError
from core.session_manager_persistent import SQLiteSessionManager, SessionState


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
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "sessions_test.db")
        mgr = SQLiteSessionManager(db_path=db_path, ttl_seconds=60, max_sessions=10)
        yield mgr
        # Cleanup
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(mgr.close())
            else:
                loop.run_until_complete(mgr.close())
        except Exception:
            pass
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        """Test creating a new session."""
        session = await manager.create_session("sess-1")
        assert session.session_id == "sess-1"
        assert not session.is_authenticated

    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        """Test retrieving a session."""
        await manager.create_session("sess-1")
        session = await manager.get_session("sess-1")
        assert session is not None
        assert session.session_id == "sess-1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, manager):
        """Test retrieving a session that doesn't exist."""
        session = await manager.get_session("does-not-exist")
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session(self, manager):
        """Test deleting a session."""
        await manager.create_session("sess-1")
        assert await manager.delete_session("sess-1") is True
        assert await manager.get_session("sess-1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, manager):
        """Test deleting a session that doesn't exist."""
        assert await manager.delete_session("does-not-exist") is False

    @pytest.mark.asyncio
    async def test_session_max_limit(self):
        """Test maximum session limit enforcement."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "sessions_test.db")
        try:
            manager = SQLiteSessionManager(db_path=db_path, ttl_seconds=60, max_sessions=2)
            await manager.create_session("sess-1")
            await manager.create_session("sess-2")

            with pytest.raises(SessionError, match="Maximum session limit reached"):
                await manager.create_session("sess-3")
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_session_expiry_cleanup(self, manager):
        """Test expired session automatic cleanup."""
        await manager.create_session("sess-1")
        # Manually expire it in SQLite database
        async with manager._transaction() as conn:
            await conn.execute("UPDATE sessions SET last_accessed = ? WHERE session_id = ?", (time.time() - 120, "sess-1"))

        # Get should return None and clean up
        result = await manager.get_session("sess-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_session(self, manager, test_customer_id):
        """Test authenticating a session with customer ID."""
        await manager.create_session("sess-1")
        result = await manager.authenticate_session("sess-1", test_customer_id)
        assert result is True

        session = await manager.get_session("sess-1")
        assert session.is_authenticated is True
        assert session.customer_id == test_customer_id

    @pytest.mark.asyncio
    async def test_authenticate_invalid_session(self, manager, test_customer_id):
        """Test authenticating a non-existent session."""
        with pytest.raises(SessionError, match="Session not found"):
            await manager.authenticate_session("nonexistent", test_customer_id)

    @pytest.mark.asyncio
    async def test_authenticate_invalid_customer_id(self, manager):
        """Test authenticating with invalid customer ID."""
        await manager.create_session("sess-1")

        # Too short
        with pytest.raises(AuthenticationError):
            await manager.authenticate_session("sess-1", "123")

        # Non-numeric
        with pytest.raises(AuthenticationError):
            await manager.authenticate_session("sess-1", "abcdefghijk")

    @pytest.mark.asyncio
    async def test_update_context(self, manager):
        """Test updating conversation context."""
        await manager.create_session("sess-1")
        await manager.update_context("sess-1", "last_intent", "balance_inquiry")

        value = await manager.get_context("sess-1", "last_intent")
        assert value == "balance_inquiry"

    @pytest.mark.asyncio
    async def test_get_context_default(self, manager):
        """Test getting context with default value."""
        await manager.create_session("sess-1")
        value = await manager.get_context("sess-1", "missing_key", "default_value")
        assert value == "default_value"

    @pytest.mark.asyncio
    async def test_get_stats(self, manager, test_customer_id):
        """Test session statistics."""
        await manager.create_session("sess-1")
        await manager.create_session("sess-2")
        await manager.authenticate_session("sess-1", test_customer_id)

        stats = await manager.get_stats()
        assert stats["active_sessions"] == 2
        assert stats["authenticated_sessions"] == 1
        assert stats["max_sessions"] == 10
        assert stats["ttl_seconds"] == 60
