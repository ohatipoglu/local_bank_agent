"""
Tests for extended banking tools (transaction history, account listing, credit card payment).
"""

from unittest.mock import MagicMock

from application.tools_registry import BankToolsRegistry
from infrastructure.mock_services import MockAccountService


class TestTransactionHistory:
    """Test transaction history tool."""

    def test_get_transaction_history(self):
        """Test retrieving transaction history."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        # Find transaction history tool
        txn_tool = next(t for t in tools if t.name == "get_transaction_history")

        result = txn_tool.invoke({"customer_id": "12345678901", "limit": 5})

        assert "Son işlemleriniz" in result or "işlem" in result.lower()
        assert isinstance(result, str)

    def test_get_transaction_history_no_service(self):
        """Test transaction history with no service."""
        registry = BankToolsRegistry(None)
        tools = registry.get_tools()

        txn_tool = next(t for t in tools if t.name == "get_transaction_history")

        result = txn_tool.invoke({"customer_id": "12345678901"})
        assert "Servis hatası" in result

    def test_get_transaction_history_empty(self):
        """Test transaction history with no transactions."""
        mock_service = MagicMock()
        mock_service.get_transaction_history.return_value = []

        registry = BankToolsRegistry(mock_service)
        tools = registry.get_tools()

        txn_tool = next(t for t in tools if t.name == "get_transaction_history")

        result = txn_tool.invoke({"customer_id": "12345678901"})
        assert "hiç işlem bulunamadı" in result.lower()


class TestListAccounts:
    """Test account listing tool."""

    def test_list_accounts(self):
        """Test listing customer accounts."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        # Find list accounts tool
        accounts_tool = next(t for t in tools if t.name == "list_accounts")

        result = accounts_tool.invoke({"customer_id": "12345678901"})

        assert "Hesaplarınız" in result or "hesap" in result.lower()
        assert isinstance(result, str)

    def test_list_accounts_no_service(self):
        """Test list accounts with no service."""
        registry = BankToolsRegistry(None)
        tools = registry.get_tools()

        accounts_tool = next(t for t in tools if t.name == "list_accounts")

        result = accounts_tool.invoke({"customer_id": "12345678901"})
        assert "Servis hatası" in result

    def test_list_accounts_multiple(self):
        """Test listing multiple accounts."""
        account_service = MockAccountService()

        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        accounts_tool = next(t for t in tools if t.name == "list_accounts")

        result = accounts_tool.invoke({"customer_id": "12345678901"})
        # Should include both deposit and credit card accounts
        assert isinstance(result, str)
        assert len(result) > 0


class TestPayCreditCard:
    """Test credit card payment tool."""

    def test_pay_credit_card_full(self):
        """Test paying full credit card debt."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        # Find pay credit card tool
        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        result = pay_tool.invoke({"customer_id": "12345678901", "amount": None})

        assert "başarıyla" in result.lower() or "ödeme" in result.lower()
        assert isinstance(result, str)

    def test_pay_credit_card_partial(self):
        """Test paying partial credit card debt."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        # Pay partial amount
        result = pay_tool.invoke({"customer_id": "12345678901", "amount": 1000.0})

        assert isinstance(result, str)

    def test_pay_credit_card_no_debt(self):
        """Test paying when no debt exists."""
        mock_service = MagicMock()
        mock_service.get_credit_card_debt.return_value = {
            "card_name": "Test Card",
            "debt": 0,
            "currency": "TRY",
            "due_date": "10 Nisan",
        }

        registry = BankToolsRegistry(mock_service)
        tools = registry.get_tools()

        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        result = pay_tool.invoke({"customer_id": "12345678901", "amount": None})
        assert "borcunuz bulunmuyor" in result.lower()

    def test_pay_credit_card_overpay(self):
        """Test paying more than debt."""
        mock_service = MagicMock()
        mock_service.get_credit_card_debt.return_value = {
            "card_name": "Test Card",
            "debt": 1000,
            "currency": "TRY",
            "due_date": "10 Nisan",
        }

        registry = BankToolsRegistry(mock_service)
        tools = registry.get_tools()

        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        result = pay_tool.invoke({"customer_id": "12345678901", "amount": 2000.0})
        assert "fazla olamaz" in result.lower()

    def test_pay_credit_card_no_service(self):
        """Test pay credit card with no service."""
        registry = BankToolsRegistry(None)
        tools = registry.get_tools()

        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        result = pay_tool.invoke({"customer_id": "12345678901", "amount": None})
        assert "Servis hatası" in result

    def test_pay_credit_card_invalid_amount(self):
        """Test pay credit card with invalid amount."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        pay_tool = next(t for t in tools if t.name == "pay_credit_card")

        result = pay_tool.invoke({"customer_id": "12345678901", "amount": -100.0})
        assert isinstance(result, str)
        assert "Geçersiz tutar" in result


class TestBankToolsRegistry:
    """Test bank tools registry."""

    def test_get_tools_count(self):
        """Test that all tools are registered."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        # Should have 7 tools now
        assert len(tools) == 7

    def test_tool_names(self):
        """Test that all expected tools are present."""
        account_service = MockAccountService()
        registry = BankToolsRegistry(account_service)
        tools = registry.get_tools()

        tool_names = {t.name for t in tools}
        expected_names = {
            "get_balance",
            "get_credit_card_debt",
            "execute_eft",
            "execute_havale",
            "get_transaction_history",
            "list_accounts",
            "pay_credit_card",
        }

        assert tool_names == expected_names