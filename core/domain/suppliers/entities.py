"""Supplier Aggregate Root"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Any

from .value_objects import SupplierId, SupplierCode, SupplierStatus, ContactInfo, Address
from .exceptions import InvalidSupplierStatusTransition
from .events import SupplierCreatedEvent, SupplierUpdatedEvent, SupplierDeletedEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Supplier:
    """
    AGGREGATE ROOT - المورد
    
    ملاحظة: الـ version هو للتحكم في التزامن (Optimistic Locking)
    يتم إدارته فقط بواسطة الـ Repository ولا يتم تعديله داخل الـ Entity
    """
    
    id: SupplierId = field(default_factory=SupplierId.generate)
    code: SupplierCode = field(default_factory=lambda: SupplierCode(""))
    name: str = ""
    status: SupplierStatus = SupplierStatus.ACTIVE
    
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    address: Address = field(default_factory=Address)
    
    tax_number: Optional[str] = None
    credit_limit: Decimal = Decimal('0')
    currency: str = "USD"
    
    notes: Optional[str] = None
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    # التحكم في التزامن (تتم إدارته فقط بواسطة Repository)
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_active(self) -> bool:
        return self.status == SupplierStatus.ACTIVE and self.deleted_at is None
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @classmethod
    def create(
        cls,
        code: SupplierCode,
        name: str,
        contact_info: Optional[ContactInfo] = None,
        address: Optional[Address] = None,
        tax_number: Optional[str] = None,
        credit_limit: Decimal = Decimal('0'),
        currency: str = "USD",
        notes: Optional[str] = None,
        created_by: str = ""
    ) -> 'Supplier':
        supplier = cls(
            code=code,
            name=name,
            contact_info=contact_info or ContactInfo(),
            address=address or Address(),
            tax_number=tax_number,
            credit_limit=credit_limit,
            currency=currency,
            notes=notes,
            created_by=created_by,
            updated_by=created_by,
            version=1,  # الإصدار الأولي
        )
        
        supplier._events.append(SupplierCreatedEvent(
            supplier_id=supplier.id,
            supplier_code=supplier.code,
            supplier_name=supplier.name,
            created_by=created_by
        ))
        
        return supplier
    
    def update(
        self,
        name: Optional[str] = None,
        contact_info: Optional[ContactInfo] = None,
        address: Optional[Address] = None,
        tax_number: Optional[str] = None,
        credit_limit: Optional[Decimal] = None,
        currency: Optional[str] = None,
        notes: Optional[str] = None,
        updated_by: str = ""
    ) -> None:
        """
        تحديث بيانات المورد
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.deleted_at is not None:
            raise ValueError("Cannot update a deleted supplier")
        
        changes = {}
        
        if name is not None and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if credit_limit is not None:
            changes['credit_limit'] = {'old': float(self.credit_limit), 'new': float(credit_limit)}
            self.credit_limit = credit_limit
        
        if currency is not None and currency != self.currency:
            changes['currency'] = {'old': self.currency, 'new': currency}
            self.currency = currency
        
        if notes is not None:
            changes['notes'] = {'old': self.notes, 'new': notes}
            self.notes = notes
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            # ❌ self.version += 1 - تم حذفها
            
            self._events.append(SupplierUpdatedEvent(
                supplier_id=self.id,
                supplier_code=self.code,
                supplier_name=self.name,
                changes=changes,
                updated_by=updated_by
            ))
    
    def change_status(self, new_status: SupplierStatus, reason: Optional[str] = None, changed_by: str = "") -> None:
        """
        تغيير حالة المورد
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.deleted_at is not None:
            raise ValueError("Cannot change status of a deleted supplier")
        
        if self.status == new_status:
            return
        
        valid_transitions = {
            SupplierStatus.ACTIVE: [SupplierStatus.INACTIVE, SupplierStatus.SUSPENDED],
            SupplierStatus.INACTIVE: [SupplierStatus.ACTIVE],
            SupplierStatus.SUSPENDED: [SupplierStatus.ACTIVE, SupplierStatus.BLOCKED],
            SupplierStatus.BLOCKED: [SupplierStatus.INACTIVE],
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise InvalidSupplierStatusTransition(self.status.value, new_status.value)
        
        self.status = new_status
        self.updated_at = utc_now()
        self.updated_by = changed_by
        # ❌ self.version += 1 - تم حذفها
    
    def soft_delete(self, deleted_by: str, reason: Optional[str] = None) -> None:
        """
        حذف ناعم للمورد
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.deleted_at is not None:
            return
        
        self.status = SupplierStatus.INACTIVE
        self.deleted_at = utc_now()
        self.deleted_by = deleted_by
        self.updated_at = utc_now()
        self.updated_by = deleted_by
        # ❌ self.version += 1 - تم حذفها
        
        self._events.append(SupplierDeletedEvent(
            supplier_id=self.id,
            supplier_code=self.code,
            supplier_name=self.name,
            deleted_by=deleted_by,
            reason=reason
        ))
    
    def restore(self, restored_by: str) -> None:
        """
        استعادة مورد محذوف
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.deleted_at is None:
            return
        
        self.status = SupplierStatus.ACTIVE
        self.deleted_at = None
        self.deleted_by = None
        self.updated_at = utc_now()
        self.updated_by = restored_by
        # ❌ self.version += 1 - تم حذفها
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events