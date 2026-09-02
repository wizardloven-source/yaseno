# core/application/currency/services/exchange_rate_service.py
"""
Exchange Rate Service - خدمة أسعار الصرف
"""

import logging
from typing import Optional, Dict, Any  # ✅ إضافة Dict
from decimal import Decimal

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.interfaces import ICurrencyRepository

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """
    خدمة أسعار الصرف - إدارة أسعار الصرف بين العملات
    """
    
    def __init__(self, currency_repo: ICurrencyRepository, uow):
        self._currency_repo = currency_repo
        self._uow = uow
    
    def get_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        الحصول على سعر الصرف بين عملتين
        
        Args:
            from_currency: كود العملة المصدر
            to_currency: كود العملة الهدف
        
        Returns:
            سعر الصرف أو None
        """
        if from_currency == to_currency:
            return 1.0
        
        currency = self._currency_repo.get_by_code(CurrencyCode(from_currency))
        if not currency:
            return None
        
        return currency.get_exchange_rate(to_currency)
    
    def set_rate(self, from_currency: str, to_currency: str, rate: float, updated_by: str = "system") -> bool:
        """
        تعيين سعر الصرف بين عملتين
        
        Args:
            from_currency: كود العملة المصدر
            to_currency: كود العملة الهدف
            rate: سعر الصرف
            updated_by: من قام بالتحديث
        
        Returns:
            True إذا تم التحديث بنجاح
        """
        currency = self._currency_repo.get_by_code(CurrencyCode(from_currency))
        if not currency:
            return False
        
        currency.set_exchange_rate(to_currency, rate, updated_by)
        self._currency_repo.save(currency)
        return True
    
    def fetch_latest_rates(self) -> Dict[str, float]:
        """
        جلب أحدث أسعار الصرف من مصدر خارجي
        
        Returns:
            قاموس {عملة: سعر}
        """
        # TODO: تنفيذ جلب من API خارجي
        # مؤقتاً: إرجاع أسعار افتراضية
        return {
            "EUR": 0.85,
            "GBP": 0.73,
            "LBP": 15000.0,
        }
    
    def update_all_rates(self, rates: Dict[str, float], updated_by: str = "system") -> int:
        """
        تحديث جميع أسعار الصرف
        
        Args:
            rates: قاموس {عملة: سعر}
            updated_by: من قام بالتحديث
        
        Returns:
            عدد العملات المحدثة
        """
        updated_count = 0
        for currency_code, rate in rates.items():
            if self.set_rate("USD", currency_code, rate, updated_by):
                updated_count += 1
        
        return updated_count