# core/application/customer_branch/commands.py
"""
Customer Branch Commands - أوامر إدارة فروع العملاء
"""

from dataclasses import dataclass
from typing import Optional


# =============================================================================
# COMMANDS
# =============================================================================

@dataclass(frozen=True)
class CreateBranchCommand:
    """أمر إنشاء فرع عميل جديد"""
    code: str
    name: str
    customer_id: str
    customer_name: str
    customer_code: str = ""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: str = "store"
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateBranchCommand:
    """أمر تحديث فرع عميل"""
    branch_id: str
    version: int  # للتحكم في التزامن
    name: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: Optional[str] = None
    status: Optional[str] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class DeleteBranchCommand:
    """أمر حذف فرع عميل"""
    branch_id: str
    permanent: bool = False
    deleted_by: str = "system"


@dataclass(frozen=True)
class ActivateBranchCommand:
    """أمر تنشيط فرع عميل"""
    branch_id: str
    activated_by: str = "system"


@dataclass(frozen=True)
class DeactivateBranchCommand:
    """أمر تعطيل فرع عميل"""
    branch_id: str
    reason: Optional[str] = None
    deactivated_by: str = "system"


@dataclass(frozen=True)
class SetDefaultBranchCommand:
    """أمر تعيين فرع كافتراضي"""
    branch_id: str
    customer_id: str
    set_by: str = "system"