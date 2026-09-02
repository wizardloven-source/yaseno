# core/domain/tax/events.py
"""
Tax Events - أحداث مجال الضرائب
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import TaxId, TaxCode, TaxRate, TaxCalculationResult


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث القواعد الضريبية
# =============================================================================

@dataclass(frozen=True)
class TaxRuleCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء قاعدة ضريبية جديدة"""
    tax_id: TaxId
    tax_code: TaxCode
    tax_name: str
    rate: TaxRate
    is_compound: bool = False
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.rule.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "tax_id": str(self.tax_id),
            "tax_code": str(self.tax_code),
            "tax_name": self.tax_name,
            "rate": str(self.rate),
            "is_compound": self.is_compound,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxRuleUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث قاعدة ضريبية"""
    tax_id: TaxId
    tax_code: TaxCode
    changes: Dict[str, Any]
    updated_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.rule.updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "tax_id": str(self.tax_id),
            "tax_code": str(self.tax_code),
            "changes": self.changes,
            "updated_by": self.updated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxRuleActivatedEvent(BaseDomainEvent):
    """يُرفع عند تفعيل قاعدة ضريبية"""
    tax_id: TaxId
    tax_code: TaxCode
    activated_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.rule.activated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "tax_id": str(self.tax_id),
            "tax_code": str(self.tax_code),
            "activated_by": self.activated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxRuleDeactivatedEvent(BaseDomainEvent):
    """يُرفع عند تعطيل قاعدة ضريبية"""
    tax_id: TaxId
    tax_code: TaxCode
    deactivated_by: str = "system"
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.rule.deactivated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "tax_id": str(self.tax_id),
            "tax_code": str(self.tax_code),
            "deactivated_by": self.deactivated_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث حساب الضريبة
# =============================================================================

@dataclass(frozen=True)
class TaxCalculatedEvent(BaseDomainEvent):
    """يُرفع عند حساب ضريبة"""
    invoice_id: Optional[str]
    taxable_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str = "USD"
    breakdown: Dict[str, Decimal] = field(default_factory=dict)
    rules_applied: List[str] = field(default_factory=list)
    calculation_type: str = "exclusive"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.calculated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": self.invoice_id,
            "taxable_amount": str(self.taxable_amount),
            "tax_amount": str(self.tax_amount),
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "breakdown": {k: str(v) for k, v in self.breakdown.items()},
            "rules_applied": self.rules_applied,
            "calculation_type": self.calculation_type,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxExemptionAppliedEvent(BaseDomainEvent):
    """يُرفع عند تطبيق إعفاء ضريبي"""
    invoice_id: Optional[str]
    exemption_id: str
    exemption_code: str
    exempted_amount: Decimal
    exempted_tax: Decimal
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.exemption.applied"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": self.invoice_id,
            "exemption_id": self.exemption_id,
            "exemption_code": self.exemption_code,
            "exempted_amount": str(self.exempted_amount),
            "exempted_tax": str(self.exempted_tax),
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث المجموعات الضريبية
# =============================================================================

@dataclass(frozen=True)
class TaxGroupCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء مجموعة ضرائب جديدة"""
    group_id: str
    group_code: str
    group_name: str
    rule_count: int
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.group.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "group_id": self.group_id,
            "group_code": self.group_code,
            "group_name": self.group_name,
            "rule_count": self.rule_count,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث الإعفاءات
# =============================================================================

@dataclass(frozen=True)
class TaxExemptionCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء إعفاء ضريبي جديد"""
    exemption_id: str
    exemption_code: str
    exemption_name: str
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.exemption.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "exemption_id": self.exemption_id,
            "exemption_code": self.exemption_code,
            "exemption_name": self.exemption_name,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث الفترات الضريبية
# =============================================================================

@dataclass(frozen=True)
class TaxPeriodCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء فترة ضريبية جديدة"""
    period_id: str
    period_code: str
    period_name: str
    start_date: date
    end_date: date
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.period.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "period_id": self.period_id,
            "period_code": self.period_code,
            "period_name": self.period_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxPeriodClosedEvent(BaseDomainEvent):
    """يُرفع عند إغلاق فترة ضريبية"""
    period_id: str
    period_code: str
    period_name: str
    closed_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.period.closed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "period_id": self.period_id,
            "period_code": self.period_code,
            "period_name": self.period_name,
            "closed_by": self.closed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class TaxPeriodReopenedEvent(BaseDomainEvent):
    """يُرفع عند إعادة فتح فترة ضريبية"""
    period_id: str
    period_code: str
    period_name: str
    reopened_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.period.reopened"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "period_id": self.period_id,
            "period_code": self.period_code,
            "period_name": self.period_name,
            "reopened_by": self.reopened_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث التقارير الضريبية
# =============================================================================

@dataclass(frozen=True)
class TaxReportGeneratedEvent(BaseDomainEvent):
    """يُرفع عند توليد تقرير ضريبي"""
    report_id: str
    period_name: str
    total_tax: Decimal
    total_sales: Decimal
    total_purchases: Decimal
    net_tax_due: Decimal
    generated_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "tax.report.generated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "report_id": self.report_id,
            "period_name": self.period_name,
            "total_tax": str(self.total_tax),
            "total_sales": str(self.total_sales),
            "total_purchases": str(self.total_purchases),
            "net_tax_due": str(self.net_tax_due),
            "generated_by": self.generated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Tax Rule Events
    'TaxRuleCreatedEvent',
    'TaxRuleUpdatedEvent',
    'TaxRuleActivatedEvent',
    'TaxRuleDeactivatedEvent',

    # Tax Calculation Events
    'TaxCalculatedEvent',
    'TaxExemptionAppliedEvent',

    # Tax Group Events
    'TaxGroupCreatedEvent',

    # Tax Exemption Events
    'TaxExemptionCreatedEvent',

    # Tax Period Events
    'TaxPeriodCreatedEvent',
    'TaxPeriodClosedEvent',
    'TaxPeriodReopenedEvent',

    # Tax Report Events
    'TaxReportGeneratedEvent',
]