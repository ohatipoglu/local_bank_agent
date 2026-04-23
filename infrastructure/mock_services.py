"""
Mock implementations of banking services for development and testing.
"""

import hashlib
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from domain.interfaces import IAccountService, IAuthService


class MockAuthService(IAuthService):
    """
    Mock authentication service for development.

    Validates 11-digit Turkish TC Kimlik number format with algorithmic check.
    Simulates password/OTP verification for production-like auth flow.
    Generates JWT tokens for authenticated sessions.

    Note: Test numbers are now algorithmically valid TC Kimlik numbers.
    - 10000000146: Valid per checksum algorithm
    - 20000000114: Valid per checksum algorithm

    Simulated credentials (for development only):
    - Customer 10000000146: password="123456", OTP="111111"
    - Customer 20000000114: password="654321", OTP="222222"
    """

    # JWT configuration - CRITICAL: Use strong secret from environment in production
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    # Simulated customer database (using algorithmically valid TC Kimlik numbers)
    _CUSTOMERS = {
        "10000000146": {
            "id": "CUST001",
            "tc_kimlik": "10000000146",
            "first_name": "Ahmet",
            "last_name": "Yılmaz",
            "phone_number": "5551234567",
            # Simulated credentials (in production, these would be hashed)
            "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
            "otp_code": "111111",  # Simulated SMS OTP
        },
        "20000000114": {
            "id": "CUST002",
            "tc_kimlik": "20000000114",
            "first_name": "Fatma",
            "last_name": "Demir",
            "phone_number": "5559876543",
            "password_hash": hashlib.sha256("654321".encode()).hexdigest(),
            "otp_code": "222222",  # Simulated SMS OTP
        },
    }

    def verify_customer(self, id_number: str) -> bool:
        """
        Verify customer by 11-digit ID number with TC Kimlik algorithm check.

        Args:
            id_number: Turkish TC Kimlik number (11 digits)

        Returns:
            True if valid format and algorithmically valid
        """
        if not id_number or len(id_number) != 11 or not id_number.isdigit():
            return False

        # Import algorithmic validation
        from core.tc_kimlik_validator import validate_tc_kimlik

        # Check algorithmic validity
        if not validate_tc_kimlik(id_number):
            return False

        # For mock: accept any algorithmically valid number
        return True

    def verify_password(self, id_number: str, password: str) -> bool:
        """
        Verify customer password (simulated).

        Args:
            id_number: Turkish TC Kimlik number
            password: Plain text password

        Returns:
            True if password matches
        """
        customer = self._CUSTOMERS.get(id_number)
        if not customer:
            return False

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == customer["password_hash"]

    def verify_otp(self, id_number: str, otp_code: str) -> bool:
        """
        Verify SMS OTP code (simulated).

        In production, this would check against a real SMS gateway.
        For development, uses hardcoded OTP codes.

        Args:
            id_number: Turkish TC Kimlik number
            otp_code: 6-digit OTP code

        Returns:
            True if OTP matches
        """
        customer = self._CUSTOMERS.get(id_number)
        if not customer:
            return False

        return otp_code == customer["otp_code"]

    def generate_jwt_token(self, id_number: str, auth_method: str = "password") -> str:
        """
        Generate JWT token for authenticated customer.

        Args:
            id_number: Turkish TC Kimlik number
            auth_method: Method used for authentication ("password" or "otp")

        Returns:
            JWT token string
        """
        customer = self._CUSTOMERS.get(id_number)
        if not customer:
            raise ValueError(f"Customer not found: {id_number}")

        now = datetime.now(timezone.utc)
        payload = {
            "sub": id_number,
            "customer_id": customer["id"],
            "name": f"{customer['first_name']} {customer['last_name']}",
            "auth_method": auth_method,
            "iat": now,
            "exp": now + timedelta(hours=self.JWT_EXPIRY_HOURS),
            "jti": str(uuid.uuid4()),  # Unique token ID
        }

        token = jwt.encode(payload, self.JWT_SECRET, algorithm=self.JWT_ALGORITHM)
        return token

    def decode_jwt_token(self, token: str) -> dict[str, Any] | None:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_customer_info(self, id_number: str) -> dict[str, Any] | None:
        """
        Get customer info by ID number.

        Args:
            id_number: Turkish TC Kimlik number

        Returns:
            Customer info dictionary or None
        """
        customer = self._CUSTOMERS.get(id_number)
        if customer is None:
            return None

        # Return copy without sensitive data
        return {
            "id": customer["id"],
            "tc_kimlik": customer["tc_kimlik"],
            "first_name": customer["first_name"],
            "last_name": customer["last_name"],
            "phone_number": customer["phone_number"],
        }


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

    def get_balance(self, customer_id: str) -> dict[str, Any]:
        """
        Get customer account balance.

        Args:
            customer_id: Customer ID number

        Returns:
            Account balance information
        """
        return self._ACCOUNTS.get(
            customer_id,
            {"account_type": "Vadesiz", "balance": 15000.00, "currency": "TRY"},
        )

    def get_credit_card_debt(self, customer_id: str) -> dict[str, Any]:
        """
        Get customer credit card debt.

        Args:
            customer_id: Customer ID number

        Returns:
            Credit card debt information
        """
        return self._CREDIT_CARDS.get(
            customer_id,
            {
                "card_name": "Classic Visa",
                "debt": 5000.00,
                "currency": "TRY",
                "due_date": "10 Nisan",
            },
        )

    def execute_eft(
        self, customer_id: str, to_iban: str, amount: float
    ) -> dict[str, Any]:
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

    def execute_havale(
        self, customer_id: str, to_account: str, amount: float
    ) -> dict[str, Any]:
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
        self, customer_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
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
        for _ in range(min(limit, 5)):
            days_ago = random.randint(1, 30)
            date = datetime.now() - timedelta(days=days_ago)
            transactions.append(
                {
                    "transaction_id": f"TXN{uuid.uuid4().hex[:6].upper()}",
                    "type": random.choice(["EFT", "Havale", "Kredi Kartı Ödeme"]),
                    "amount": round(random.uniform(100, 5000), 2),
                    "currency": "TRY",
                    "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Başarılı",
                }
            )
        return transactions

    def list_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        """
        List all accounts for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of account dictionaries
        """
        # Return all accounts for this customer
        accounts = []

        # Get deposit account
        if customer_id in self._ACCOUNTS:
            account = self._ACCOUNTS[customer_id].copy()
            account["account_number"] = customer_id
            accounts.append(account)

        # Get credit card account
        if customer_id in self._CREDIT_CARDS:
            card = self._CREDIT_CARDS[customer_id].copy()
            card["account_type"] = "Kredi Kartı"
            card["balance"] = -card.get("debt", 0)  # Negative balance = debt
            card["account_number"] = customer_id
            accounts.append(card)

        # If no accounts found, return default
        if not accounts:
            accounts.append(
                {
                    "account_type": "Vadesiz",
                    "balance": 15000.00,
                    "currency": "TRY",
                    "account_number": customer_id,
                }
            )

        return accounts

    def pay_credit_card(self, customer_id: str, amount: float) -> dict[str, Any]:
        """
        Pay credit card bill.

        Args:
            customer_id: Customer ID
            amount: Payment amount

        Returns:
            Transaction result
        """
        # Validate amount
        if amount <= 0:
            return {
                "status": "error",
                "message": "Geçersiz tutar. Pozitif bir miktar giriniz.",
                "transaction_id": None,
            }

        # Get current debt
        debt_info = self.get_credit_card_debt(customer_id)
        current_debt = debt_info.get("debt", 0)

        if current_debt <= 0:
            return {
                "status": "error",
                "message": "Kredi kartı borcunuz bulunmuyor.",
                "transaction_id": None,
            }

        if amount > current_debt:
            return {
                "status": "error",
                "message": f"Ödeme tutarı borçtan fazla olamaz. Güncel borç: {current_debt:,.2f} {debt_info.get('currency', 'TRY')}",
                "transaction_id": None,
            }

        # Simulate payment transaction
        transaction_id = f"CCP{uuid.uuid4().hex[:8].upper()}"
        remaining_debt = current_debt - amount

        return {
            "status": "success",
            "message": (
                f"Kredi kartı ödemesi başarıyla tamamlandı. "
                f"İşlem No: {transaction_id}, "
                f"Ödenen: {amount:,.2f} {debt_info.get('currency', 'TRY')}, "
                f"Kalan Borç: {remaining_debt:,.2f} {debt_info.get('currency', 'TRY')}"
            ),
            "transaction_id": transaction_id,
            "amount_paid": amount,
            "remaining_debt": remaining_debt,
        }
