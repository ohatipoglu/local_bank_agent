"""
Persistent session management with SQLite storage.
Provides session persistence across server restarts with TTL expiration.

This replaces the in-memory SessionManager for production use.
The in-memory version is still available at core.session_manager for dev/testing.
"""

import json
import os
import sqlite3
import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from typing import Any
import aiosqlite

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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["conversation_context"] = json.dumps(d["conversation_context"])
        d["metadata"] = json.dumps(d["metadata"])
        return d

    @staticmethod
    def from_row(row: dict[str, Any]) -> "SessionState":
        """Create SessionState from database row."""
        return SessionState(
            session_id=row["session_id"],
            customer_id=row.get("customer_id"),
            is_authenticated=bool(row.get("is_authenticated", 0)),
            created_at=float(row.get("created_at", time.time())),
            last_accessed=float(row.get("last_accessed", time.time())),
            conversation_context=json.loads(row.get("conversation_context", "{}")),
            metadata=json.loads(row.get("metadata", "{}")),
        )


class SQLiteSessionManager:
    """
    Thread-safe session manager with SQLite persistence and TTL expiration.

    Sessions survive server restarts. Expired sessions are automatically
    cleaned up on access.

    Usage:
        session_mgr = SQLiteSessionManager(db_path="sessions.db")
        session = await session_mgr.create_session("unique-id")
        await session_mgr.authenticate_session("unique-id", "12345678901")
    """

    # SQL schema for sessions table
    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        customer_id TEXT,
        is_authenticated INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        last_accessed REAL NOT NULL,
        conversation_context TEXT DEFAULT '{}',
        metadata TEXT DEFAULT '{}'
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed
    ON sessions(last_accessed);

    CREATE INDEX IF NOT EXISTS idx_sessions_customer_id
    ON sessions(customer_id);
    """

    def __init__(
        self,
        db_path: str = None,
        ttl_seconds: int = 3600,
        max_sessions: int = 10000,
    ):
        """
        Initialize SQLite session manager.

        Args:
            db_path: Path to SQLite database file (default: sessions.db in project root)
            ttl_seconds: Session time-to-live in seconds (default: 1 hour)
            max_sessions: Maximum active sessions (default: 10000)

        Raises:
            SessionError: If database cannot be initialized
        """
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "data", "sessions.db")

        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._lock = asyncio.Lock()

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_db_sync()

    def _init_db_sync(self):
        """Initialize database schema synchronously."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.executescript(self._SCHEMA)
            conn.commit()
        finally:
            conn.close()

    @asynccontextmanager
    async def _transaction(self):
        """Async context manager for database transactions."""
        conn = await aiosqlite.connect(self.db_path, timeout=10)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def create_session(self, session_id: str) -> SessionState:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier

        Returns:
            New SessionState instance

        Raises:
            SessionError: If maximum session limit reached
        """
        async with self._lock:
            now = time.time()

            # Cleanup expired sessions first
            await self._cleanup_expired()

            # Check session limit
            async with self._transaction() as conn:
                async with conn.execute("SELECT COUNT(*) as cnt FROM sessions") as cursor:
                    row = await cursor.fetchone()
                    count = row["cnt"] if row else 0
                    if count >= self.max_sessions:
                        raise SessionError(
                            f"Maximum session limit reached ({self.max_sessions}). "
                            "Please wait and try again."
                        )

            # Create session
            session = SessionState(
                session_id=session_id, created_at=now, last_accessed=now
            )

            async with self._transaction() as conn:
                await conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, customer_id, is_authenticated,
                        created_at, last_accessed, conversation_context, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.session_id,
                        session.customer_id,
                        int(session.is_authenticated),
                        session.created_at,
                        session.last_accessed,
                        json.dumps(session.conversation_context),
                        json.dumps(session.metadata),
                    ),
                )

            return session

    async def get_session(self, session_id: str) -> SessionState | None:
        """
        Retrieve an existing session.

        Args:
            session_id: Session identifier

        Returns:
            SessionState if found and not expired, None otherwise
        """
        async with self._lock:
            async with self._transaction() as conn:
                async with conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,),
                ) as cursor:
                    row = await cursor.fetchone()

                    if row is None:
                        return None

                    session = SessionState.from_row(dict(row))

                    # Check expiration
                    if session.is_expired(self.ttl_seconds):
                        await conn.execute(
                            "DELETE FROM sessions WHERE session_id = ?",
                            (session_id,),
                        )
                        return None

                    # Update last_accessed
                    session.touch()
                    await conn.execute(
                        "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
                        (session.last_accessed, session_id),
                    )

                    return session

    async def authenticate_session(self, session_id: str, customer_id: str) -> bool:
        """
        Bind a customer identity to a session.

        Args:
            session_id: Session identifier
            customer_id: Verified customer ID number

        Returns:
            True if authentication successful

        Raises:
            SessionError: If session not found or expired
            AuthenticationError: If customer ID validation fails
        """
        async with self._lock:
            async with self._transaction() as conn:
                async with conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,),
                ) as cursor:
                    row = await cursor.fetchone()

                    if row is None:
                        raise SessionError(f"Session not found: {session_id}")

                    session = SessionState.from_row(dict(row))

                    if session.is_expired(self.ttl_seconds):
                        await conn.execute(
                            "DELETE FROM sessions WHERE session_id = ?",
                            (session_id,),
                        )
                        raise SessionError("Session expired")

                    # Import TC Kimlik validator
                    from core.tc_kimlik_validator import validate_tc_kimlik

                    # Validate TC Kimlik algorithmically
                    if not customer_id or not validate_tc_kimlik(customer_id):
                        raise AuthenticationError(
                            "Geçersiz TC Kimlik numarası. "
                            "11 haneli geçerli bir numara giriniz."
                        )

                    # Update session
                    session.customer_id = customer_id
                    session.is_authenticated = True
                    session.touch()

                    await conn.execute(
                        """
                        UPDATE sessions
                        SET customer_id = ?, is_authenticated = 1, last_accessed = ?
                        WHERE session_id = ?
                        """,
                        (customer_id, session.last_accessed, session_id),
                    )

                    return True

    async def update_context(self, session_id: str, key: str, value: Any):
        """
        Update conversation context data.

        Args:
            session_id: Session identifier
            key: Context key
            value: Context value
        """
        session = await self.get_session(session_id)
        if session:
            session.conversation_context[key] = value
            async with self._lock:
                async with self._transaction() as conn:
                    await conn.execute(
                        """
                        UPDATE sessions SET conversation_context = ?, last_accessed = ?
                        WHERE session_id = ?
                        """,
                        (
                            json.dumps(session.conversation_context),
                            session.last_accessed,
                            session_id,
                        ),
                    )

    async def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get conversation context data.

        Args:
            session_id: Session identifier
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        session = await self.get_session(session_id)
        if session:
            return session.conversation_context.get(key, default)
        return default

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        async with self._lock:
            async with self._transaction() as conn:
                async with conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,),
                ) as cursor:
                    rowcount = cursor.rowcount
                    return rowcount > 0

    async def _cleanup_expired(self):
        """Remove all expired sessions."""
        cutoff = time.time() - self.ttl_seconds
        async with self._transaction() as conn:
            await conn.execute(
                "DELETE FROM sessions WHERE last_accessed < ?",
                (cutoff,),
            )

    async def get_stats(self) -> dict[str, Any]:
        """
        Get session manager statistics.

        Returns:
            Dictionary with session statistics
        """
        async with self._lock:
            # Cleanup first
            await self._cleanup_expired()

            async with self._transaction() as conn:
                async with conn.execute("SELECT COUNT(*) as cnt FROM sessions") as cursor:
                    row = await cursor.fetchone()
                    total = row["cnt"] if row else 0

                async with conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions WHERE is_authenticated = 1"
                ) as cursor:
                    row = await cursor.fetchone()
                    authenticated = row["cnt"] if row else 0

                async with conn.execute(
                    "SELECT MIN(last_accessed) as min_ts FROM sessions"
                ) as cursor:
                    row = await cursor.fetchone()
                    oldest = row["min_ts"] if row and row["min_ts"] else None

                return {
                    "active_sessions": total,
                    "authenticated_sessions": authenticated,
                    "max_sessions": self.max_sessions,
                    "ttl_seconds": self.ttl_seconds,
                    "oldest_session": oldest,
                    "storage": "sqlite",
                    "db_path": self.db_path,
                }

    async def cleanup_all(self):
        """Manually cleanup all expired sessions."""
        async with self._lock:
            await self._cleanup_expired()

    async def close(self):
        """Close the session manager (cleanup resources)."""
        pass   # SQLite connections are closed per-transaction, nothing to cleanup
        pass
