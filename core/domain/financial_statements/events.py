# core/domain/financial_statements/events.py
"""
Financial Statements Events - أحداث القوائم المالية

هذا الملف يحتوي على جميع الأحداث المتعلقة بالقوائم المالية،
والتي تُستخدم لتتبع التغييرات والإجراءات على القوائم المالية
وتفعيل العمليات التلقائية المرتبطة بها.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import StatementId, StatementType, AccountCategory


def _aware_utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC مع المنطقة الزمنية"""
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث توليد القوائم المالية
# =============================================================================

@dataclass(frozen=True)
class IncomeStatementGeneratedEvent(BaseDomainEvent):
    """
    يُرفع عند توليد قائمة الدخل
    
    هذا الحدث يُستخدم لتتبع عمليات توليد قائمة الدخل،
    ويمكن استخدامه لتحديث لوحة التحكم أو إرسال إشعارات.
    """
    statement_id: StatementId
    period_start: datetime
    period_end: datetime
    currency: str
    net_income: Decimal
    revenue: Decimal
    gross_profit: Decimal
    operating_profit: Decimal
    generated_by: str
    is_comparative: bool = False
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.income_statement.generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "net_income": str(self.net_income),
            "revenue": str(self.revenue),
            "gross_profit": str(self.gross_profit),
            "operating_profit": str(self.operating_profit),
            "generated_by": self.generated_by,
            "is_comparative": self.is_comparative,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class BalanceSheetGeneratedEvent(BaseDomainEvent):
    """
    يُرفع عند توليد الميزانية العمومية
    
    هذا الحدث يُستخدم لتتبع عمليات توليد الميزانية العمومية،
    ويمكن استخدامه لتحديث المؤشرات المالية في لوحة التحكم.
    """
    statement_id: StatementId
    as_of_date: datetime
    currency: str
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    is_balanced: bool
    generated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.balance_sheet.generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "as_of_date": self.as_of_date.isoformat(),
            "currency": self.currency,
            "total_assets": str(self.total_assets),
            "total_liabilities": str(self.total_liabilities),
            "total_equity": str(self.total_equity),
            "is_balanced": self.is_balanced,
            "generated_by": self.generated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class CashFlowStatementGeneratedEvent(BaseDomainEvent):
    """
    يُرفع عند توليد قائمة التدفقات النقدية
    
    هذا الحدث يُستخدم لتتبع عمليات توليد قائمة التدفقات النقدية،
    ويمكن استخدامه لتحليل السيولة.
    """
    statement_id: StatementId
    period_start: datetime
    period_end: datetime
    currency: str
    operating_cash_flow: Decimal
    investing_cash_flow: Decimal
    financing_cash_flow: Decimal
    net_cash_flow: Decimal
    ending_cash: Decimal
    generated_by: str
    method: str = "indirect"
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.cash_flow.generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "operating_cash_flow": str(self.operating_cash_flow),
            "investing_cash_flow": str(self.investing_cash_flow),
            "financing_cash_flow": str(self.financing_cash_flow),
            "net_cash_flow": str(self.net_cash_flow),
            "ending_cash": str(self.ending_cash),
            "generated_by": self.generated_by,
            "method": self.method,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class EquityStatementGeneratedEvent(BaseDomainEvent):
    """
    يُرفع عند توليد قائمة التغيرات في حقوق الملكية
    """
    statement_id: StatementId
    period_start: datetime
    period_end: datetime
    currency: str
    beginning_equity: Decimal
    net_income: Decimal
    dividends_paid: Decimal
    ending_equity: Decimal
    generated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.equity_statement.generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "beginning_equity": str(self.beginning_equity),
            "net_income": str(self.net_income),
            "dividends_paid": str(self.dividends_paid),
            "ending_equity": str(self.ending_equity),
            "generated_by": self.generated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث تحليل القوائم المالية
# =============================================================================

@dataclass(frozen=True)
class FinancialRatioCalculatedEvent(BaseDomainEvent):
    """
    يُرفع عند حساب النسب المالية
    
    هذا الحدث يُستخدم لتتبع النسب المالية المحسوبة من القوائم،
    ويمكن استخدامه لتنبيه المستخدمين عند تجاوز نسب معينة.
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    currency: str
    ratios: Dict[str, Decimal]  # اسم النسبة -> القيمة
    generated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.ratios.calculated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "currency": self.currency,
            "ratios": {k: str(v) for k, v in self.ratios.items()},
            "generated_by": self.generated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class FinancialRatioAlertEvent(BaseDomainEvent):
    """
    يُرفع عند تجاوز نسبة مالية حداً معيناً
    
    هذا الحدث يُستخدم للتنبيه عند وجود مؤشرات مالية غير طبيعية.
    """
    statement_id: StatementId
    ratio_name: str
    current_value: Decimal
    threshold: Decimal
    threshold_type: str  # "min", "max"
    period: str
    currency: str
    severity: str  # "info", "warning", "critical"
    message: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.ratio_alert.triggered"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "ratio_name": self.ratio_name,
            "current_value": str(self.current_value),
            "threshold": str(self.threshold),
            "threshold_type": self.threshold_type,
            "period": self.period,
            "currency": self.currency,
            "severity": self.severity,
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث المقارنة والتحليل
# =============================================================================

@dataclass(frozen=True)
class ComparativeStatementGeneratedEvent(BaseDomainEvent):
    """
    يُرفع عند توليد قائمة مقارنة بين فترتين
    
    هذا الحدث يُستخدم لتتبع عمليات المقارنة المالية.
    """
    statement_id: StatementId
    statement_type: StatementType
    current_period_start: datetime
    current_period_end: datetime
    previous_period_start: datetime
    previous_period_end: datetime
    currency: str
    changes: Dict[str, Decimal]  # اسم البند -> التغير
    percentage_changes: Dict[str, Decimal]  # اسم البند -> النسبة المئوية للتغير
    generated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.comparative.generated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "previous_period_start": self.previous_period_start.isoformat(),
            "previous_period_end": self.previous_period_end.isoformat(),
            "currency": self.currency,
            "changes": {k: str(v) for k, v in self.changes.items()},
            "percentage_changes": {k: str(v) for k, v in self.percentage_changes.items()},
            "generated_by": self.generated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث التقارير والتصدير
# =============================================================================

@dataclass(frozen=True)
class FinancialReportExportedEvent(BaseDomainEvent):
    """
    يُرفع عند تصدير تقرير مالي
    
    هذا الحدث يُستخدم لتتبع عمليات تصدير التقارير المالية.
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    format: str  # PDF, Excel, CSV, JSON
    file_path: str
    exported_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.report.exported"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "format": self.format,
            "file_path": self.file_path,
            "exported_by": self.exported_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class FinancialReportPrintedEvent(BaseDomainEvent):
    """
    يُرفع عند طباعة تقرير مالي
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    printed_by: str
    printer_name: str
    copies: int = 1
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.report.printed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "printed_by": self.printed_by,
            "printer_name": self.printer_name,
            "copies": self.copies,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث التدقيق والمصادقة
# =============================================================================

@dataclass(frozen=True)
class FinancialStatementVerifiedEvent(BaseDomainEvent):
    """
    يُرفع عند التحقق من صحة القائمة المالية
    
    هذا الحدث يُستخدم لتتبع عمليات التدقيق والتحقق من صحة القوائم.
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    verified_by: str
    verification_notes: Optional[str] = None
    is_valid: bool = True
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.statement.verified"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "verified_by": self.verified_by,
            "verification_notes": self.verification_notes,
            "is_valid": self.is_valid,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class FinancialStatementAuditedEvent(BaseDomainEvent):
    """
    يُرفع عند تدقيق القائمة المالية
    
    هذا الحدث يُستخدم لتتبع عمليات التدقيق الرسمية للقوائم المالية.
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    audited_by: str
    audit_firm: str
    audit_opinion: str  # unqualified, qualified, adverse, disclaimer
    audit_notes: Optional[str] = None
    audit_date: datetime = field(default_factory=_aware_utc_now)
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.statement.audited"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "audited_by": self.audited_by,
            "audit_firm": self.audit_firm,
            "audit_opinion": self.audit_opinion,
            "audit_notes": self.audit_notes,
            "audit_date": self.audit_date.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث التخزين والحذف
# =============================================================================

@dataclass(frozen=True)
class FinancialStatementSavedEvent(BaseDomainEvent):
    """
    يُرفع عند حفظ قائمة مالية في قاعدة البيانات
    """
    statement_id: StatementId
    statement_type: StatementType
    period_start: datetime
    period_end: datetime
    currency: str
    saved_by: str
    is_new: bool = True
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.statement.saved"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "currency": self.currency,
            "saved_by": self.saved_by,
            "is_new": self.is_new,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class FinancialStatementDeletedEvent(BaseDomainEvent):
    """
    يُرفع عند حذف قائمة مالية
    
    هذا الحدث يُستخدم لتتبع عمليات الحذف ولأغراض التدقيق.
    """
    statement_id: StatementId
    statement_type: StatementType
    period: str
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "financial_statements.statement.deleted"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "statement_id": str(self.statement_id),
            "statement_type": self.statement_type.value,
            "period": self.period,
            "deleted_by": self.deleted_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# تصدير جميع الأحداث
# =============================================================================

__all__ = [
    # أحداث توليد القوائم
    "IncomeStatementGeneratedEvent",
    "BalanceSheetGeneratedEvent",
    "CashFlowStatementGeneratedEvent",
    "EquityStatementGeneratedEvent",
    
    # أحداث التحليل
    "FinancialRatioCalculatedEvent",
    "FinancialRatioAlertEvent",
    
    # أحداث المقارنة
    "ComparativeStatementGeneratedEvent",
    
    # أحداث التقارير
    "FinancialReportExportedEvent",
    "FinancialReportPrintedEvent",
    
    # أحداث التدقيق
    "FinancialStatementVerifiedEvent",
    "FinancialStatementAuditedEvent",
    
    # أحداث التخزين
    "FinancialStatementSavedEvent",
    "FinancialStatementDeletedEvent",
]