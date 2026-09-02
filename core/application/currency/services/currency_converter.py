# core/application/currency/services/currency_converter.py
"""
Currency Converter - خدمة تحويل العملات
"""

import logging
from typing import Optional, Dict, Any  # ✅ إضافة Dict, Any
from decimal import Decimal

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.interfaces import ICurrencyRepository
from .exchange_rate_service import ExchangeRateService

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """
    خدمة تحويل العملات - تحويل المبالغ بين العملات المختلفة
    """
    
    def __init__(self, currency_repo: ICurrencyRepository, exchange_rate_service: ExchangeRateService):
        self._currency_repo = currency_repo
        self._exchange_rate_service = exchange_rate_service
    
    def convert(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """
        تحويل مبلغ من عملة إلى أخرى
        
        Args:
            amount: المبلغ المراد تحويله
            from_currency: كود العملة المصدر
            to_currency: كود العملة الهدف
        
        Returns:
            المبلغ المحول أو None
        """
        if from_currency == to_currency:
            return amount
        
        rate = self._exchange_rate_service.get_rate(from_currency, to_currency)
        if rate is None:
            return None
        
        return amount * rate
    
    def convert_with_rounding(self, amount: float, from_currency: str, to_currency: str, decimal_places: int = 2) -> Optional[float]:
        """
        تحويل مبلغ مع تقريب النتيجة
        
        Args:
            amount: المبلغ المراد تحويله
            from_currency: كود العملة المصدر
            to_currency: كود العملة الهدف
            decimal_places: عدد الخانات العشرية للتقريب
        
        Returns:
            المبلغ المحول مقرباً أو None
        """
        result = self.convert(amount, from_currency, to_currency)
        if result is None:
            return None
        
        return round(result, decimal_places)
    
    def convert_money(self, amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        تحويل مبلغ مع معلومات إضافية
        
        Returns:
            قاموس يحتوي على المبلغ المحول، العملات، وسعر الصرف المستخدم
        """
        rate = self._exchange_rate_service.get_rate(from_currency, to_currency)
        if rate is None:
            return {
                "success": False,
                "message": f"No exchange rate found for {from_currency} to {to_currency}"
            }
        
        converted = amount * rate
        
        return {
            "success": True,
            "from_amount": amount,
            "from_currency": from_currency,
            "to_amount": converted,
            "to_currency": to_currency,
            "rate": rate,
        }