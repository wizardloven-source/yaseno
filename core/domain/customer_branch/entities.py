# core/domain/customer_branch/entities.py
"""
Customer Branch Entity - كيان فرع العميل
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Any

from .value_objects import (
    BranchId, BranchCode, BranchStatus, BranchAddress, 
    BranchContact, BranchGeoLocation
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CustomerBranch:
    """
    AGGREGATE ROOT - فرع العميل
    
    هذه الوحدة مستقلة تماماً ولا تعتمد على أي وحدة أخرى.
    يمكن استخدامها بمفردها أو دمجها مع أي نظام.
    """
    
    # ========== المعلومات الأساسية ==========
    id: BranchId = field(default_factory=BranchId.generate)
    code: BranchCode = field(default_factory=lambda: BranchCode(""))
    name: str = ""
    status: BranchStatus = BranchStatus.ACTIVE
    
    # ========== معلومات العميل ==========
    customer_id: str = ""  # نص عادي للاستقلالية
    customer_name: str = ""
    customer_code: str = ""
    
    # ========== العنوان والاتصال ==========
    address: BranchAddress = field(default_factory=BranchAddress)
    contact: BranchContact = field(default_factory=BranchContact)
    geo_location: BranchGeoLocation = field(default_factory=BranchGeoLocation)
    
    # ========== معلومات إضافية ==========
    tax_number: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: str = "store"  # store, warehouse, office, delivery
    
    # ========== بيانات الحذف ==========
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    # ========== بيانات التدقيق ==========
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    version: int = 1
    
    # ========== أحداث المجال ==========
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========== الخصائص ==========
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        if self.address.city:
            return f"{self.code} - {self.name} ({self.address.city})"
        return f"{self.code} - {self.name}"
    
    @property
    def is_active(self) -> bool:
        return self.status == BranchStatus.ACTIVE and not self.is_deleted
    
    @property
    def full_address(self) -> str:
        return self.address.full_address
    
    # ========== دالة المصنع ==========
    
    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        customer_id: str,
        customer_name: str,
        customer_code: str = "",
        address: Optional[BranchAddress] = None,
        contact: Optional[BranchContact] = None,
        geo_location: Optional[BranchGeoLocation] = None,
        tax_number: Optional[str] = None,
        is_default: bool = False,
        notes: Optional[str] = None,
        working_hours: Optional[str] = None,
        branch_type: str = "store",
        created_by: str = ""
    ) -> 'CustomerBranch':
        """إنشاء فرع عميل جديد"""
        
        branch = cls(
            code=BranchCode(code),
            name=name,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_code=customer_code,
            address=address or BranchAddress(),
            contact=contact or BranchContact(),
            geo_location=geo_location or BranchGeoLocation(),
            tax_number=tax_number,
            is_default=is_default,
            notes=notes,
            working_hours=working_hours,
            branch_type=branch_type,
            created_by=created_by,
            updated_by=created_by,
            version=1
        )
        
        # ✅ إضافة حدث الإنشاء
        from .events import BranchCreatedEvent
        branch._events.append(BranchCreatedEvent(
            branch_id=branch.id,
            branch_code=branch.code,
            branch_name=branch.name,
            customer_id=branch.customer_id,
            customer_name=branch.customer_name,
            created_by=created_by
        ))
        
        return branch
    
    # ========== العمليات الأساسية ==========
    
    def update(
        self,
        name: Optional[str] = None,
        address: Optional[BranchAddress] = None,
        contact: Optional[BranchContact] = None,
        geo_location: Optional[BranchGeoLocation] = None,
        tax_number: Optional[str] = None,
        is_default: Optional[bool] = None,
        notes: Optional[str] = None,
        working_hours: Optional[str] = None,
        branch_type: Optional[str] = None,
        status: Optional[BranchStatus] = None,
        updated_by: str = ""
    ) -> None:
        """تحديث بيانات الفرع"""
        
        changes = {}
        
        if name is not None and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if address is not None and address != self.address:
            changes['address'] = {'old': self.address, 'new': address}
            self.address = address
        
        if contact is not None and contact != self.contact:
            changes['contact'] = {'old': self.contact, 'new': contact}
            self.contact = contact
        
        if geo_location is not None and geo_location != self.geo_location:
            changes['geo_location'] = {'old': self.geo_location, 'new': geo_location}
            self.geo_location = geo_location
        
        if tax_number is not None and tax_number != self.tax_number:
            changes['tax_number'] = {'old': self.tax_number, 'new': tax_number}
            self.tax_number = tax_number
        
        if is_default is not None and is_default != self.is_default:
            changes['is_default'] = {'old': self.is_default, 'new': is_default}
            self.is_default = is_default
        
        if notes is not None and notes != self.notes:
            changes['notes'] = {'old': self.notes, 'new': notes}
            self.notes = notes
        
        if working_hours is not None and working_hours != self.working_hours:
            changes['working_hours'] = {'old': self.working_hours, 'new': working_hours}
            self.working_hours = working_hours
        
        if branch_type is not None and branch_type != self.branch_type:
            changes['branch_type'] = {'old': self.branch_type, 'new': branch_type}
            self.branch_type = branch_type
        
        if status is not None and status != self.status:
            changes['status'] = {'old': self.status.value, 'new': status.value}
            self.status = status
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1
            
            from .events import BranchUpdatedEvent
            self._events.append(BranchUpdatedEvent(
                branch_id=self.id,
                changes=changes,
                updated_by=updated_by
            ))
    
    def activate(self, activated_by: str) -> None:
        """تنشيط الفرع"""
        if self.status == BranchStatus.ACTIVE:
            return
        
        self.status = BranchStatus.ACTIVE
        self.updated_at = utc_now()
        self.updated_by = activated_by
        self.version += 1
        
        from .events import BranchActivatedEvent
        self._events.append(BranchActivatedEvent(
            branch_id=self.id,
            branch_code=self.code,
            branch_name=self.name,
            activated_by=activated_by
        ))
    
    def deactivate(self, deactivated_by: str, reason: Optional[str] = None) -> None:
        """تعطيل الفرع"""
        if self.status == BranchStatus.INACTIVE:
            return
        
        self.status = BranchStatus.INACTIVE
        self.updated_at = utc_now()
        self.updated_by = deactivated_by
        self.version += 1
        
        from .events import BranchDeactivatedEvent
        self._events.append(BranchDeactivatedEvent(
            branch_id=self.id,
            branch_code=self.code,
            branch_name=self.name,
            deactivated_by=deactivated_by,
            reason=reason
        ))
    
    def soft_delete(self, deleted_by: str) -> None:
        """حذف ناعم للفرع"""
        if self.is_deleted:
            return
        
        self.is_deleted = True
        self.status = BranchStatus.DELETED
        self.deleted_at = utc_now()
        self.deleted_by = deleted_by
        self.updated_at = utc_now()
        self.updated_by = deleted_by
        self.version += 1
        
        from .events import BranchDeletedEvent
        self._events.append(BranchDeletedEvent(
            branch_id=self.id,
            branch_code=self.code,
            branch_name=self.name,
            deleted_by=deleted_by
        ))
    
    def set_as_default(self, updated_by: str) -> None:
        """تعيين الفرع كافتراضي"""
        if self.is_default:
            return
        
        self.is_default = True
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1
    
    def unset_default(self, updated_by: str) -> None:
        """إلغاء تعيين الفرع كافتراضي"""
        if not self.is_default:
            return
        
        self.is_default = False
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1
    
    # ========== أحداث المجال ==========
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def __repr__(self) -> str:
        return f"CustomerBranch(id={self.id}, code={self.code}, name={self.name}, customer={self.customer_name})"