"""
Session management with TTL, customer identity binding, and conversation state.
Provides in-memory session storage with automatic expiration.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from core.exceptions import AuthenticationError, SessionError


@dataclass
class SessionState:
    """Represents the state of a single user session."""

    session_id: str
    customer_id: str | None = None
    is_authenticated: bool = False
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    conversation_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if session has exceeded TTL."""
        return (time.time() - self.last_accessed) > ttl_seconds

    def touch(self):
        """Update last accessed timestamp."""
        self.last_accessed = time.time()


class SessionManager:
    """
    Thread-safe session manager with TTL expiration.

    Stores sessions in memory with automatic cleanup of expired sessions.
    For production use, replace with Redis or database-backed sessions.
    """

    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str) -> SessionState:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier (UUID recommended)

        Returns:
            New SessionState instance

        Raises:
            SessionError: If maximum session limit reached
        """
        with self._lock:
            # Cleanup expired sessions first
            self._cleanup_expired()

            if len(self._sessions) >= self.max_sessions:
                raise SessionError(
                    f"Maximum session limit reached ({self.max_sessions}). "
                    "Please wait and try again."
                )

            session = SessionState(session_id=session_id)
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> SessionState | None:
        """
        Retrieve an existing session.

        Args:
            session_id: Session identifier

        Returns:
            SessionState if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if session.is_expired(self.ttl_seconds):
                del self._sessions[session_id]
                return None

            session.touch()
            return session

    def authenticate_session(self, session_id: str, customer_id: str) -> bool:
        """
        Bind a customer identity to a session.

        Args:
            session_id: Session identifier
            customer_id: Verified customer ID number (TC Kimlik)

        Returns:
            True if authentication successful

        Raises:
            SessionError: If session not found
            AuthenticationError: If customer ID validation fails
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionError(f"Session not found: {session_id}")

            if session.is_expired(self.ttl_seconds):
                del self._sessions[session_id]
                raise SessionError("Session expired")

            # Import and use TC Kimlik algorithmic validation
            from core.tc_kimlik_validator import validate_tc_kimlik

            if not customer_id or not validate_tc_kimlik(customer_id):
                raise AuthenticationError(
                    "Geçersiz TC Kimlik numarası. "
                    "11 haneli geçerli bir numara giriniz."
                )

            session.customer_id = customer_id
            session.is_authenticated = True
            session.touch()
            return True

    def update_context(self, session_id: str, key: str, value: Any):
        """
        Update conversation context data.

        Args:
            session_id: Session identifier
            key: Context key
            value: Context value
        """
        session = self.get_session(session_id)
        if session:
            session.conversation_context[key] = value

    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get conversation context data.

        Args:
            session_id: Session identifier
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        session = self.get_session(session_id)
        if session:
            return session.conversation_context.get(key, default)
        return default

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def _cleanup_expired(self):
        """Remove all expired sessions. Must be called within lock."""
        expired_ids = [
            sid
            for sid, session in self._sessions.items()
            if session.is_expired(self.ttl_seconds)
        ]
        for sid in expired_ids:
            del self._sessions[sid]

    def get_stats(self) -> dict[str, Any]:
        """
        Get session manager statistics.

        Returns:
            Dictionary with active_sessions, expired_sessions, etc.
        """
        with self._lock:
            self._cleanup_expired()
            return {
                "active_sessions": len(self._sessions),
                "max_sessions": self.max_sessions,
                "ttl_seconds": self.ttl_seconds,
                "authenticated_sessions": sum(
                    1 for s in self._sessions.values() if s.is_authenticated
                ),
            }


# Global session manager instance
session_manager = SessionManager()
