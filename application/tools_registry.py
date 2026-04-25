"""
LangChain tool definitions for banking operations.
Registry pattern for dynamic tool injection with dependency injection.

Security: customer_id is passed via ContextVar, never through LLM-visible
tool parameters, preventing prompt injection attacks.
"""

from collections.abc import Callable
from contextvars import ContextVar

from langchain_core.tools import tool

from domain.interfaces import IAccountService

# ContextVar that holds the authenticated customer_id for the current request.
# Set by LangChainBankAgent.handle_turn() before invoking the agent.
# Each thread/task gets its own isolated copy via asyncio.to_thread context propagation.
_current_customer_id: ContextVar[str] = ContextVar("current_customer_id", default="")


def set_customer_id(customer_id: str):
    """Set customer_id for the current execution context. Returns the reset token."""
    return _current_customer_id.set(customer_id)


def reset_customer_id(token) -> None:
    """Reset customer_id to the previous value using the token from set_customer_id."""
    _current_customer_id.reset(token)


def _get_customer_id() -> str:
    return _current_customer_id.get()


class BankToolsRegistry:
    """
    Registry for banking operation tools.

    Provides LangChain-compatible tools that wrap the account service
    abstraction. customer_id is read from a ContextVar (not from LLM parameters)
    to prevent prompt injection.

    Tools:
    - get_balance: Query account balance
    - get_credit_card_debt: Query credit card debt
    - execute_eft: Transfer to another bank (via IBAN)
    - execute_havale: Same-bank transfer (via account number)
    - get_transaction_history: Recent transaction list
    - list_accounts: All customer accounts
    - pay_credit_card: Pay credit card bill
    """

    def __init__(self, account_service: IAccountService):
        self.account_service = account_service
        self.tools = self._initialize_tools()

    def get_tools(self) -> list[Callable]:
        return self.tools

    def _initialize_tools(self) -> list[Callable]:
        """Define and register all banking tools."""

        @tool
        def get_balance() -> str:
            """
            Müşterinin vadesiz hesap bakiyesini sorgular.
            Kullanıcı 'ne kadar param var', 'bakiyem nedir',
            'hesabımda ne kadar var' dediğinde bu aracı kullanın.
            """
            customer_id = _get_customer_id()
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
        def get_credit_card_debt() -> str:
            """
            Müşterinin güncel kredi kartı borcunu ve son ödeme tarihini sorgular.
            Kullanıcı 'kredi kartı borcum ne kadar', 'kart ekstresi',
            'son ödeme tarihi ne zaman' dediğinde bu aracı kullanın.
            """
            customer_id = _get_customer_id()
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
        def execute_eft(iban: str, amount: float) -> str:
            """
            Başka bir bankaya para gönderme (EFT) işlemi yapar.
            Kullanıcı EFT yapmak istediğinde bu aracı kullanın.

            Args:
                iban: Hedef IBAN numarası (TR ile başlamalı)
                amount: Gönderilecek tutar
            """
            customer_id = _get_customer_id()
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

            if not iban or not iban.startswith("TR"):
                return "Geçersiz IBAN formatı. IBAN TR ile başlamalıdır (örn: TR123456789012345678901234)."

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
        def execute_havale(account_number: str, amount: float) -> str:
            """
            Aynı bankadaki başka bir hesaba para gönderme (Havale) işlemi yapar.
            Kullanıcı havale yapmak istediğinde bu aracı kullanın.

            Args:
                account_number: Hedef hesap numarası
                amount: Gönderilecek tutar
            """
            customer_id = _get_customer_id()
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

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
        def get_transaction_history(limit: int = 5) -> str:
            """
            Müşterinin son işlemlerini getirir.
            Kullanıcı 'son işlemlerim', 'hesap hareketlerim',
            'işlem geçmişim' dediğinde bu aracı kullanın.

            Args:
                limit: Kaç işlem gösterileceği (varsayılan: 5)
            """
            customer_id = _get_customer_id()
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                transactions = self.account_service.get_transaction_history(
                    customer_id, limit
                )
                if not transactions:
                    return "Son dönemde hiç işlem bulunamadı."

                # TTS-friendly: plain sentences instead of bullet list
                parts = []
                for txn in transactions:
                    parts.append(
                        f"{txn['timestamp']} tarihinde {txn['type']} işlemi, "
                        f"{txn['amount']:,.2f} {txn['currency']}, durum: {txn['status']}"
                    )
                intro = f"Son {len(transactions)} işleminiz şu şekilde:"
                return intro + ". " + ". ".join(parts) + "."
            except Exception as e:
                return f"İşlem geçmişi sorgulama hatası: {str(e)}"

        @tool
        def list_accounts() -> str:
            """
            Müşterinin tüm hesaplarını listeler.
            Kullanıcı 'hesaplarım neler', 'tüm hesaplarım',
            'hangi hesaplarım var' dediğinde bu aracı kullanın.
            """
            customer_id = _get_customer_id()
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."
            try:
                accounts = self.account_service.list_customer_accounts(customer_id)
                if not accounts:
                    return "Hiç hesap bulunamadı."

                # TTS-friendly: plain sentences
                parts = []
                for account in accounts:
                    parts.append(
                        f"{account['account_type']} hesabınızda "
                        f"{account['balance']:,.2f} {account['currency']} bulunmaktadır"
                    )
                return ". ".join(parts) + "."
            except Exception as e:
                return f"Hesap listeleme hatası: {str(e)}"

        @tool
        def pay_credit_card(amount: float = None) -> str:
            """
            Kredi kartı borcu öder.
            Kullanıcı 'kredi kartı borcumu öde', 'kart borcunu yatır'
            dediğinde bu aracı kullanın.

            Args:
                amount: Ödenecek tutar (belirtilmezse tam borç ödenir)
            """
            customer_id = _get_customer_id()
            if not self.account_service:
                return "Servis hatası: Hesap servisine ulaşılamıyor."

            try:
                debt_info = self.account_service.get_credit_card_debt(customer_id)
                current_debt = debt_info.get("debt", 0)

                if current_debt <= 0:
                    return "Kredi kartı borcunuz bulunmuyor."

                if amount is None:
                    amount = current_debt

                if amount > current_debt:
                    return (
                        f"Ödeme tutarı borçtan fazla olamaz. "
                        f"Güncel borç: {current_debt:,.2f} {debt_info.get('currency', 'TRY')}"
                    )

                result = self.account_service.pay_credit_card(customer_id, amount)

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
