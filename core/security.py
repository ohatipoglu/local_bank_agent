"""
Security middleware for request validation, rate limiting, and input sanitization.
"""

import os
import re
import threading
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for use in paths
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r"[\\/\:\*\?\"\<\>\|]", "", filename)

    # Remove leading dots and whitespace
    sanitized = sanitized.lstrip(". ").strip()

    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:245] + ext

    # Ensure we have something
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        text: User input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove control characters except newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text.strip()


class RateLimiter:
    """Thread-safe rate limiter using sliding window algorithm."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for the given client."""
        with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            if client_id not in self._requests:
                self._requests[client_id] = []

            # Remove old requests outside the window
            self._requests[client_id] = [
                req_time
                for req_time in self._requests[client_id]
                if req_time > window_start
            ]

            # Check if under limit
            if len(self._requests[client_id]) < self.max_requests:
                self._requests[client_id].append(now)
                return True

            return False

    def get_retry_after(self, client_id: str) -> float:
        """Get seconds until next request is allowed."""
        with self._lock:
            if client_id not in self._requests or not self._requests[client_id]:
                return 0.0
            oldest = min(self._requests[client_id])
            return max(0, self.window_seconds - (time.time() - oldest))


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation, rate limiting, and security headers."""

    ALLOWED_AUDIO_MIME_TYPES = {
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "application/octet-stream",  # Fallback for some browsers
    }

    MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter(
            max_requests=30, window_seconds=60
        )

    async def dispatch(self, request: Request, call_next):
        # Skip security middleware for static files and docs
        path = request.url.path
        if path in [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ] or path.startswith("/static"):
            return await call_next(request)

        # Rate limiting for audio processing endpoint
        if path == "/process_audio":
            client_ip = request.client.host
            if not self.rate_limiter.is_allowed(client_ip):
                retry_after = self.rate_limiter.get_retry_after(client_ip)
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "message": "Çok fazla istek gönderildi. Lütfen bekleyin.",
                        "retry_after": round(retry_after, 1),
                    },
                    headers={"Retry-After": str(int(retry_after))},
                )

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        return response


def validate_audio_upload(file, filename: str = None) -> tuple[bool, str]:
    """
    Validate audio file upload: check MIME type and file size.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if hasattr(file, "file") and hasattr(file.file, "seek"):
        try:
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(0)  # Reset to beginning

            if file_size > SecurityMiddleware.MAX_AUDIO_SIZE_BYTES:
                max_mb = SecurityMiddleware.MAX_AUDIO_SIZE_BYTES / (1024 * 1024)
                return (
                    False,
                    f"Dosya boyutu çok büyük. Maksimum {max_mb:.0f} MB olmalıdır.",
                )
        except Exception:
            pass  # If we can't check size, continue anyway

    # Check file extension
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed_extensions = {"wav", "webm", "ogg", "mp3", "mp4", "m4a"}
        if ext not in allowed_extensions:
            return (
                False,
                f"Desteklenmeyen dosya formatı: .{ext}. İzin verilenler: {', '.join(allowed_extensions)}",
            )

    return True, ""
