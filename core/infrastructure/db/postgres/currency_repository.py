# core/infrastructure/db/postgres/currency_repository.py
"""
PostgreSQL Repository for Currency - مستودع العملات
✅ يدعم Optimistic Locking
✅ يدعم البحث المتقدم
✅ يدعم Pagination
"""

import logging  # ✅ إضافة هذا السطر
from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode, ExchangeRate
from core.domain.currency.interfaces import ICurrencyRepository
from core.domain.currency.exceptions import CurrencyCodeAlreadyExistsError
from core.shared.exceptions import ConcurrentModificationError
from core.infrastructure.db.models.currency_model import CurrencyModel

# تعيين logger
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


def _model_to_domain(model: CurrencyModel) -> Currency:
    """تحويل ORM Model إلى Domain Entity"""
    if not model:
        return None
    
    currency = Currency(
        id=model.id,
        code=CurrencyCode(model.code),
        name=model.name,
        symbol=model.symbol or "",
        decimal_places=model.decimal_places,
        is_active=model.is_active,
        is_base=model.is_base,
        created_at=model.created_at,
        created_by=model.created_by or "system",
        updated_at=model.updated_at,
        updated_by=model.updated_by or "system",
        version=model.version
    )
    
    # إعادة بناء أسعار الصرف
    if model.exchange_rates:
        er_data = model.exchange_rates
        if isinstance(er_data, list):
            for er in er_data:
                if isinstance(er, dict):
                    to_code = er.get('to_currency', er.get('to', ''))
                    rate_val = er.get('rate', 0)
                    if to_code:
                        currency.exchange_rates.append(ExchangeRate(
                            from_currency=CurrencyCode(model.code),
                            to_currency=CurrencyCode(to_code),
                            rate=float(rate_val)
                        ))
        elif isinstance(er_data, dict):
            for to_code, rate in er_data.items():
                currency.exchange_rates.append(ExchangeRate(
                    from_currency=CurrencyCode(model.code),
                    to_currency=CurrencyCode(to_code),
                    rate=float(rate)
                ))
    
    return currency


def _domain_to_model(currency: Currency) -> CurrencyModel:
    """تحويل Domain Entity إلى ORM Model"""
    # بناء قاموس أسعار الصرف
    exchange_rates = {}
    for er in currency.exchange_rates:
        exchange_rates[er.to_currency.value] = er.rate
    
    return CurrencyModel(
        id=currency.id,
        code=currency.code.value,
        name=currency.name,
        symbol=currency.symbol,
        decimal_places=currency.decimal_places,
        is_active=currency.is_active,
        is_base=currency.is_base,
        exchange_rates=exchange_rates,
        created_at=currency.created_at,
        created_by=currency.created_by,
        updated_at=currency.updated_at,
        updated_by=currency.updated_by,
        version=currency.version
    )


class PostgresCurrencyRepository(ICurrencyRepository):
    """
    PostgreSQL implementation of ICurrencyRepository
    
    الميزات:
        1. Optimistic Locking عبر الـ version
        2. بحث متقدم بالكود أو الاسم
        3. Pagination للقوائم الكبيرة
        4. معالجة التكرارات
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # ========== العمليات الأساسية ==========
    
    def save(self, currency: Currency) -> None:
        """
        حفظ العملة (جديدة أو محدثة) مع Optimistic Locking
        
        ✅ يستخدم UPDATE مع شرط الإصدار للتحقق من التزامن
        """
        existing = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.id == currency.id)
        ).scalar_one_or_none()
        
        if existing:
            # ✅ التحديث مع التحقق من الإصدار (Optimistic Locking)
            # نسخة الكيان قد تكون مساوية لنسخة قاعدة البيانات (تعديل مباشر)
            # أو أكبر بواحد إذا زادها أسلوب دومين (تحديث عبر طريقة كائنية)
            if existing.version != currency.version and existing.version != currency.version - 1:
                raise ConcurrentModificationError(
                    "Currency",
                    str(currency.id),
                    currency.version,
                    existing.version
                )
            expected_version = existing.version
            now = utc_now()
            new_version = existing.version + 1
            
            result = self._session.execute(
                update(CurrencyModel)
                .where(
                    CurrencyModel.id == currency.id,
                    CurrencyModel.version == expected_version  # ✅ شرط التحقق
                )
                .values(
                    name=currency.name,
                    symbol=currency.symbol,
                    decimal_places=currency.decimal_places,
                    is_active=currency.is_active,
                    is_base=currency.is_base,
                    exchange_rates={er.to_currency.value: er.rate for er in currency.exchange_rates},
                    updated_at=now,
                    updated_by=currency.updated_by,
                    version=new_version
                )
            )
            
            # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Currency",
                    str(currency.id),
                    currency.version,
                    existing.version
                )
            
            # ✅ تحديث الكائن المحلي بالنسخة الجديدة
            currency.version = new_version
            currency.updated_at = now
            
        else:
            # ✅ التحقق من عدم وجود كود مكرر
            duplicate = self._session.execute(
                select(CurrencyModel).where(CurrencyModel.code == currency.code.value)
            ).scalar_one_or_none()
            
            if duplicate:
                raise CurrencyCodeAlreadyExistsError(currency.code.value)
            
            # إنشاء عملة جديدة
            model = _domain_to_model(currency)
            self._session.add(model)
            self._session.flush()
            currency.version = 1  # الإصدار الأولي
    
    def get_by_id(self, currency_id: UUID) -> Optional[Currency]:
        """الحصول على عملة بواسطة المعرف"""
        model = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.id == currency_id)
        ).scalar_one_or_none()
        return _model_to_domain(model) if model else None
    
    def get_by_code(self, code: CurrencyCode) -> Optional[Currency]:
        """الحصول على عملة بواسطة الكود"""
        model = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.code == code.value)
        ).scalar_one_or_none()
        return _model_to_domain(model) if model else None
    
    def get_all(self, include_inactive: bool = False) -> List[Currency]:
        """الحصول على جميع العملات"""
        query = select(CurrencyModel).order_by(CurrencyModel.code)
        if not include_inactive:
            query = query.where(CurrencyModel.is_active == True)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def get_base_currency(self) -> Optional[Currency]:
        """الحصول على العملة الأساسية"""
        model = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.is_base == True)
        ).scalar_one_or_none()
        return _model_to_domain(model) if model else None
    
    def delete(self, currency_id: UUID) -> bool:
        """حذف عملة (حذف فعلي - استخدم بحذر)"""
        model = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.id == currency_id)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        self._session.delete(model)
        return True
    
    # ========== عمليات إضافية متقدمة ==========
    
    def get_by_codes(self, codes: List[str]) -> List[Currency]:
        """الحصول على عملات متعددة بواسطة الأكواد"""
        if not codes:
            return []
        
        models = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.code.in_(codes))
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def get_active_currencies(self) -> List[Currency]:
        """الحصول على العملات النشطة فقط"""
        return self.get_all(include_inactive=False)
    
    def get_inactive_currencies(self) -> List[Currency]:
        """الحصول على العملات غير النشطة"""
        models = self._session.execute(
            select(CurrencyModel).where(CurrencyModel.is_active == False)
        ).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def search_currencies(
        self,
        search_text: str,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Currency]:
        """
        البحث عن العملات بالكود أو الاسم
        
        Args:
            search_text: نص البحث
            include_inactive: تضمين العملات غير النشطة
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        """
        search_pattern = f"%{search_text}%"
        
        conditions = [
            CurrencyModel.code.ilike(search_pattern),
            CurrencyModel.name.ilike(search_pattern),
        ]
        
        query = select(CurrencyModel).where(or_(*conditions))
        
        if not include_inactive:
            query = query.where(CurrencyModel.is_active == True)
        
        query = query.order_by(CurrencyModel.code).limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def count_currencies(self, include_inactive: bool = False) -> int:
        """حساب عدد العملات"""
        query = select(func.count()).select_from(CurrencyModel)
        if not include_inactive:
            query = query.where(CurrencyModel.is_active == True)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_active_currencies(self) -> int:
        """حساب عدد العملات النشطة"""
        return self.count_currencies(include_inactive=False)
    
    def get_currencies_with_exchange_rates(self) -> List[Currency]:
        """الحصول على جميع العملات التي لديها أسعار صرف محددة"""
        models = self._session.execute(
            select(CurrencyModel).where(
                CurrencyModel.exchange_rates != {}
            )
        ).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    def set_base_currency(self, currency_id: UUID, updated_by: str = "system") -> bool:
        """
        تعيين عملة كعملة أساسية (يتم تعطيل العملات الأساسية الأخرى تلقائياً)
        
        Args:
            currency_id: معرف العملة المراد جعلها أساسية
            updated_by: من قام بالتغيير
        
        Returns:
            True إذا تم التغيير بنجاح
        """
        now = utc_now()
        
        # تعطيل جميع العملات الأساسية الأخرى
        self._session.execute(
            update(CurrencyModel)
            .where(CurrencyModel.is_base == True)
            .values(
                is_base=False,
                updated_at=now,
                updated_by=updated_by,
                version=CurrencyModel.version + 1
            )
        )
        
        # تعيين العملة الجديدة كأساس
        result = self._session.execute(
            update(CurrencyModel)
            .where(CurrencyModel.id == currency_id)
            .values(
                is_base=True,
                updated_at=now,
                updated_by=updated_by,
                version=CurrencyModel.version + 1
            )
        )
        
        return result.rowcount > 0
    
    def get_exchange_rate(self, from_code: str, to_code: str) -> Optional[float]:
        """
        الحصول على سعر الصرف بين عملتين
        
        Args:
            from_code: كود العملة المصدر
            to_code: كود العملة الهدف
        
        Returns:
            سعر الصرف أو None
        """
        currency = self.get_by_code(CurrencyCode(from_code.upper()))
        if not currency:
            return None
        
        for er in currency.exchange_rates:
            if er.to_currency.value == to_code.upper():
                return er.rate
        
        return None
    
    def update_exchange_rate(
        self,
        from_code: str,
        to_code: str,
        rate: float,
        updated_by: str = "system"
    ) -> bool:
        """
        تحديث سعر الصرف لعملة
        
        Args:
            from_code: كود العملة المصدر
            to_code: كود العملة الهدف
            rate: سعر الصرف الجديد
            updated_by: من قام بالتحديث
        
        Returns:
            True إذا تم التحديث بنجاح
        """
        currency = self.get_by_code(CurrencyCode(from_code.upper()))
        if not currency:
            return False
        
        # تحديث سعر الصرف
        currency.set_exchange_rate(to_code.upper(), rate, updated_by)
        self.save(currency)
        
        return True
    
    def bulk_save(self, currencies: List[Currency]) -> int:
        """
        حفظ多条 عملات دفعة واحدة
        
        Args:
            currencies: قائمة العملات للحفظ
        
        Returns:
            عدد العملات المحفوظة
        """
        saved_count = 0
        for currency in currencies:
            try:
                self.save(currency)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving currency {currency.code.value}: {e}")
        
        return saved_count
    
    def get_currencies_dict(self, include_inactive: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        الحصول على العملات كقاموس (مفيد للتخزين المؤقت)
        
        Returns:
            قاموس بمفتاح كود العملة وقيمة بيانات العملة
        """
        currencies = self.get_all(include_inactive=include_inactive)
        
        result = {}
        for currency in currencies:
            result[currency.code.value] = {
                'id': str(currency.id),
                'code': currency.code.value,
                'name': currency.name,
                'symbol': currency.symbol,
                'decimal_places': currency.decimal_places,
                'is_active': currency.is_active,
                'is_base': currency.is_base,
                'exchange_rates': {
                    er.to_currency.value: er.rate
                    for er in currency.exchange_rates
                }
            }
        
        return result