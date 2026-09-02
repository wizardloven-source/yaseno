# core/domain/products/events.py
"""
Domain Events for Products Context
أحداث المجال للمنتجات - تسجيل الأحداث الهامة في دورة حياة المنتج
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent, Money
from .value_objects import ProductId, ProductCode, ProductStatus, StockMovementType


def _aware_utc_now() -> datetime:
    """دالة مساعدة لإنشاء توقيت UTC واعي بالمنطقة الزمنية"""
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProductCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء منتج جديد"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    unit_price: Money
    category: Optional[str]
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.product.created"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "unit_price": str(self.unit_price.amount),
            "currency": self.unit_price.currency,
            "category": self.category,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class ProductUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث بيانات المنتج"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.product.updated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "changes": self.changes,
            "updated_by": self.updated_by,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class ProductDeletedEvent(BaseDomainEvent):
    """يُرفع عند حذف/تعطيل منتج"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.product.deleted"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "deleted_by": self.deleted_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class ProductReactivatedEvent(BaseDomainEvent):
    """يُرفع عند إعادة تنشيط منتج معطل"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    reactivated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.product.reactivated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "reactivated_by": self.reactivated_by,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class StockUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تغيير كمية المخزون"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    old_quantity: int
    new_quantity: int
    quantity_change: int
    movement_type: StockMovementType
    reason: str
    reference_id: Optional[str]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.stock.updated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "old_quantity": self.old_quantity,
            "new_quantity": self.new_quantity,
            "quantity_change": self.quantity_change,
            "movement_type": self.movement_type.value,
            "reason": self.reason,
            "reference_id": self.reference_id,
            "updated_by": self.updated_by,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class LowStockAlertEvent(BaseDomainEvent):
    """يُرفع عندما يصل المخزون إلى حد التحذير"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    current_quantity: int
    threshold: int
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.stock.low_alert"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "current_quantity": self.current_quantity,
            "threshold": self.threshold,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class OutOfStockEvent(BaseDomainEvent):
    """يُرفع عندما يصبح المخزون صفراً"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.stock.out_of_stock"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "occurred_at": self.occurred_at.isoformat(),
        }


@dataclass(frozen=True)
class PriceChangedEvent(BaseDomainEvent):
    """يُرفع عند تغيير سعر المنتج"""
    product_id: ProductId
    product_code: ProductCode
    product_name: str
    old_price: Money
    new_price: Money
    changed_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "products.price.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "product_id": str(self.product_id),
            "product_code": str(self.product_code),
            "product_name": self.product_name,
            "old_price": str(self.old_price.amount),
            "new_price": str(self.new_price.amount),
            "currency": self.new_price.currency,
            "changed_by": self.changed_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat(),
        }