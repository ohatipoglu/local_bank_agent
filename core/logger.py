"""
Structured logging with correlation IDs and JSON formatting support.
Provides both human-readable console output and machine-parseable JSON logs.
"""
import sys
import sqlite3
import datetime
import json
import uuid
import os
import threading
from loguru import logger
from contextvars import ContextVar
from typing import Optional

# SQLite Log Database Path
LOG_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'logs.db'
)

# Context variable for correlation ID (thread-safe async context)
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def get_correlation_id() -> str:
    """Get or create a correlation ID for request tracing."""
    cid = correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())[:12]
        correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str):
    """Set correlation ID for current context."""
    correlation_id.set(cid)


def init_db():
    """Initialize SQLite log database with proper schema."""
    conn = sqlite3.connect(LOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            session_id TEXT,
            correlation_id TEXT,
            module TEXT,
            function TEXT,
            line INTEGER,
            message TEXT,
            extra_json TEXT
        )
    ''')
    # Add correlation_id column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE application_logs ADD COLUMN correlation_id TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Add extra_json column for structured data
    try:
        cursor.execute('ALTER TABLE application_logs ADD COLUMN extra_json TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


# Thread-safe connection pool for SQLite
class LogConnectionPool:
    """Simple connection pool for SQLite log writes to avoid lock contention."""

    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._lock = threading.Lock()
        self._connections = []
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._connections = [
                        sqlite3.connect(self.db_path, check_same_thread=False)
                        for _ in range(self.pool_size)
                    ]
                    self._initialized = True

    def get_connection(self):
        """Get a connection from the pool (thread-safe)."""
        self._initialize()
        with self._lock:
            if self._connections:
                return self._connections.pop()
            # If pool exhausted, create temporary connection
            return sqlite3.connect(self.db_path, check_same_thread=False)

    def return_connection(self, conn, is_temp: bool = False):
        """Return a connection to the pool."""
        if is_temp:
            try:
                conn.close()
            except Exception:
                pass
        else:
            with self._lock:
                if len(self._connections) < self.pool_size:
                    self._connections.append(conn)
                else:
                    try:
                        conn.close()
                    except Exception:
                        pass


# Global connection pool
_pool = LogConnectionPool(LOG_DB_PATH)


def sqlite_sink(message):
    """Structured SQLite log sink with correlation ID support."""
    record = message.record
    conn = _pool.get_connection()
    is_temp = conn not in _pool._connections if _pool._initialized else True

    try:
        cursor = conn.cursor()
        # Serialize extra data as JSON
        extra_data = record.get("extra", {})
        extra_json_str = json.dumps(extra_data, default=str) if extra_data else None

        cursor.execute('''
            INSERT INTO application_logs
            (timestamp, level, session_id, correlation_id, module, function, line, message, extra_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            record["level"].name,
            record["extra"].get("session_id", "system"),
            record["extra"].get("correlation_id", get_correlation_id()),
            record["name"],
            record["function"],
            record["line"],
            record["message"],
            extra_json_str
        ))
        conn.commit()
    except Exception as e:
        # Fallback: print to stderr if logging fails
        print(f"Log yazılamadı: {e}", file=sys.stderr)
    finally:
        _pool.return_connection(conn, is_temp)


# Console log format with correlation ID
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "[<magenta>{extra[session_id]}</magenta>] | "
    "[<yellow>{extra[correlation_id]}</yellow>] | "
    "<level>{message}</level>"
)

# JSON log format for production (use in prod environments)
def json_format_sink(message):
    """JSON structured log output for production environments."""
    record = message.record
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "level": record["level"].name,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
        "session_id": record["extra"].get("session_id", "system"),
        "correlation_id": record["extra"].get("correlation_id", get_correlation_id()),
    }
    # Add any extra fields
    for key, value in record["extra"].items():
        if key not in ["session_id", "correlation_id"]:
            log_entry[key] = value

    print(json.dumps(log_entry, default=str))


# Initialize database on module load
init_db()

# Remove default logger
logger.remove()

# Add console logger (development)
logger.add(
    sys.stdout,
    format=CONSOLE_FORMAT,
    level="DEBUG",
    backtrace=True,
    diagnose=True
)

# Add SQLite sink
logger.add(sqlite_sink, level="DEBUG")

# Optional: Add JSON console logger for production (uncomment in prod)
# logger.add(json_format_sink, level="INFO", serialize=False)


def get_session_logger(session_id: str = None) -> "loguru.Logger":
    """
    Get a logger bound to a specific session with automatic correlation ID.

    Args:
        session_id: Optional session identifier. Auto-generated if not provided.

    Returns:
        Loguru logger instance bound with session_id and correlation_id.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    cid = get_correlation_id()
    return logger.bind(session_id=session_id, correlation_id=cid)


def get_correlated_logger(session_id: str = None, correlation_id: str = None) -> "loguru.Logger":
    """
    Get a logger with explicit correlation ID for request tracing.

    Args:
        session_id: Session identifier
        correlation_id: Request correlation ID for distributed tracing

    Returns:
        Loguru logger instance with full context binding
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]
    if correlation_id is None:
        correlation_id = get_correlation_id()

    return logger.bind(session_id=session_id, correlation_id=correlation_id)
