from abc import ABC, abstractmethod
from typing import Any


class IAuthService(ABC):
    """
    Authentication service interface.

    Implementations can use:
    - Mock validation (development)
    - Database lookup (production)
    - External identity provider (enterprise)
    """

    @abstractmethod
    def verify_customer(self, id_number: str) -> bool:
        """
        Verify customer identity by ID number.

        Args:
            id_number: Customer identification number (e.g., Turkish TC Kimlik)

        Returns:
            True if customer exists and is valid
        """
        pass

    @abstractmethod
    def get_customer_info(self, id_number: str) -> dict[str, Any] | None:
        """
        Retrieve customer information by ID number.

        Args:
            id_number: Customer identification number

        Returns:
            Dictionary with customer info or None if not found
        """
        pass


class IAccountService(ABC):
    """
    Account service interface for banking operations.

    Implementations can use:
    - Mock data (development/testing)
    - Core banking API (production)
    - Database direct access (legacy)
    """

    @abstractmethod
    def get_balance(self, customer_id: str) -> dict[str, Any]:
        """
        Get customer account balance.

        Args:
            customer_id: Verified customer ID

        Returns:
            Dictionary with account_type, balance, currency
        """
        pass

    @abstractmethod
    def get_credit_card_debt(self, customer_id: str) -> dict[str, Any]:
        """
        Get customer credit card debt information.

        Args:
            customer_id: Verified customer ID

        Returns:
            Dictionary with card_name, debt, currency, due_date
        """
        pass

    @abstractmethod
    def execute_eft(
        self, customer_id: str, to_iban: str, amount: float
    ) -> dict[str, Any]:
        """
        Execute EFT (Electronic Funds Transfer) to another bank.

        Args:
            customer_id: Source customer ID
            to_iban: Destination IBAN (TR...)
            amount: Transfer amount

        Returns:
            Dictionary with status, transaction_id, message
        """
        pass

    @abstractmethod
    def execute_havale(
        self, customer_id: str, to_account: str, amount: float
    ) -> dict[str, Any]:
        """
        Execute Havale (same-bank transfer).

        Args:
            customer_id: Source customer ID
            to_account: Destination account number
            amount: Transfer amount

        Returns:
            Dictionary with status, transaction_id, message
        """
        pass

    @abstractmethod
    def get_transaction_history(
        self, customer_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get recent transaction history.

        Args:
            customer_id: Customer ID
            limit: Number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        pass

    @abstractmethod
    def list_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        """
        List all accounts for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of account dictionaries with type, balance, currency
        """
        pass

    @abstractmethod
    def pay_credit_card(self, customer_id: str, amount: float) -> dict[str, Any]:
        """
        Pay credit card bill.

        Args:
            customer_id: Customer ID
            amount: Payment amount

        Returns:
            Dictionary with status, transaction_id, message
        """
        pass
