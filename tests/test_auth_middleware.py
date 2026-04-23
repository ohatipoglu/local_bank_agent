"""
Tests for authentication middleware.
"""

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from core.auth_middleware import (
    APIKeySecurity,
    AuthenticationMiddleware,
    get_api_key,
    setup_cors_middleware,
)


class TestAPIKeySecurity:
    """Test API key authentication."""

    def test_api_key_security_class(self):
        """Test APIKeySecurity initialization."""
        auth = APIKeySecurity(name="X-API-Key", auto_error=False)
        assert auth.model.name == "X-API-Key"
        assert auth.auto_error is False


class TestGetApiKey:
    """Test API key validation function."""

    @pytest.mark.asyncio
    async def test_no_api_key_configured(self):
        """Test when no API key is configured."""
        import core.auth_middleware as auth_module

        original_key = auth_module.API_KEY
        auth_module.API_KEY = ""

        result = await get_api_key(api_key=None)
        assert result is None

        auth_module.API_KEY = original_key

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test valid API key."""
        import core.auth_middleware as auth_module

        original_key = auth_module.API_KEY
        auth_module.API_KEY = "test-secret-key"

        result = await get_api_key(api_key="test-secret-key")
        assert result == "test-secret-key"

        auth_module.API_KEY = original_key

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test invalid API key raises exception."""
        import core.auth_middleware as auth_module

        original_key = auth_module.API_KEY
        auth_module.API_KEY = "test-secret-key"

        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(api_key="wrong-key")

        assert exc_info.value.status_code == 401
        assert "Invalid or missing API key" in exc_info.value.detail

        auth_module.API_KEY = original_key


class TestAuthenticationMiddleware:
    """Test authentication middleware."""

    @pytest.mark.asyncio
    async def test_public_path_skip(self):
        """Test public paths skip authentication."""
        app = FastAPI()
        app.add_middleware(AuthenticationMiddleware)

        @app.get("/")
        async def root():
            return {"message": "OK"}

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_protected_path_without_key(self):
        """Test protected path requires API key."""
        import core.auth_middleware as auth_module

        original_key = auth_module.API_KEY
        auth_module.API_KEY = "test-secret-key"

        app = FastAPI()
        app.add_middleware(AuthenticationMiddleware)

        @app.get("/api/logs")
        async def logs():
            return {"logs": []}

        client = TestClient(app)
        response = client.get("/api/logs")
        assert response.status_code == 401

        auth_module.API_KEY = original_key

    def test_protected_path_with_valid_key(self):
        """Test protected path with valid API key."""
        import core.auth_middleware as auth_module

        original_key = auth_module.API_KEY
        auth_module.API_KEY = "test-secret-key"

        app = FastAPI()
        app.add_middleware(AuthenticationMiddleware)

        @app.get("/api/logs")
        async def logs():
            return {"logs": []}

        client = TestClient(app)
        response = client.get("/api/logs", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 200

        auth_module.API_KEY = original_key


class TestCORSMiddleware:
    """Test CORS middleware setup."""

    def test_setup_cors_default_origins(self):
        """Test CORS setup with default origins."""
        app = FastAPI()
        setup_cors_middleware(app)

        # Check middleware is added
        assert len(app.user_middleware) > 0

    def test_setup_cors_custom_origins(self):
        """Test CORS setup with custom origins."""
        app = FastAPI()
        origins = ["http://localhost:3000", "https://example.com"]
        setup_cors_middleware(app, origins=origins)

        # Check middleware is added
        assert len(app.user_middleware) > 0
