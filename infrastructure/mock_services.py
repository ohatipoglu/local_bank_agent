"""
Mock implementations of banking services for development and testing.
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from domain.interfaces import IAccountService, IAuthService


class MockAuthService(IAuthService):
    """
    Mock authentication service for development.
    
    Validates 11-digit Turkish TC Kimlik number format.
    Replace with real authentication in production.
    """

    # Simulated customer database
    _CUSTOMERS = {
        "12345678901": {
            "id": "CUST001",
            "tc_kimlik": "12345678901",
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "phone_number": "5551234567",
        },
        "98765432109": {
            "id": "CUST002",
            "tc_kimlik": "98765432109",
            "first_name": "Fatma",
            "last_name": "Demir",
            "phone_number": "5559876543",
        },
    }

    def verify_customer(self, id_number: str) -> bool:
        """
        Verify customer by 11-digit ID number.
        
        Args:
            id_number: Turkish TC Kimlik number (11 digits)
            
        Returns:
            True if valid format and customer exists
        """
        if not id_number or len(id_number) != 11 or not id_number.isdigit():
            return False

        # For mock: accept any 11-digit number
        return True

    def get_customer_info(self, id_number: str) -> Optional[Dict[str, Any]]:
        """
        Get customer info by ID number.
        
        Args:
            id_number: Turkish TC Kimlik number
            
        Returns:
            Customer info dictionary or None
        """
        return self._CUSTOMERS.get(id_number)


class MockAccountService(IAccountService):
    """
    Mock account service for development and testing.
    
    Returns hardcoded data. Replace with real banking API in production.
    """

    # Simulated account data
    _ACCOUNTS = {
        "12345678901": {
            "account_type": "Vadesiz",
            "balance": 45500.00,
            "currency": "TRY",
        },
        "98765432109": {
            "account_type": "Vadeli",
            "balance": 128750.50,
            "currency": "TRY",
        },
    }

    _CREDIT_CARDS = {
        "12345678901": {
            "card_name": "Platinum Visa",
            "debt": 12450.75,
            "currency": "TRY",
            "due_date": "15 Nisan",
        },
        "98765432109": {
            "card_name": "Gold MasterCard",
            "debt": 8320.00,
            "currency": "TRY",
            "due_date": "20 Nisan",
        },
    }

    def get_balance(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer account balance.
        
        Args:
            customer_id: Customer ID number
            
        Returns:
            Account balance information
        """
        return self._ACCOUNTS.get(
            customer_id,
            {"account_type": "Vadesiz", "balance": 15000.00, "currency": "TRY"}
        )

    def get_credit_card_debt(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer credit card debt.
        
        Args:
            customer_id: Customer ID number
            
        Returns:
            Credit card debt information
        """
        return self._CREDIT_CARDS.get(
            customer_id,
            {"card_name": "Classic Visa", "debt": 5000.00, "currency": "TRY", "due_date": "10 Nisan"}
        )

    def execute_eft(self, customer_id: str, to_iban: str, amount: float) -> Dict[str, Any]:
        """
        Execute EFT transfer.
        
        Args:
            customer_id: Source customer ID
            to_iban: Destination IBAN
            amount: Transfer amount
            
        Returns:
            Transaction result
        """
        # Validate IBAN format
        if not to_iban.startswith("TR"):
            return {
                "status": "error",
                "message": "Geçersiz IBAN formatı. IBAN TR ile başlamalıdır.",
                "transaction_id": None,
            }

        # Simulate transaction
        transaction_id = f"EFT{uuid.uuid4().hex[:8].upper()}"
        return {
            "status": "success",
            "message": f"EFT işlemi başarıyla tamamlandı. İşlem No: {transaction_id}",
            "transaction_id": transaction_id,
            "amount": amount,
            "to_iban": to_iban,
        }

    def execute_havale(self, customer_id: str, to_account: str, amount: float) -> Dict[str, Any]:
        """
        Execute Havale transfer (same bank).
        
        Args:
            customer_id: Source customer ID
            to_account: Destination account number
            amount: Transfer amount
            
        Returns:
            Transaction result
        """
        # Simulate transaction
        transaction_id = f"HVL{uuid.uuid4().hex[:8].upper()}"
        return {
            "status": "success",
            "message": f"Havale işlemi başarıyla tamamlandı. İşlem No: {transaction_id}",
            "transaction_id": transaction_id,
            "amount": amount,
            "to_account": to_account,
        }

    def get_transaction_history(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent transaction history.
        
        Args:
            customer_id: Customer ID
            limit: Number of transactions to return
            
        Returns:
            List of recent transactions
        """
        # Generate mock transactions
        transactions = []
        for i in range(min(limit, 5)):
            days_ago = random.randint(1, 30)
            date = datetime.now() - timedelta(days=days_ago)
            transactions.append({
                "transaction_id": f"TXN{uuid.uuid4().hex[:6].upper()}",
                "type": random.choice(["EFT", "Havale", "Kredi Kartı Ödeme"]),
                "amount": round(random.uniform(100, 5000), 2),
                "currency": "TRY",
                "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Başarılı",
            })
        return transactions
