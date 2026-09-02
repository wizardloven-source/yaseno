# core/domain/shared/__init__.py
"""
Shared Domain Components - مشترك بين جميع الـ Bounded Contexts
"""

from .value_objects import (
    Money,
    Timestamp,
    Quantity,
    EntityId,
    Debit,
    Credit,
    TransactionDate,
    UserId,
    BaseDomainEvent, # إذا كان BaseDomainEvent موجوداً داخل value_objects.py
    AccountCode,     # تأكد من إضافته إذا وضعته هناك
)

__all__ = [
    "Money",
    "Timestamp",
    "Quantity",
    "EntityId",
    "Debit",
    "Credit",
    "TransactionDate",
    "UserId",
    "BaseDomainEvent",
    "AccountCode",
]