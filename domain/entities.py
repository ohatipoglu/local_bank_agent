# domain/entities.py

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    """Müşteri (Kullanıcı) Varlığı (Entity)"""
    id: str
    tc_kimlik: str
    first_name: str
    last_name: str
    phone_number: str

@dataclass
class Account:
    """Banka Hesabı Varlığı"""
    account_number: str
    customer_id: str
    account_type: str # Vadesiz, Vadeli vb.
    balance: float
    currency: str # TRY, USD, EUR vb.
    iban: str

@dataclass
class CreditCard:
    """Kredi Kartı Varlığı"""
    card_number: str
    customer_id: str
    card_name: str # Platinum, Gold vb.
    limit: float
    current_debt: float
    currency: str
    due_date: str # Son ödeme tarihi (örn: 2024-05-15)

@dataclass
class Transaction:
    """Banka İşlemi Varlığı (EFT, Havale vb.)"""
    transaction_id: str
    source_account: str
    target_account: str # Hedef IBAN veya Hesap Numarası
    amount: float
    currency: str
    timestamp: datetime
    type: str # EFT, HAVALE, KART_ODEME vb.
    status: str # BASARILI, BEKLEMEDE, IPTAL
