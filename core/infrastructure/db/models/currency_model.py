# core/infrastructure/db/models/currency_model.py
"""
Currency ORM Model - نموذج العملات في قاعدة البيانات
✅ يدعم العملات المتعددة
✅ يدعم أسعار الصرف
✅ يدعم Optimistic Locking
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Boolean, Float, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC مع المنطقة الزمنية"""
    return datetime.now(timezone.utc)


class CurrencyModel(Base):
    """
    ORM Model للعملات
    
    الحقول:
        id: المعرف الفريد (UUID)
        code: كود العملة (3 أحرف، مثل USD, EUR, LBP)
        name: اسم العملة (مثل دولار أمريكي)
        symbol: رمز العملة (مثل $, €, ل.ل)
        decimal_places: عدد الخانات العشرية (مثال: 2 للدولار، 0 لليرة)
        is_active: هل العملة نشطة؟ (يمكن تعطيلها بدلاً من حذفها)
        is_base: هل هي العملة الأساسية للنظام؟
        exchange_rates: أسعار الصرف مخزنة كـ JSONB (مفتاح: كود العملة الهدف، قيمة: السعر)
        created_at, created_by: بيانات الإنشاء
        updated_at, updated_by: بيانات التحديث
        version: رقم الإصدار للتحكم في التزامن (Optimistic Locking)
    """
    
    __tablename__ = "currencies"
    
    # ========== الحقول الأساسية ==========
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4,
        doc="المعرف الفريد للعملة"
    )
    
    code: Mapped[str] = mapped_column(
        String(3), 
        unique=True, 
        nullable=False, 
        index=True,
        doc="كود العملة (مثل USD, EUR, LBP)"
    )
    
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        doc="اسم العملة (مثل دولار أمريكي)"
    )
    
    symbol: Mapped[str] = mapped_column(
        String(10), 
        default="",
        doc="رمز العملة (مثل $, €)"
    )
    
    decimal_places: Mapped[int] = mapped_column(
        Integer, 
        default=2,
        doc="عدد الخانات العشرية (مثال: 2 للدولار، 0 لليرة)"
    )
    
    # ========== حالة العملة ==========
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False,
        doc="هل العملة نشطة؟ (يمكن تعطيلها بدلاً من حذفها)"
    )
    
    is_base: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        doc="هل هي العملة الأساسية للنظام؟"
    )
    
    # ========== أسعار الصرف ==========
    exchange_rates: Mapped[Dict[str, float]] = mapped_column(
        JSONB, 
        default=dict,
        doc="أسعار الصرف (مفتاح: كود العملة الهدف، قيمة: سعر الصرف)"
    )
    
    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        nullable=False,
        doc="تاريخ الإنشاء"
    )
    
    created_by: Mapped[str] = mapped_column(
        String(100), 
        default="system", 
        nullable=False,
        doc="من قام بالإنشاء"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        onupdate=utc_now, 
        nullable=False,
        doc="تاريخ آخر تحديث"
    )
    
    updated_by: Mapped[str] = mapped_column(
        String(100), 
        default="system", 
        nullable=False,
        doc="من قام بآخر تحديث"
    )
    
    # ========== التحكم في التزامن (Optimistic Locking) ==========
    version: Mapped[int] = mapped_column(
        Integer, 
        default=1, 
        nullable=False,
        doc="رقم الإصدار - يستخدم للتحقق من التزامن"
    )
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        # فهرس مركب للبحث عن العملات النشطة
        Index("idx_currencies_code_active", "code", "is_active"),
        
        # فهرس للعملات الأساسية
        Index("idx_currencies_is_base", "is_base"),
        
        # فهرس للحالة النشطة
        Index("idx_currencies_active", "is_active"),
        
        # فهرس للبحث بالنص
        Index("idx_currencies_name_trgm", "name"),
        
        # التحقق من أن كود العملة هو 3 أحرف كبيرة
        CheckConstraint(
            "code ~ '^[A-Z]{3}$'",
            name="chk_currency_code_format"
        ),
        
        # التحقق من أن عدد الخانات العشرية بين 0 و 4
        CheckConstraint(
            "decimal_places BETWEEN 0 AND 4",
            name="chk_decimal_places_range"
        ),
        
        # لا يمكن أن يكون هناك أكثر من عملة أساسية واحدة (يتم فرضه في التطبيق)
        # ولكن نضيف قيد فريد جزئي لضمان ذلك
        Index("idx_currencies_unique_base", "is_base", postgresql_where="is_base = true", unique=True),
    )
    
    def __repr__(self) -> str:
        """تمثيل نصي للنموذج"""
        return f"CurrencyModel(id={self.id}, code={self.code}, name={self.name}, is_active={self.is_active}, is_base={self.is_base})"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل النموذج إلى قاموس"""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'decimal_places': self.decimal_places,
            'is_active': self.is_active,
            'is_base': self.is_base,
            'exchange_rates': self.exchange_rates,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CurrencyModel':
        """إنشاء نموذج من قاموس"""
        return cls(
            id=data.get('id', uuid4()),
            code=data['code'],
            name=data['name'],
            symbol=data.get('symbol', ''),
            decimal_places=data.get('decimal_places', 2),
            is_active=data.get('is_active', True),
            is_base=data.get('is_base', False),
            exchange_rates=data.get('exchange_rates', {}),
            created_by=data.get('created_by', 'system'),
            updated_by=data.get('updated_by', 'system'),
            version=data.get('version', 1),
        )


# ========== نموذج بديل: جدول منفصل لأسعار الصرف (للأنظمة الأكثر تعقيداً) ==========

class ExchangeRateModel(Base):
    """
    نموذج منفصل لأسعار الصرف - يمكن استخدامه بدلاً من JSONB
    هذا مفيد إذا كنت بحاجة إلى:
        1. تتبع تاريخ أسعار الصرف
        2. تقارير تفصيلية عن التغيرات
        3. استعلامات معقدة على أسعار الصرف
    """
    __tablename__ = "exchange_rates"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # العملة المصدر (من)
    from_currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="معرف العملة المصدر"
    )
    
    # العملة الهدف (إلى)
    to_currency_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="معرف العملة الهدف"
    )
    
    # سعر الصرف
    rate: Mapped[float] = mapped_column(
        Float, 
        nullable=False,
        doc="سعر الصرف (كم من العملة الهدف يعادل 1 من العملة المصدر)"
    )
    
    # التاريخ (للتتبع التاريخي)
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ سريان هذا السعر"
    )
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # الفهارس
    __table_args__ = (
        Index("idx_exchange_rates_from_to", "from_currency_id", "to_currency_id"),
        Index("idx_exchange_rates_date", "effective_date"),
        # قيد فريد: لا يمكن أن يكون هناك سعرين مختلفين لنفس الزوج في نفس التاريخ
        Index("idx_exchange_rates_unique", "from_currency_id", "to_currency_id", "effective_date", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"ExchangeRateModel(from={self.from_currency_id}, to={self.to_currency_id}, rate={self.rate})"


# ========== إضافة العلاقات إلى CurrencyModel (إذا كنت تريد استخدام جدول منفصل) ==========

# إذا كنت تريد استخدام نموذج ExchangeRateModel المنفصل،
# يمكنك إضافة العلاقات التالية إلى CurrencyModel:

# from_rates: Mapped[List["ExchangeRateModel"]] = relationship(
#     "ExchangeRateModel",
#     foreign_keys=[ExchangeRateModel.from_currency_id],
#     cascade="all, delete-orphan"
# )
# 
# to_rates: Mapped[List["ExchangeRateModel"]] = relationship(
#     "ExchangeRateModel",
#     foreign_keys=[ExchangeRateModel.to_currency_id]
# )