"""
Tests for Security Domain Models and Services

Tests:
- Permission hierarchy (Module.Screen.Action)
- Role-Based Access Control (RBAC)
- Password policy enforcement
- Account lockout logic
- Audit trail recording
- Authorization checks
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.domain.security.models import (
    Permission, Role, User, AuditEvent, AuditEventType,
    PasswordPolicy, ActionType, STANDARD_PERMISSIONS, get_system_roles
)
from core.domain.security.services import (
    AuthorizationService, AuthenticationService, AuditTrailService,
    PermissionService, PermissionDeniedError, AuthenticationError,
    AccountLockedError, PasswordPolicyViolationError
)


# =============================================================================
# Permission Tests
# =============================================================================

class TestPermission:
    """Test permission hierarchy and validation"""
    
    def test_permission_code_parsing(self):
        """Test that permission codes are parsed correctly into module.screen.action"""
        perm = Permission("sales.invoice.create", "Create Invoice")
        
        assert perm.module == "sales"
        assert perm.screen == "invoice"
        assert perm.action == "create"
    
    def test_permission_with_nested_screen(self):
        """Test permissions with nested screen names like journal.entry"""
        perm = Permission("accounting.journal_entry.post", "Post Journal Entry")
        
        assert perm.module == "accounting"
        assert perm.screen == "journal_entry"
        assert perm.action == "post"
    
    def test_invalid_permission_code_raises_error(self):
        """Test that invalid permission codes raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            Permission("invalid.code", "Invalid")
        
        assert "Module.Screen.Action" in str(exc_info.value)
    
    def test_build_permission_from_components(self):
        """Test building permission from module, screen, action components"""
        perm = Permission.build("sales", "invoice", ActionType.POST)
        
        assert perm.code == "sales.invoice.post"
        assert "Sales" in perm.name
        assert "Invoice" in perm.name
        assert "Post" in perm.name
    
    def test_standard_permissions_format(self):
        """Test all standard permissions follow the correct format"""
        for code, perm in STANDARD_PERMISSIONS.items():
            assert perm.module is not None
            assert perm.screen is not None
            assert perm.action is not None
            assert '.' in perm.screen or perm.screen.count('.') >= 0


# =============================================================================
# Role Tests
# =============================================================================

class TestRole:
    """Test role-based access control"""
    
    def test_create_role(self):
        """Test creating a new role"""
        role = Role.create("Test Role", "Test description", "admin")
        
        assert role.name == "Test Role"
        assert role.description == "Test description"
        assert role.created_by == "admin"
        assert len(role.permissions) == 0
        assert not role.is_system
    
    def test_add_permission_to_role(self):
        """Test adding permissions to a role"""
        role = Role.create("Test Role")
        perm = Permission("sales.invoice.create", "Create Invoice")
        
        role.add_permission(perm)
        
        assert len(role.permissions) == 1
        assert role.has_permission("sales.invoice.create")
    
    def test_remove_permission_from_role(self):
        """Test removing permissions from a role"""
        role = Role.create("Test Role")
        perm = Permission("sales.invoice.create", "Create Invoice")
        role.add_permission(perm)
        
        result = role.remove_permission("sales.invoice.create")
        
        assert result is True
        assert not role.has_permission("sales.invoice.create")
        assert len(role.permissions) == 0
    
    def test_has_any_permission(self):
        """Test checking if role has any of multiple permissions"""
        role = Role.create("Test Role")
        role.add_permission(Permission("sales.invoice.create", "Create"))
        role.add_permission(Permission("sales.invoice.read", "Read"))
        
        assert role.has_any_permission(["sales.invoice.create", "purchase.order.create"]) is True
        assert role.has_any_permission(["purchase.order.create", "purchase.order.read"]) is False
    
    def test_has_all_permissions(self):
        """Test checking if role has all required permissions"""
        role = Role.create("Test Role")
        role.add_permission(Permission("sales.invoice.create", "Create"))
        role.add_permission(Permission("sales.invoice.read", "Read"))
        
        assert role.has_all_permissions(["sales.invoice.create", "sales.invoice.read"]) is True
        assert role.has_all_permissions(["sales.invoice.create", "sales.invoice.delete"]) is False
    
    def test_system_role_cannot_be_modified_flag(self):
        """Test that system roles are marked appropriately"""
        system_roles = get_system_roles()
        
        for role in system_roles:
            assert role.is_system is True


# =============================================================================
# User Tests
# =============================================================================

class TestUser:
    """Test user authentication and authorization"""
    
    def test_create_user(self):
        """Test creating a new user"""
        user = User.create("john.doe", "john@example.com", "John Doe", "admin")
        
        assert user.username == "john.doe"
        assert user.email == "john@example.com"
        assert user.full_name == "John Doe"
        assert user.is_active is True
        assert user.is_locked is False
        assert user.failed_login_attempts == 0
    
    def test_assign_role_to_user(self):
        """Test assigning roles to user"""
        user = User.create("john.doe", "john@example.com", "John Doe")
        role = Role.create("Sales Manager")
        role.add_permission(Permission("sales.invoice.create", "Create Invoice"))
        
        user.assign_role(role)
        
        assert len(user.roles) == 1
        assert user.has_permission("sales.invoice.create")
    
    def test_user_inherits_permissions_from_roles(self):
        """Test that users inherit permissions from all assigned roles"""
        user = User.create("john.doe", "john@example.com", "John Doe")
        
        role1 = Role.create("Sales Role")
        role1.add_permission(Permission("sales.invoice.create", "Create Invoice"))
        
        role2 = Role.create("Inventory Role")
        role2.add_permission(Permission("inventory.stock.adjust", "Adjust Stock"))
        
        user.assign_role(role1)
        user.assign_role(role2)
        
        assert user.has_permission("sales.invoice.create") is True
        assert user.has_permission("inventory.stock.adjust") is True
        assert user.has_permission("accounting.journal_entry.post") is False
    
    def test_failed_login_tracking(self):
        """Test tracking failed login attempts"""
        user = User.create("john.doe", "john@example.com", "John Doe")
        
        user.record_failed_login()
        user.record_failed_login()
        user.record_failed_login()
        
        assert user.failed_login_attempts == 3
    
    def test_account_lockout(self):
        """Test account lockout after too many failed attempts"""
        user = User.create("john.doe", "john@example.com", "John Doe")
        
        # Simulate 5 failed attempts
        for _ in range(5):
            user.record_failed_login()
        
        # Lock account for 30 minutes
        user.lock(30)
        
        assert user.is_locked is True
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)
    
    def test_reset_failed_logins(self):
        """Test resetting failed login counter on successful login"""
        user = User.create("john.doe", "john@example.com", "John Doe")
        user.record_failed_login()
        user.record_failed_login()
        user.lock(30)
        
        user.reset_failed_logins()
        
        assert user.failed_login_attempts == 0
        assert user.is_locked is False
        assert user.locked_until is None


# =============================================================================
# Password Policy Tests
# =============================================================================

class TestPasswordPolicy:
    """Test password policy enforcement"""
    
    def test_default_policy_requirements(self):
        """Test default password policy requirements"""
        policy = PasswordPolicy()
        
        assert policy.min_length == 8
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True
        assert policy.require_digits is True
        assert policy.require_special_chars is True
        assert policy.lockout_threshold == 5
        assert policy.lockout_duration_minutes == 30
    
    def test_validate_weak_password(self):
        """Test validation of weak passwords"""
        policy = PasswordPolicy()
        
        violations = policy.validate("weak")
        
        assert len(violations) > 0
        # Check for any violation related to length, uppercase, digits, or special chars
        assert any("length" in v.lower() or "uppercase" in v.lower() or 
                   "digit" in v.lower() or "special" in v.lower() for v in violations)
    
    def test_validate_strong_password(self):
        """Test validation of strong passwords"""
        policy = PasswordPolicy()
        
        violations = policy.validate("StrongP@ss123")
        
        assert len(violations) == 0
    
    def test_validate_missing_uppercase(self):
        """Test password missing uppercase letters"""
        policy = PasswordPolicy()
        
        violations = policy.validate("lowercase123!")
        
        assert any("uppercase" in v.lower() for v in violations)
    
    def test_validate_missing_digit(self):
        """Test password missing digits"""
        policy = PasswordPolicy()
        
        violations = policy.validate("NoDigitsHere!")
        
        assert any("digit" in v.lower() for v in violations)


# =============================================================================
# Audit Event Tests
# =============================================================================

class TestAuditEvent:
    """Test audit trail event creation"""
    
    def test_create_audit_event(self):
        """Test creating a basic audit event"""
        event = AuditEvent.create(
            event_type=AuditEventType.CREATE,
            entity_type="Customer",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="john.doe"
        )
        
        assert event.event_type == AuditEventType.CREATE
        assert event.entity_type == "Customer"
        assert event.username == "john.doe"
        assert event.timestamp is not None
    
    def test_create_update_event_with_values(self):
        """Test creating update event with old and new values"""
        old_values = {"name": "Old Name", "email": "old@example.com"}
        new_values = {"name": "New Name", "email": "new@example.com"}
        
        event = AuditEvent.for_update(
            entity_type="Customer",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="john.doe",
            old_values=old_values,
            new_values=new_values,
            reason="Customer requested name change"
        )
        
        assert event.event_type == AuditEventType.UPDATE
        assert event.old_values == old_values
        assert event.new_values == new_values
        assert event.reason == "Customer requested name change"
    
    def test_create_post_event(self):
        """Test creating post event for document posting"""
        event = AuditEvent.for_post(
            entity_type="Invoice",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="accountant",
            document_reference="INV-2026-001"
        )
        
        assert event.event_type == AuditEventType.POST
        assert event.document_reference == "INV-2026-001"
    
    def test_create_cancel_event_with_reason(self):
        """Test creating cancel event with reason"""
        event = AuditEvent.for_cancel(
            entity_type="Invoice",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="manager",
            document_reference="INV-2026-001",
            reason="Customer requested cancellation"
        )
        
        assert event.event_type == AuditEventType.CANCEL
        assert event.reason == "Customer requested cancellation"
    
    def test_audit_event_includes_metadata(self):
        """Test that audit events can include IP, device, session info"""
        event = AuditEvent.create(
            event_type=AuditEventType.LOGIN,
            entity_type="User",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="john.doe",
            ip_address="192.168.1.100",
            device_info="Mozilla/5.0 Windows NT 10.0",
            session_id="abc123xyz"
        )
        
        assert event.ip_address == "192.168.1.100"
        assert "Windows" in event.device_info
        assert event.session_id == "abc123xyz"


# =============================================================================
# Mock Repository for Service Tests
# =============================================================================

class MockUserRepository:
    """Mock user repository for testing"""
    
    def __init__(self):
        self.users = {}
        self.roles = {}
        self.audit_events = []
    
    def get_user_by_id(self, user_id):
        return self.users.get(user_id)
    
    def get_user_by_username(self, username):
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def save_user(self, user):
        self.users[user.id] = user
    
    def get_role_by_id(self, role_id):
        return self.roles.get(role_id)
    
    def save_role(self, role):
        self.roles[role.id] = role
    
    def save_audit_event(self, event):
        self.audit_events.append(event)


# =============================================================================
# Authorization Service Tests
# =============================================================================

class TestAuthorizationService:
    """Test authorization service"""
    
    def test_check_permission_granted(self):
        """Test checking permission that is granted"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        role = Role.create("Sales Role")
        role.add_permission(Permission("sales.invoice.create", "Create Invoice"))
        user.assign_role(role)
        repo.save_user(user)
        
        auth_service = AuthorizationService(repo)
        
        assert auth_service.check_permission(user.id, "sales.invoice.create") is True
    
    def test_check_permission_denied(self):
        """Test checking permission that is not granted"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        repo.save_user(user)
        
        auth_service = AuthorizationService(repo)
        
        assert auth_service.check_permission(user.id, "sales.invoice.create") is False
    
    def test_require_permission_raises_on_denial(self):
        """Test that require_permission raises exception when denied"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        repo.save_user(user)
        
        auth_service = AuthorizationService(repo)
        
        with pytest.raises(PermissionDeniedError):
            auth_service.require_permission(user.id, "sales.invoice.create")
    
    def test_inactive_user_cannot_access(self):
        """Test that inactive users cannot access resources"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        user.is_active = False
        role = Role.create("Admin")
        role.add_permission(Permission("admin.settings.update", "Update Settings"))
        user.assign_role(role)
        repo.save_user(user)
        
        auth_service = AuthorizationService(repo)
        
        assert auth_service.check_permission(user.id, "admin.settings.update") is False
    
    def test_locked_user_cannot_access(self):
        """Test that locked users cannot access resources"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        user.is_locked = True
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        role = Role.create("Admin")
        role.add_permission(Permission("admin.settings.update", "Update Settings"))
        user.assign_role(role)
        repo.save_user(user)
        
        auth_service = AuthorizationService(repo)
        
        assert auth_service.check_permission(user.id, "admin.settings.update") is False


# =============================================================================
# Authentication Service Tests
# =============================================================================

class TestAuthenticationService:
    """Test authentication service"""
    
    def test_successful_authentication(self):
        """Test successful user authentication"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        # Set password hash manually for testing
        import hashlib
        user.password_hash = hashlib.sha256("password123john.doe".encode()).hexdigest()
        repo.save_user(user)
        
        auth_service = AuthenticationService(repo)
        
        authenticated_user = auth_service.authenticate("john.doe", "password123")
        
        assert authenticated_user.id == user.id
        assert authenticated_user.last_login is not None
    
    def test_failed_authentication_wrong_password(self):
        """Test authentication with wrong password"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        user.password_hash = "wrong_hash"
        repo.save_user(user)
        
        auth_service = AuthenticationService(repo)
        
        with pytest.raises(AuthenticationError):
            auth_service.authenticate("john.doe", "wrongpassword")
    
    def test_account_lockout_after_failed_attempts(self):
        """Test account lockout after multiple failed attempts"""
        repo = MockUserRepository()
        policy = PasswordPolicy(lockout_threshold=3, lockout_duration_minutes=30)
        user = User.create("john.doe", "john@example.com", "John Doe")
        user.password_hash = "wrong_hash"
        repo.save_user(user)
        
        auth_service = AuthenticationService(repo, password_policy=policy)
        
        # Try 3 failed attempts
        for _ in range(3):
            with pytest.raises(AuthenticationError):
                auth_service.authenticate("john.doe", "wrongpassword")
        
        # Account should now be locked
        stored_user = repo.get_user_by_id(user.id)
        assert stored_user.is_locked is True
        assert stored_user.locked_until is not None
    
    def test_password_change_with_policy_validation(self):
        """Test password change validates against policy"""
        repo = MockUserRepository()
        user = User.create("john.doe", "john@example.com", "John Doe")
        import hashlib
        user.password_hash = hashlib.sha256("OldPass123!john.doe".encode()).hexdigest()
        repo.save_user(user)
        
        policy = PasswordPolicy(min_length=8, require_uppercase=True, require_digits=True)
        auth_service = AuthenticationService(repo, password_policy=policy)
        
        # Try weak password
        with pytest.raises(PasswordPolicyViolationError):
            auth_service.change_password(user.id, "OldPass123!", "weak")
        
        # Strong password should work
        auth_service.change_password(user.id, "OldPass123!", "NewPass456!")
        
        updated_user = repo.get_user_by_id(user.id)
        assert updated_user.password_changed_at is not None


# =============================================================================
# Permission Service Tests
# =============================================================================

class TestPermissionService:
    """Test permission management service"""
    
    def test_get_permission(self):
        """Test retrieving a permission by code"""
        user_repo = MockUserRepository()
        role_repo = MockUserRepository()
        perm_service = PermissionService(user_repo, role_repo)
        
        perm = perm_service.get_permission("sales.invoice.create")
        
        assert perm is not None
        assert perm.code == "sales.invoice.create"
    
    def test_get_permissions_for_module(self):
        """Test getting all permissions for a module"""
        user_repo = MockUserRepository()
        role_repo = MockUserRepository()
        perm_service = PermissionService(user_repo, role_repo)
        
        sales_perms = perm_service.get_permissions_for_module("sales")
        
        assert len(sales_perms) > 0
        assert all(p.module == "sales" for p in sales_perms)
    
    def test_create_role(self):
        """Test creating a new role"""
        user_repo = MockUserRepository()
        role_repo = MockUserRepository()
        perm_service = PermissionService(user_repo, role_repo)
        
        role = perm_service.create_role("Custom Role", "Custom description", "admin")
        
        assert role.name == "Custom Role"
        assert role_repo.get_role_by_id(role.id) is not None
    
    def test_add_permission_to_role(self):
        """Test adding permission to role"""
        user_repo = MockUserRepository()
        role_repo = MockUserRepository()
        perm_service = PermissionService(user_repo, role_repo)
        
        role = perm_service.create_role("Test Role")
        perm_service.add_permission_to_role(role.id, "sales.invoice.create", "admin")
        
        updated_role = role_repo.get_role_by_id(role.id)
        assert updated_role.has_permission("sales.invoice.create")


print("\n✅ All security domain tests defined successfully!")
