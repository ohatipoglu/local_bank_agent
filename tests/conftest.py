"""
Pytest configuration and conftest fixtures for Local Bank AI Agent tests.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_logger():
    """Provide a mock Loguru logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.fixture
def mock_account_service():
    """Provide a mock IAccountService implementation."""
    from infrastructure.mock_services import MockAccountService
    return MockAccountService()


@pytest.fixture
def mock_auth_service():
    """Provide a mock IAuthService implementation."""
    from infrastructure.mock_services import MockAuthService
    return MockAuthService()


@pytest.fixture
def test_session_id():
    """Provide a test session ID."""
    return "test-session-12345"


@pytest.fixture
def test_customer_id():
    """Provide a test customer ID (11-digit Turkish TC format)."""
    return "12345678901"
