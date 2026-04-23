"""
LangChain tool definitions for banking operations.
Registry pattern for dynamic tool injection with dependency injection.
"""

from collections.abc import Callable

from langchain_core.tools import tool

from domain.interfaces import IAccountService


class BankToolsRegistry:
    """
    Registry for banking operation tools.

    Provides LangChain-compatible tools that wrap the account service
    abstraction. New tools can be added without modifying agent logic.

    Tools:
    - get_balance: Query account balance
    - get_credit_card_debt: Query credit card debt
    - execute_eft: Transfer to another bank (via IBAN)
    - execute_havale: Same-bank transfer (via account number)
    """

    def __init__(self, account_service: IAccountService):
        """
        Initialize tools registry with account service dependency.

        Args:
            account_service: Implementation of IAccountService
        """
        self.account_service = account_service
        self.tools = self._initialize_tools()

    def get_tools(self) -> list[Callable]:
        """
        Get all registered banking tools.

        Returns:
            List of LangChain tool callables
        """
        return self.tools

    def _initialize_tools(self) -> list[Callable]:
        """Define and register all banking tools."""

        @tool
        def get_balance(customer_id: str) -> str:
            """
            Müşterinin vadesiz hesap bakiyesini sorgular.
            Kullanıcı 'ne kadar param var', 'bakiyem nedir',
            'hesabımda ne kadar var' dediğinde bu aracı kullanın.

            Args:
                customer_id: Müşteri kimlik numarası (11 haneli)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                info = self.account_service.get_balance(customer_id)
                return (
                    f"Müşterinin {info['account_type']} hesabında "
                    f"{info['balance']:,.2f} {info['currency']} bulunmaktadır."
                )
            except Exception as e:
                return f"Bakiye sorgulama hatası: {str(e)}"

        @tool
        def get_credit_card_debt(customer_id: str) -> str:
            """
            Müşterinin güncel kredi kartı borcunu ve son ödeme tarihini sorgular.
            Kullanıcı 'kredi kartı borcum ne kadar', 'kart ekstresi',
            'son ödeme tarihi ne zaman' dediğinde bu aracı kullanın.

            Args:
                customer_id: Müşteri kimlik numarası (11 haneli)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                info = self.account_service.get_credit_card_debt(customer_id)
                return (
                    f"Müşterinin {info['card_name']} kartına ait güncel borcu "
                    f"{info['debt']:,.2f} {info['currency']}. "
                    f"Son ödeme tarihi: {info['due_date']}."
                )
            except Exception as e:
                return f"Kredi kartı sorgulama hatası: {str(e)}"

        @tool
        def execute_eft(iban: str, amount: float, customer_id: str) -> str:
            """
            Başka bir bankaya para gönderme (EFT) işlemi yapar.
            Kullanıcı EFT yapmak istediğinde bu aracı kullanın.

            Args:
                iban: Hedef IBAN numarası (TR ile başlamalı)
                amount: Gönderilecek tutar
                customer_id: Müşteri kimlik numarası (11 haneli)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

            # Validate IBAN format
            if not iban or not iban.startswith("TR"):
                return "Geçersiz IBAN formatı. IBAN TR ile başlamalıdır (örn: TR123456789012345678901234)."

            # Validate amount
            if amount <= 0:
                return "Geçersiz tutar. Pozitif bir miktar giriniz."

            try:
                result = self.account_service.execute_eft(
                    customer_id, iban, float(amount)
                )
                return result.get("message", "EFT işlemi başarıyla gerçekleşti.")
            except Exception as e:
                return f"EFT işlemi hatası: {str(e)}"

        @tool
        def execute_havale(account_number: str, amount: float, customer_id: str) -> str:
            """
            Aynı bankadaki başka bir hesaba para gönderme (Havale) işlemi yapar.
            Kullanıcı havale yapmak istediğinde bu aracı kullanın.

            Args:
                account_number: Hedef hesap numarası
                amount: Gönderilecek tutar
                customer_id: Müşteri kimlik numarası (11 haneli)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

            # Validate amount
            if amount <= 0:
                return "Geçersiz tutar. Pozitif bir miktar giriniz."

            try:
                result = self.account_service.execute_havale(
                    customer_id, account_number, float(amount)
                )
                return result.get("message", "Havale işlemi başarıyla gerçekleşti.")
            except Exception as e:
                return f"Havale işlemi hatası: {str(e)}"

        @tool
        def get_transaction_history(customer_id: str, limit: int = 10) -> str:
            """
            Müşterinin son işlemlerini getirir.
            Kullanıcı 'son işlemlerim', 'hesap hareketlerim',
            'işlem geçmişim' dediğinde bu aracı kullanın.

            Args:
                customer_id: Müşteri kimlik numarası (11 haneli)
                limit: Kaç işlem gösterileceği (varsayılan: 10)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                transactions = self.account_service.get_transaction_history(
                    customer_id, limit
                )
                if not transactions:
                    return "Son dönemde hiç işlem bulunamadı."

                result_lines = ["Son işlemleriniz:"]
                for txn in transactions:
                    result_lines.append(
                        f"- {txn['timestamp']}: {txn['type']} - "
                        f"{txn['amount']:,.2f} {txn['currency']} ({txn['status']})"
                    )
                return "\n".join(result_lines)
            except Exception as e:
                return f"İşlem geçmişi sorgulama hatası: {str(e)}"

        @tool
        def list_accounts(customer_id: str) -> str:
            """
            Müşterinin tüm hesaplarını listeler.
            Kullanıcı 'hesaplarım neler', 'tüm hesaplarım',
            'hangi hesaplarım var' dediğinde bu aracı kullanın.

            Args:
                customer_id: Müşteri kimlik numarası (11 haneli)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                accounts = self.account_service.list_customer_accounts(customer_id)
                if not accounts:
                    return "Hiç hesap bulunamadı."

                result_lines = ["Hesaplarınız:"]
                for account in accounts:
                    result_lines.append(
                        f"- {account['account_type']}: {account['balance']:,.2f} {account['currency']}"
                    )
                return "\n".join(result_lines)
            except Exception as e:
                return f"Hesap listeleme hatası: {str(e)}"

        @tool
        def pay_credit_card(customer_id: str, amount: float = None) -> str:
            """
            Kredi kartı borcu öder.
            Kullanıcı 'kredi kartı borcumu öde', 'kart borcunu yatır'
            dediğinde bu aracı kullanın.

            Args:
                customer_id: Müşteri kimlik numarası (11 haneli)
                amount: Ödenecek tutar (None = tam borç)
            """
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

            try:
                # Get current debt first
                debt_info = self.account_service.get_credit_card_debt(customer_id)
                current_debt = debt_info.get("debt", 0)

                if current_debt <= 0:
                    return "Kredi kartı borcunuz bulunmuyor."

                # If no amount specified, pay full debt
                if amount is None:
                    amount = current_debt

                # Validate amount against current debt
                if amount > current_debt:
                    return f"Ödeme tutarı borçtan fazla olamaz. Güncel borç: {current_debt:,.2f} {debt_info.get('currency', 'TRY')}"

                result = self.account_service.pay_credit_card(customer_id, amount)
                
                # Check if it returned an error (like invalid amount)
                if isinstance(result, dict) and result.get("status") == "error":
                    return result.get("message", "Geçersiz işlem.")

                return result.get(
                    "message", "Kredi kartı ödemesi başarıyla gerçekleşti."
                )
            except Exception as e:
                return f"Kredi kartı ödeme hatası: {str(e)}"

        return [
            get_balance,
            get_credit_card_debt,
            execute_eft,
            execute_havale,
            get_transaction_history,
            list_accounts,
            pay_credit_card,
        ]
