from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any
from uuid import UUID, uuid4

from .value_objects import CurrencyCode, ExchangeRate


@dataclass
class Currency:
    """
    AGGREGATE ROOT - العملة
    تمثل عملة مدعومة في النظام مع أسعار صرفها
    """
    id: UUID = field(default_factory=uuid4)
    code: CurrencyCode = field(default_factory=lambda: CurrencyCode(""))
    name: str = ""
    symbol: str = ""
    decimal_places: int = 2
    is_active: bool = True
    is_base: bool = False  # العملة الأساسية للنظام (مثل USD)
    exchange_rates: List[ExchangeRate] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"      # ✅ إضافة هذا الحقل
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = "system"      # ✅ إضافة هذا الحقل
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        symbol: str = "",
        decimal_places: int = 2,
        is_base: bool = False,
        created_by: str = "system"
    ) -> 'Currency':
        """مصنع لإنشاء عملة جديدة"""
        currency = cls(
            code=CurrencyCode(code.upper()),
            name=name,
            symbol=symbol,
            decimal_places=decimal_places,
            is_base=is_base,
            created_by=created_by,      # ✅ الآن هذا الحقل موجود
            updated_by=created_by       # ✅ الآن هذا الحقل موجود
        )
        
        # إضافة حدث المجال
        from .events import CurrencyCreatedEvent
        currency._events.append(CurrencyCreatedEvent(
            currency_id=currency.id,
            code=currency.code.value,
            name=currency.name,
            created_by=created_by
        ))
        
        return currency
    
    def update(
        self,
        name: Optional[str] = None,
        symbol: Optional[str] = None,
        decimal_places: Optional[int] = None,
        is_active: Optional[bool] = None,
        updated_by: str = "system"
    ) -> None:
        """تحديث بيانات العملة"""
        old_name = self.name
        if name and name != self.name:
            self.name = name
        if symbol is not None:
            self.symbol = symbol
        if decimal_places is not None:
            self.decimal_places = decimal_places
        if is_active is not None:
            self.is_active = is_active
        
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by    # ✅ تحديث الحقل
        self.version += 1
        
        # إضافة حدث المجال
        from .events import CurrencyUpdatedEvent
        self._events.append(CurrencyUpdatedEvent(
            currency_id=self.id,
            code=self.code.value,
            old_name=old_name,
            new_name=self.name,
            updated_by=updated_by
        ))
    
    def set_exchange_rate(self, to_currency_code: str, rate: float, updated_by: str = "system") -> None:
        """تعيين أو تحديث سعر الصرف لعملة أخرى"""
        to_currency = CurrencyCode(to_currency_code.upper())
        
        # البحث عن سعر الصرف الموجود
        for i, er in enumerate(self.exchange_rates):
            if er.to_currency == to_currency:
                # تحديث السعر الموجود
                self.exchange_rates[i] = ExchangeRate(self.code, to_currency, rate)
                break
        else:
            # إضافة سعر صرف جديد
            self.exchange_rates.append(ExchangeRate(self.code, to_currency, rate))
        
        self.updated_at = datetime.utcnow()
        self.updated_by = updated_by    # ✅ تحديث الحقل
        self.version += 1
        
        from .events import ExchangeRateUpdatedEvent
        self._events.append(ExchangeRateUpdatedEvent(
            from_currency=self.code.value,
            to_currency=to_currency.value,
            new_rate=rate,
            updated_by=updated_by
        ))
    
    def get_exchange_rate(self, to_currency_code: str) -> Optional[float]:
        """الحصول على سعر الصرف لعملة أخرى"""
        to_currency = CurrencyCode(to_currency_code.upper())
        for er in self.exchange_rates:
            if er.to_currency == to_currency:
                return er.rate
        return None
    
    def convert(self, amount: float, to_currency_code: str) -> Optional[float]:
        """تحويل المبلغ من هذه العملة إلى عملة أخرى"""
        rate = self.get_exchange_rate(to_currency_code)
        if rate is None:
            return None
        return amount * rate
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events