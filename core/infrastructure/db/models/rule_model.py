# core/infrastructure/db/models/rule_model.py
"""
Accounting Rules ORM Models - نماذج القواعد المحاسبية في قاعدة البيانات
✅ يدعم: PostingRule, RuleGroup, RuleExecutionLog
✅ يدعم: Optimistic Locking عبر الـ version
✅ يدعم: JSONB لتخزين الشروط والإجراءات
✅ يدعم: الفهارس المحسنة للبحث السريع
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Integer, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Numeric,
    UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ✅ استيراد Base من account_model
from .account_model import Base


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# =============================================================================
# PostingRuleModel - نموذج القاعدة المحاسبية
# =============================================================================

class PostingRuleModel(Base):
    """
    ORM Model للقاعدة المحاسبية
    
    تخزن القاعدة مع شروطها وإجراءاتها كـ JSONB للمرونة.
    """
    __tablename__ = "posting_rules"

    # ========== الحقول الأساسية ==========
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للقاعدة"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود القاعدة (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم القاعدة"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="وصف القاعدة"
    )

    # ========== نوع القاعدة وأولويتها ==========
    rule_type: Mapped[str] = mapped_column(
        Enum(
            'invoice_cash_sale', 'invoice_credit_sale',
            'invoice_cash_purchase', 'invoice_credit_purchase',
            'invoice_return', 'invoice_refund', 'invoice_discount',
            'payment_receive', 'payment_pay', 'payment_transfer',
            'payment_receive_invoice', 'payment_pay_invoice',
            'fund_deposit', 'fund_withdraw', 'fund_transfer',
            'stock_in', 'stock_out', 'stock_adjust', 'stock_transfer',
            'asset_purchase', 'asset_depreciation', 'asset_sale', 'asset_write_off',
            'salary', 'expense', 'revenue', 'adjustment',
            'reversal', 'closing', 'opening', 'custom',
            name='rule_type_enum'
        ),
        nullable=False,
        index=True,
        doc="نوع القاعدة"
    )

    priority: Mapped[str] = mapped_column(
        Enum(
            'critical', 'high', 'normal', 'low', 'lowest',
            name='rule_priority_enum'
        ),
        default='normal',
        nullable=False,
        doc="أولوية القاعدة"
    )

    # ✅ تغيير الاسم من `order` إلى `display_order` (لتجنب الكلمة المحجوزة)
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="ترتيب التنفيذ"
    )

    # ========== الشروط والإجراءات (JSONB) ==========
    conditions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        doc="شروط القاعدة (مصفوفة JSON)"
    )

    condition_logic: Mapped[str] = mapped_column(
        String(10),
        default="AND",
        nullable=False,
        doc="منطق الشروط (AND/OR)"
    )

    actions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        doc="إجراءات القاعدة (مصفوفة JSON)"
    )

    # ========== قالب القيد المحاسبي ==========
    journal_template: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="قالب القيد المحاسبي (JSON)"
    )

    # ========== الحالة ==========
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="هل القاعدة نشطة؟"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هي القاعدة الافتراضية؟"
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل القاعدة إجبارية؟"
    )

    # ========== إعدادات منع التكرار ==========
    prevent_duplicate: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="منع تنفيذ القاعدة أكثر من مرة"
    )

    duplicate_check_fields: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="حقول التحقق من التكرار"
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

    # ========== Optimistic Locking ==========
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار - يستخدم للتحقق من التزامن"
    )

    # ========== العلاقات ==========
    group_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rule_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="معرف مجموعة القواعد"
    )

    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_posting_rules_type_active", "rule_type", "is_active"),
        Index("idx_posting_rules_priority", "priority"),
        Index("idx_posting_rules_default", "is_default"),
        Index("idx_posting_rules_code_active", "code", "is_active"),

        CheckConstraint(
            "priority IN ('critical', 'high', 'normal', 'low', 'lowest')",
            name="chk_rule_priority"
        ),
        CheckConstraint(
            "condition_logic IN ('AND', 'OR')",
            name="chk_condition_logic"
        ),
        CheckConstraint(
            "display_order >= 0",
            name="chk_rule_order_non_negative"
        ),
    )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"PostingRuleModel(id={self.id}, code={self.code}, type={self.rule_type}, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        """تحويل النموذج إلى قاموس"""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type,
            'priority': self.priority,
            'display_order': self.display_order,
            'conditions': self.conditions,
            'condition_logic': self.condition_logic,
            'actions': self.actions,
            'journal_template': self.journal_template,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_mandatory': self.is_mandatory,
            'prevent_duplicate': self.prevent_duplicate,
            'duplicate_check_fields': self.duplicate_check_fields,
            'group_id': str(self.group_id) if self.group_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# RuleGroupModel - نموذج مجموعة القواعد
# =============================================================================

class RuleGroupModel(Base):
    """
    ORM Model لمجموعة القواعد
    
    تستخدم لتنظيم القواعد حسب نوع المعاملة أو القسم.
    """
    __tablename__ = "rule_groups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للمجموعة"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود المجموعة (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم المجموعة"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="وصف المجموعة"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="هل المجموعة نشطة؟"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هي المجموعة الافتراضية؟"
    )

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

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار"
    )

    rules: Mapped[List["PostingRuleModel"]] = relationship(
        "PostingRuleModel",
        backref="group",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rule_groups_code_active", "code", "is_active"),
        Index("idx_rule_groups_default", "is_default"),
    )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"RuleGroupModel(id={self.id}, code={self.code}, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'rule_count': len(self.rules) if self.rules else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# RuleExecutionLogModel - نموذج سجل تنفيذ القواعد
# =============================================================================

class RuleExecutionLogModel(Base):
    """
    ORM Model لسجل تنفيذ القواعد
    
    يستخدم لتتبع تنفيذ القواعد وتشخيص الأخطاء.
    """
    __tablename__ = "rule_execution_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        doc="المعرف الفريد للسجل"
    )

    rule_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="معرف القاعدة"
    )

    rule_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="كود القاعدة"
    )

    rule_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم القاعدة"
    )

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="نوع الكيان (invoice, payment, fund, etc.)"
    )

    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="معرف الكيان"
    )

    context_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="لقطة من سياق التنفيذ"
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="هل نجح التنفيذ؟"
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        doc="رسالة التنفيذ"
    )

    journal_entry_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="معرف القيد المحاسبي المنشأ"
    )

    actions_executed: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="الإجراءات المنفذة"
    )

    errors: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="قائمة الأخطاء"
    )

    execution_time_ms: Mapped[float] = mapped_column(
        Numeric(10, 2),
        default=0.0,
        nullable=False,
        doc="وقت التنفيذ بالمللي ثانية"
    )

    executed_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من نفذ القاعدة"
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
        doc="وقت التنفيذ"
    )

    __table_args__ = (
        Index("idx_rule_logs_rule_entity", "rule_id", "entity_type", "entity_id"),
        Index("idx_rule_logs_success", "success", "executed_at"),
        Index("idx_rule_logs_executed_by", "executed_by"),
        Index("idx_rule_logs_journal", "journal_entry_id"),
        Index("idx_rule_logs_executed_at", "executed_at"),
    )

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"RuleExecutionLogModel(id={self.id}, rule={self.rule_code}, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_code': self.rule_code,
            'rule_name': self.rule_name,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'context_snapshot': self.context_snapshot,
            'success': self.success,
            'message': self.message,
            'journal_entry_id': self.journal_entry_id,
            'actions_executed': self.actions_executed,
            'errors': self.errors,
            'execution_time_ms': float(self.execution_time_ms),
            'executed_by': self.executed_by,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostingRuleModel',
    'RuleGroupModel',
    'RuleExecutionLogModel',
]