"""
Tests for banking tools registry.
"""
import pytest
from application.tools_registry import BankToolsRegistry
from infrastructure.mock_services import MockAccountService


class TestBankToolsRegistry:
    """Test BankToolsRegistry tool creation and execution."""

    @pytest.fixture
    def registry(self):
        """Create registry with mock service."""
        service = MockAccountService()
        return BankToolsRegistry(service)

    def test_get_tools_returns_list(self, registry):
        """Test that get_tools returns a list of callables."""
        tools = registry.get_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 4  # balance, debt, eft, havale
        assert all(hasattr(tool, "invoke") for tool in tools)

    def test_get_balance_tool(self, registry):
        """Test balance inquiry tool execution."""
        tools = registry.get_tools()
        balance_tool = tools[0]

        # Tool should be callable
        assert hasattr(balance_tool, "invoke")

        # Tool has name attribute
        assert balance_tool.name == "get_balance"

    def test_get_credit_card_debt_tool(self, registry):
        """Test credit card debt tool execution."""
        tools = registry.get_tools()
        debt_tool = tools[1]

        assert hasattr(debt_tool, "invoke")
        assert debt_tool.name == "get_credit_card_debt"

    def test_execute_eft_tool(self, registry):
        """Test EFT tool execution."""
        tools = registry.get_tools()
        eft_tool = tools[2]

        assert hasattr(eft_tool, "invoke")
        assert eft_tool.name == "execute_eft"

    def test_execute_havale_tool(self, registry):
        """Test Havale tool execution."""
        tools = registry.get_tools()
        havale_tool = tools[3]

        assert hasattr(havale_tool, "invoke")
        assert havale_tool.name == "execute_havale"

    def test_tool_descriptions(self, registry):
        """Test all tools have meaningful descriptions."""
        tools = registry.get_tools()
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 20, f"Tool {tool.name} description too short"
