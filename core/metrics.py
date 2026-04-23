"""
Prometheus metrics instrumentation for FastAPI.
Provides request/response metrics, latency histograms, and error rates.
"""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from core.config import Config
from core.logger import get_correlated_logger

log = get_correlated_logger()


def setup_prometheus_metrics(app: FastAPI):
    """
    Set up Prometheus metrics instrumentation.

    Metrics collected:
    - http_requests_total: Total HTTP requests (counter)
    - http_request_duration_seconds: Request latency (histogram)
    - http_requests_in_progress: Requests currently being processed (gauge)
    - http_request_size_bytes: Request size (histogram)
    - http_response_size_bytes: Response size (histogram)

    Args:
        app: FastAPI application instance
    """
    if not Config.ENABLE_PROMETHEUS:
        log.info("Prometheus metrics disabled")
        return

    log.info("Setting up Prometheus metrics...")

    # Create instrumentator with custom configuration
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        excluded_handlers=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/static/.*",
            "/favicon.ico",
        ],
    )

    # Add custom latency histogram with Turkish labels
    instrumentator.add(
        metrics.latency(
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                30.0,
                60.0,
            ),
        )
    )

    # Instrument the app
    instrumentator.instrument(app)

    # Expose metrics endpoint
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        tags=["monitoring"],
    )

    log.info("Prometheus metrics enabled at /metrics")


def create_custom_metrics():
    """
    Create custom business metrics.

    These metrics track banking-specific operations:
    - Audio processing latency
    - STT/TTS success rates
    - Agent response times
    - Authentication attempts
    """
    from prometheus_client import Counter, Gauge, Histogram

    # Audio processing metrics
    audio_processing_duration = Histogram(
        "audio_processing_duration_seconds",
        "Time spent processing audio (STT -> Agent -> TTS)",
        ["status"],  # success, error
        buckets=(1, 5, 10, 20, 30, 60, 120),
    )

    stt_duration = Histogram(
        "stt_duration_seconds",
        "Speech-to-text transcription time",
        ["status"],
        buckets=(0.5, 1, 2, 5, 10, 20, 30),
    )

    tts_duration = Histogram(
        "tts_duration_seconds",
        "Text-to-speech generation time",
        ["engine", "status"],  # google, piper, coqui, edge
        buckets=(0.5, 1, 2, 5, 10, 20, 30),
    )

    agent_response_duration = Histogram(
        "agent_response_duration_seconds",
        "AI agent response time",
        ["status"],
        buckets=(0.5, 1, 2, 5, 10, 20, 30),
    )

    # Authentication metrics
    auth_attempts = Counter(
        "auth_attempts_total",
        "Total authentication attempts",
        ["method", "status"],  # password, otp / success, failure
    )

    # Session metrics
    active_sessions = Gauge(
        "active_sessions",
        "Number of active user sessions",
    )

    # Banking operation metrics
    banking_operations = Counter(
        "banking_operations_total",
        "Total banking operations",
        ["operation_type", "status"],  # balance, eft, havale, credit_card / success, error
    )

    return {
        "audio_processing_duration": audio_processing_duration,
        "stt_duration": stt_duration,
        "tts_duration": tts_duration,
        "agent_response_duration": agent_response_duration,
        "auth_attempts": auth_attempts,
        "active_sessions": active_sessions,
        "banking_operations": banking_operations,
    }


# Global custom metrics instance
_custom_metrics = None


def get_custom_metrics():
    """Get or create custom metrics instance."""
    global _custom_metrics
    if _custom_metrics is None:
        _custom_metrics = create_custom_metrics()
    return _custom_metrics
