"""
Security Domain Models for YASeen ERP

Implements:
- Permission hierarchy (Module → Screen → Action → Permission)
- Role-Based Access Control (RBAC)
- Audit Trail entities
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID


class ActionType(Enum):
    """Standard actions for any entity"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    POST = "post"
    CANCEL = "cancel"
    APPROVE = "approve"
    REJECT = "reject"
    PRINT = "print"
    EXPORT = "export"
    IMPORT = "import"
    CONFIGURE = "configure"


@dataclass(frozen=True)
class Permission:
    """
    Granular permission following the hierarchy:
    Module.Screen.Action
    
    Examples:
    - sales.invoice.create
    - sales.invoice.edit
    - sales.invoice.post
    - sales.invoice.cancel
    - sales.invoice.delete
    - accounting.journal_entry.post
    - inventory.stock.adjust
    """
    code: str  # e.g., "sales.invoice.create"
    name: str  # Human-readable name
    description: Optional[str] = None
    module: str = field(init=False)
    screen: str = field(init=False)
    action: str = field(init=False)
    
    def __post_init__(self):
        parts = self.code.split('.')
        if len(parts) < 3:
            raise ValueError(f"Permission code must follow Module.Screen.Action format: {self.code}")
        
        object.__setattr__(self, 'module', parts[0])
        object.__setattr__(self, 'screen', '.'.join(parts[1:-1]))
        object.__setattr__(self, 'action', parts[-1])
    
    @classmethod
    def build(cls, module: str, screen: str, action: ActionType | str) -> 'Permission':
        """Build permission code from components"""
        action_str = action.value if isinstance(action, ActionType) else action
        code = f"{module}.{screen}.{action_str}"
        name = f"{module.title()} - {screen.title()} - {action_str.title()}"
        return cls(code=code, name=name)


@dataclass
class Role:
    """
    Role containing multiple permissions
    """
    id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    is_system: bool = False  # System roles cannot be deleted
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    
    @classmethod
    def create(cls, name: str, description: Optional[str] = None, 
               created_by: Optional[str] = None) -> 'Role':
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            created_by=created_by
        )
    
    def add_permission(self, permission: Permission) -> None:
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission_code: str) -> bool:
        for i, perm in enumerate(self.permissions):
            if perm.code == permission_code:
                self.permissions.pop(i)
                return True
        return False
    
    def has_permission(self, permission_code: str) -> bool:
        return any(p.code == permission_code for p in self.permissions)
    
    def has_any_permission(self, permission_codes: List[str]) -> bool:
        return any(self.has_permission(code) for code in permission_codes)
    
    def has_all_permissions(self, permission_codes: List[str]) -> bool:
        return all(self.has_permission(code) for code in permission_codes)


@dataclass
class User:
    """
    User with assigned roles
    """
    id: UUID
    username: str
    email: str
    full_name: str
    is_active: bool = True
    is_locked: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_hash: Optional[str] = None
    roles: List[Role] = field(default_factory=list)
    last_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    
    @classmethod
    def create(cls, username: str, email: str, full_name: str,
               created_by: Optional[str] = None) -> 'User':
        return cls(
            id=uuid4(),
            username=username,
            email=email,
            full_name=full_name,
            created_by=created_by
        )
    
    def assign_role(self, role: Role) -> None:
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role_id: UUID) -> bool:
        for i, role in enumerate(self.roles):
            if role.id == role_id:
                self.roles.pop(i)
                return True
        return False
    
    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a specific permission through any role"""
        return any(role.has_permission(permission_code) for role in self.roles)
    
    def has_any_permission(self, permission_codes: List[str]) -> bool:
        return any(self.has_permission(code) for code in permission_codes)
    
    def has_all_permissions(self, permission_codes: List[str]) -> bool:
        return all(self.has_permission(code) for code in permission_codes)
    
    def record_failed_login(self) -> None:
        self.failed_login_attempts += 1
    
    def reset_failed_logins(self) -> None:
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_until = None
    
    def lock(self, duration_minutes: int) -> None:
        
        self.is_locked = True
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)


class AuditEventType(Enum):
    """Types of audit events"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    POST = "POST"
    CANCEL = "CANCEL"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ROLE_ASSIGNMENT = "ROLE_ASSIGNMENT"
    PERIOD_CLOSE = "PERIOD_CLOSE"
    PERIOD_OPEN = "PERIOD_OPEN"
    EXCHANGE_RATE_UPDATE = "EXCHANGE_RATE_UPDATE"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"
    PRICE_CHANGE = "PRICE_CHANGE"
    INVOICE_MODIFICATION = "INVOICE_MODIFICATION"
    JOURNAL_ENTRY_REVERSAL = "JOURNAL_ENTRY_REVERSAL"


@dataclass
class AuditEvent:
    """
    Comprehensive audit trail entry
    
    Captures:
    - Who performed the action
    - When it happened
    - What action was performed
    - Old and new values
    - Document/Entity affected
    - Reason for change
    - IP address, device, session info
    """
    id: UUID
    event_type: AuditEventType
    entity_type: str  # e.g., "Customer", "Invoice", "JournalEntry"
    entity_id: UUID
    user_id: UUID
    username: str
    timestamp: datetime
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    document_reference: Optional[str] = None  # e.g., Invoice number
    reason: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    session_id: Optional[str] = None
    module: Optional[str] = None
    
    @classmethod
    def create(cls, event_type: AuditEventType, entity_type: str, entity_id: UUID,
               user_id: UUID, username: str, 
               old_values: Optional[Dict[str, Any]] = None,
               new_values: Optional[Dict[str, Any]] = None,
               document_reference: Optional[str] = None,
               reason: Optional[str] = None,
               ip_address: Optional[str] = None,
               device_info: Optional[str] = None,
               session_id: Optional[str] = None,
               module: Optional[str] = None) -> 'AuditEvent':
        return cls(
            id=uuid4(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            timestamp=datetime.now(timezone.utc),
            old_values=old_values,
            new_values=new_values,
            document_reference=document_reference,
            reason=reason,
            ip_address=ip_address,
            device_info=device_info,
            session_id=session_id,
            module=module
        )
    
    @classmethod
    def for_update(cls, entity_type: str, entity_id: UUID, user_id: UUID, username: str,
                   old_values: Dict[str, Any], new_values: Dict[str, Any],
                   reason: Optional[str] = None, **kwargs) -> 'AuditEvent':
        return cls.create(
            event_type=AuditEventType.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            old_values=old_values,
            new_values=new_values,
            reason=reason,
            **kwargs
        )
    
    @classmethod
    def for_create(cls, entity_type: str, entity_id: UUID, user_id: UUID, username: str,
                   new_values: Dict[str, Any], **kwargs) -> 'AuditEvent':
        return cls.create(
            event_type=AuditEventType.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            new_values=new_values,
            **kwargs
        )
    
    @classmethod
    def for_delete(cls, entity_type: str, entity_id: UUID, user_id: UUID, username: str,
                   old_values: Dict[str, Any], reason: Optional[str] = None,
                   **kwargs) -> 'AuditEvent':
        return cls.create(
            event_type=AuditEventType.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            old_values=old_values,
            reason=reason,
            **kwargs
        )
    
    @classmethod
    def for_post(cls, entity_type: str, entity_id: UUID, user_id: UUID, username: str,
                 document_reference: str, **kwargs) -> 'AuditEvent':
        return cls.create(
            event_type=AuditEventType.POST,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            document_reference=document_reference,
            **kwargs
        )
    
    @classmethod
    def for_cancel(cls, entity_type: str, entity_id: UUID, user_id: UUID, username: str,
                   document_reference: str, reason: str, **kwargs) -> 'AuditEvent':
        return cls.create(
            event_type=AuditEventType.CANCEL,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            username=username,
            document_reference=document_reference,
            reason=reason,
            **kwargs
        )


@dataclass
class PasswordPolicy:
    """
    Password policy configuration
    """
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    max_age_days: Optional[int] = 90
    prevent_reuse_count: int = 5
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 30
    
    def validate(self, password: str) -> List[str]:
        """Validate password against policy, return list of violations"""
        violations = []
        
        if len(password) < self.min_length:
            violations.append(f"Password must be at least {self.min_length} characters")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            violations.append("Password must contain uppercase letters")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            violations.append("Password must contain lowercase letters")
        
        if self.require_digits and not any(c.isdigit() for c in password):
            violations.append("Password must contain digits")
        
        if self.require_special_chars and not any(not c.isalnum() for c in password):
            violations.append("Password must contain special characters")
        
        return violations


# Predefined system roles
def get_system_roles() -> List[Role]:
    """Get predefined system roles"""
    
    # Super Admin - Full access
    super_admin = Role.create(
        name="Super Administrator",
        description="Full system access"
    )
    super_admin.is_system = True
    
    # Accountant - Full accounting access
    accountant = Role.create(
        name="Accountant",
        description="Full accounting module access"
    )
    accountant.is_system = True
    
    # Sales Manager
    sales_manager = Role.create(
        name="Sales Manager",
        description="Manage sales operations"
    )
    sales_manager.is_system = True
    
    # Inventory Manager
    inventory_manager = Role.create(
        name="Inventory Manager",
        description="Manage inventory operations"
    )
    inventory_manager.is_system = True
    
    # Viewer - Read-only access
    viewer = Role.create(
        name="Viewer",
        description="Read-only access to all modules"
    )
    viewer.is_system = True
    
    return [super_admin, accountant, sales_manager, inventory_manager, viewer]


# Standard permissions for common modules
STANDARD_PERMISSIONS = {
    # Sales
    "sales.quotation.create": Permission("sales.quotation.create", "Create Quotation"),
    "sales.quotation.read": Permission("sales.quotation.read", "View Quotation"),
    "sales.quotation.update": Permission("sales.quotation.update", "Edit Quotation"),
    "sales.quotation.delete": Permission("sales.quotation.delete", "Delete Quotation"),
    "sales.order.create": Permission("sales.order.create", "Create Sales Order"),
    "sales.order.read": Permission("sales.order.read", "View Sales Order"),
    "sales.order.update": Permission("sales.order.update", "Edit Sales Order"),
    "sales.order.delete": Permission("sales.order.delete", "Delete Sales Order"),
    "sales.invoice.create": Permission("sales.invoice.create", "Create Invoice"),
    "sales.invoice.read": Permission("sales.invoice.read", "View Invoice"),
    "sales.invoice.update": Permission("sales.invoice.update", "Edit Invoice"),
    "sales.invoice.post": Permission("sales.invoice.post", "Post Invoice"),
    "sales.invoice.cancel": Permission("sales.invoice.cancel", "Cancel Invoice"),
    "sales.invoice.delete": Permission("sales.invoice.delete", "Delete Invoice"),
    "sales.payment.create": Permission("sales.payment.create", "Create Payment"),
    "sales.payment.read": Permission("sales.payment.read", "View Payment"),
    "sales.payment.post": Permission("sales.payment.post", "Post Payment"),
    
    # Purchasing
    "purchase.rfq.create": Permission("purchase.rfq.create", "Create RFQ"),
    "purchase.rfq.read": Permission("purchase.rfq.read", "View RFQ"),
    "purchase.order.create": Permission("purchase.order.create", "Create Purchase Order"),
    "purchase.order.read": Permission("purchase.order.read", "View Purchase Order"),
    "purchase.order.update": Permission("purchase.order.update", "Edit Purchase Order"),
    "purchase.order.post": Permission("purchase.order.post", "Post Purchase Order"),
    "purchase.order.cancel": Permission("purchase.order.cancel", "Cancel Purchase Order"),
    "purchase.receive.create": Permission("purchase.receive.create", "Create Receipt"),
    "purchase.receive.read": Permission("purchase.receive.read", "View Receipt"),
    "purchase.receive.post": Permission("purchase.receive.post", "Post Receipt"),
    "purchase.bill.create": Permission("purchase.bill.create", "Create Supplier Bill"),
    "purchase.bill.read": Permission("purchase.bill.read", "View Supplier Bill"),
    "purchase.bill.post": Permission("purchase.bill.post", "Post Supplier Bill"),
    "purchase.bill.cancel": Permission("purchase.bill.cancel", "Cancel Supplier Bill"),
    "purchase.payment.create": Permission("purchase.payment.create", "Create Supplier Payment"),
    "purchase.payment.read": Permission("purchase.payment.read", "View Supplier Payment"),
    "purchase.payment.post": Permission("purchase.payment.post", "Post Supplier Payment"),
    
    # Accounting
    "accounting.journal_entry.create": Permission("accounting.journal_entry.create", "Create Journal Entry"),
    "accounting.journal_entry.read": Permission("accounting.journal_entry.read", "View Journal Entry"),
    "accounting.journal_entry.update": Permission("accounting.journal_entry.update", "Edit Journal Entry"),
    "accounting.journal_entry.post": Permission("accounting.journal_entry.post", "Post Journal Entry"),
    "accounting.journal_entry.cancel": Permission("accounting.journal_entry.cancel", "Cancel Journal Entry"),
    "accounting.journal_entry.delete": Permission("accounting.journal_entry.delete", "Delete Journal Entry"),
    "accounting.account.create": Permission("accounting.account.create", "Create Account"),
    "accounting.account.read": Permission("accounting.account.read", "View Account"),
    "accounting.account.update": Permission("accounting.account.update", "Edit Account"),
    "accounting.period.close": Permission("accounting.period.close", "Close Period"),
    "accounting.period.open": Permission("accounting.period.open", "Open Period"),
    "accounting.report.view": Permission("accounting.report.view", "View Reports"),
    "accounting.reconciliation.perform": Permission("accounting.reconciliation.perform", "Perform Reconciliation"),
    
    # Inventory
    "inventory.item.create": Permission("inventory.item.create", "Create Item"),
    "inventory.item.read": Permission("inventory.item.read", "View Item"),
    "inventory.item.update": Permission("inventory.item.update", "Edit Item"),
    "inventory.item.delete": Permission("inventory.item.delete", "Delete Item"),
    "inventory.stock.view": Permission("inventory.stock.view", "View Stock"),
    "inventory.stock.adjust": Permission("inventory.stock.adjust", "Adjust Stock"),
    "inventory.stock.transfer": Permission("inventory.stock.transfer", "Transfer Stock"),
    "inventory.warehouse.create": Permission("inventory.warehouse.create", "Create Warehouse"),
    "inventory.warehouse.read": Permission("inventory.warehouse.read", "View Warehouse"),
    "inventory.warehouse.update": Permission("inventory.warehouse.update", "Edit Warehouse"),
    "inventory.valuation.view": Permission("inventory.valuation.view", "View Valuation"),
    "inventory.movement.view": Permission("inventory.movement.view", "View Movements"),
    
    # Customers
    "customer.customer.create": Permission("customer.customer.create", "Create Customer"),
    "customer.customer.read": Permission("customer.customer.read", "View Customer"),
    "customer.customer.update": Permission("customer.customer.update", "Edit Customer"),
    "customer.customer.delete": Permission("customer.customer.delete", "Delete Customer"),
    "customer.statement.view": Permission("customer.statement.view", "View Statement"),
    
    # Suppliers
    "supplier.supplier.create": Permission("supplier.supplier.create", "Create Supplier"),
    "supplier.supplier.read": Permission("supplier.supplier.read", "View Supplier"),
    "supplier.supplier.update": Permission("supplier.supplier.update", "Edit Supplier"),
    "supplier.supplier.delete": Permission("supplier.supplier.delete", "Delete Supplier"),
    "supplier.statement.view": Permission("supplier.statement.view", "View Statement"),
    
    # Cash & Banking
    "cash.fund.create": Permission("cash.fund.create", "Create Fund"),
    "cash.fund.read": Permission("cash.fund.read", "View Fund"),
    "cash.cash_in.create": Permission("cash.cash_in.create", "Record Cash In"),
    "cash.cash_in.post": Permission("cash.cash_in.post", "Post Cash In"),
    "cash.cash_out.create": Permission("cash.cash_out.create", "Record Cash Out"),
    "cash.cash_out.post": Permission("cash.cash_out.post", "Post Cash Out"),
    "cash.transfer.create": Permission("cash.transfer.create", "Create Transfer"),
    "cash.transfer.post": Permission("cash.transfer.post", "Post Transfer"),
    "cash.reconciliation.perform": Permission("cash.reconciliation.perform", "Reconcile Cash"),
    
    # Fixed Assets
    "asset.asset.create": Permission("asset.asset.create", "Create Asset"),
    "asset.asset.read": Permission("asset.asset.read", "View Asset"),
    "asset.asset.update": Permission("asset.asset.update", "Edit Asset"),
    "asset.acquisition.perform": Permission("asset.acquisition.perform", "Acquire Asset"),
    "asset.depreciation.run": Permission("asset.depreciation.run", "Run Depreciation"),
    "asset.disposal.perform": Permission("asset.disposal.perform", "Dispose Asset"),
    
    # Administration
    "admin.user.manage": Permission("admin.user.manage", "Manage Users"),
    "admin.role.manage": Permission("admin.role.manage", "Manage Roles"),
    "admin.permission.view": Permission("admin.permission.view", "View Permissions"),
    "admin.audit.view": Permission("admin.audit.view", "View Audit Trail"),
    "admin.settings.update": Permission("admin.settings.update", "Update Settings"),
    "admin.exchange_rate.update": Permission("admin.exchange_rate.update", "Update Exchange Rates"),
}
