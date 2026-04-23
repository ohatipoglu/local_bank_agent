"""
Tests for mock services (authentication and account services).
"""
import pytest
from infrastructure.mock_services import MockAuthService, MockAccountService


class TestMockAuthService:
    """Test MockAuthService implementation."""

    @pytest.fixture
    def auth_service(self):
        """Create MockAuthService instance."""
        return MockAuthService()

    def test_verify_valid_customer(self, auth_service):
        """Test verifying a valid 11-digit customer ID."""
        assert auth_service.verify_customer("10000000146") is True
        assert auth_service.verify_customer("20000000114") is True

    def test_verify_invalid_length(self, auth_service):
        """Test verifying ID with wrong length."""
        assert auth_service.verify_customer("12345") is False
        assert auth_service.verify_customer("123456789012") is False

    def test_verify_non_numeric(self, auth_service):
        """Test verifying non-numeric ID."""
        assert auth_service.verify_customer("abcdefghijk") is False

    def test_verify_empty(self, auth_service):
        """Test verifying empty ID."""
        assert auth_service.verify_customer("") is False
        assert auth_service.verify_customer(None) is False

    def test_get_customer_info_existing(self, auth_service):
        """Test retrieving info for existing customer."""
        info = auth_service.get_customer_info("10000000146")
        assert info is not None
        assert info["first_name"] == "Ahmet"
        assert info["last_name"] == "Yılmaz"
        assert info["tc_kimlik"] == "10000000146"

    def test_get_customer_info_nonexistent(self, auth_service):
        """Test retrieving info for non-existing customer."""
        info = auth_service.get_customer_info("99999999999")
        assert info is None


class TestMockAccountService:
    """Test MockAccountService implementation."""

    @pytest.fixture
    def account_service(self):
        """Create MockAccountService instance."""
        return MockAccountService()

    def test_get_balance_existing_customer(self, account_service):
        """Test balance query for existing customer."""
        result = account_service.get_balance("12345678901")
        assert result["account_type"] == "Vadesiz"
        assert result["balance"] == 45500.00
        assert result["currency"] == "TRY"

    def test_get_balance_nonexistent_customer(self, account_service):
        """Test balance query for non-existing customer (returns default)."""
        result = account_service.get_balance("99999999999")
        assert result["balance"] == 15000.00
        assert result["currency"] == "TRY"

    def test_get_credit_card_debt_existing(self, account_service):
        """Test credit card debt query for existing customer."""
        result = account_service.get_credit_card_debt("12345678901")
        assert result["card_name"] == "Platinum Visa"
        assert result["debt"] == 12450.75
        assert result["due_date"] == "15 Nisan"

    def test_get_credit_card_debt_nonexistent(self, account_service):
        """Test credit card debt for non-existing customer (returns default)."""
        result = account_service.get_credit_card_debt("99999999999")
        assert result["debt"] == 5000.00

    def test_execute_eft_valid(self, account_service):
        """Test valid EFT execution."""
        result = account_service.execute_eft(
            "12345678901", "TR123456789012345678901234", 1000.0
        )
        assert result["status"] == "success"
        assert result["transaction_id"].startswith("EFT")
        assert "başarıyla" in result["message"]

    def test_execute_eft_invalid_iban(self, account_service):
        """Test EFT with invalid IBAN format."""
        result = account_service.execute_eft(
            "12345678901", "US1234567890", 1000.0
        )
        assert result["status"] == "error"
        assert "Geçersiz IBAN" in result["message"]

    def test_execute_havale_valid(self, account_service):
        """Test valid Havale execution."""
        result = account_service.execute_havale(
            "12345678901", "9876543210", 500.0
        )
        assert result["status"] == "success"
        assert result["transaction_id"].startswith("HVL")
        assert "başarıyla" in result["message"]

    def test_get_transaction_history(self, account_service):
        """Test transaction history retrieval."""
        transactions = account_service.get_transaction_history(
            "12345678901", limit=5
        )
        assert len(transactions) <= 5
        assert all("transaction_id" in tx for tx in transactions)
        assert all("type" in tx for tx in transactions)
        assert all("amount" in tx for tx in transactions)

    def test_get_transaction_history_limit(self, account_service):
        """Test transaction history limit enforcement."""
        transactions = account_service.get_transaction_history(
            "12345678901", limit=2
        )
        assert len(transactions) <= 2
