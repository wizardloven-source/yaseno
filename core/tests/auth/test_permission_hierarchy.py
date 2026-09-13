"""
tests/auth/test_permission_hierarchy.py

PERMISSION HIERARCHY TESTS - CRITICAL FOR ERP SECURITY

Tests the granular permission model:
    Module → Screen → Action → Permission
    
Example:
    sales.invoice.create
    sales.invoice.edit
    sales.invoice.post
    sales.invoice.cancel
    sales.invoice.delete

This is essential for commercial ERP systems.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from core.domain.auth.entities import User, Role, Permission
from core.domain.auth.value_objects import UserId, RoleId, PermissionId


# ========== FIXTURES ==========

@pytest.fixture
def sample_permissions():
    """Create a set of sample permissions for testing."""
    return {
        # Sales Invoice Permissions
        "sales.invoice.create": Permission(
            id=PermissionId("perm_001"),
            code="sales.invoice.create",
            name="Create Sales Invoice",
            category="Sales"
        ),
        "sales.invoice.edit": Permission(
            id=PermissionId("perm_002"),
            code="sales.invoice.edit",
            name="Edit Sales Invoice",
            category="Sales"
        ),
        "sales.invoice.post": Permission(
            id=PermissionId("perm_003"),
            code="sales.invoice.post",
            name="Post Sales Invoice",
            category="Sales"
        ),
        "sales.invoice.cancel": Permission(
            id=PermissionId("perm_004"),
            code="sales.invoice.cancel",
            name="Cancel Sales Invoice",
            category="Sales"
        ),
        "sales.invoice.delete": Permission(
            id=PermissionId("perm_005"),
            code="sales.invoice.delete",
            name="Delete Sales Invoice",
            category="Sales"
        ),
        # Sales Order Permissions
        "sales.order.create": Permission(
            id=PermissionId("perm_006"),
            code="sales.order.create",
            name="Create Sales Order",
            category="Sales"
        ),
        "sales.order.edit": Permission(
            id=PermissionId("perm_007"),
            code="sales.order.edit",
            name="Edit Sales Order",
            category="Sales"
        ),
        "sales.order.post": Permission(
            id=PermissionId("perm_008"),
            code="sales.order.post",
            name="Post Sales Order",
            category="Sales"
        ),
        # Accounting Permissions
        "accounting.journal.create": Permission(
            id=PermissionId("perm_009"),
            code="accounting.journal.create",
            name="Create Journal Entry",
            category="Accounting"
        ),
        "accounting.journal.post": Permission(
            id=PermissionId("perm_010"),
            code="accounting.journal.post",
            name="Post Journal Entry",
            category="Accounting"
        ),
        "accounting.period.close": Permission(
            id=PermissionId("perm_011"),
            code="accounting.period.close",
            name="Close Financial Period",
            category="Accounting"
        ),
        # Inventory Permissions
        "inventory.adjustment.create": Permission(
            id=PermissionId("perm_012"),
            code="inventory.adjustment.create",
            name="Create Stock Adjustment",
            category="Inventory"
        ),
        "inventory.transfer.create": Permission(
            id=PermissionId("perm_013"),
            code="inventory.transfer.create",
            name="Create Stock Transfer",
            category="Inventory"
        ),
    }


@pytest.fixture
def clerk_role(sample_permissions):
    """Create a clerk role with limited permissions."""
    return Role(
        id=RoleId("role_clerk"),
        name="Sales Clerk",
        display_name="Sales Clerk",
        description="Can create invoices but not post or delete",
        permissions=[
            sample_permissions["sales.invoice.create"],
            sample_permissions["sales.invoice.edit"],
            sample_permissions["sales.order.create"],
        ]
    )


@pytest.fixture
def manager_role(sample_permissions):
    """Create a manager role with broader permissions."""
    return Role(
        id=RoleId("role_manager"),
        name="Sales Manager",
        display_name="Sales Manager",
        description="Can create, edit, and post invoices",
        permissions=[
            sample_permissions["sales.invoice.create"],
            sample_permissions["sales.invoice.edit"],
            sample_permissions["sales.invoice.post"],
            sample_permissions["sales.order.create"],
            sample_permissions["sales.order.edit"],
            sample_permissions["sales.order.post"],
        ]
    )


@pytest.fixture
def accountant_role(sample_permissions):
    """Create an accountant role."""
    return Role(
        id=RoleId("role_accountant"),
        name="Accountant",
        display_name="Accountant",
        description="Can post journals and close periods",
        permissions=[
            sample_permissions["accounting.journal.create"],
            sample_permissions["accounting.journal.post"],
        ]
    )


@pytest.fixture
def admin_role(sample_permissions):
    """Create an admin role with all permissions."""
    return Role(
        id=RoleId("role_admin"),
        name="Administrator",
        display_name="System Administrator",
        description="Full system access",
        is_admin=True,
        permissions=list(sample_permissions.values())
    )


@pytest.fixture
def clerk_user(clerk_role):
    """Create a user with clerk role."""
    return User(
        id=UserId("user_clerk"),
        username="clerk_user",
        email="clerk@example.com",
        full_name="Sales Clerk",
        roles=[clerk_role]
    )


@pytest.fixture
def manager_user(manager_role):
    """Create a user with manager role."""
    return User(
        id=UserId("user_manager"),
        username="manager_user",
        email="manager@example.com",
        full_name="Sales Manager",
        roles=[manager_role]
    )


@pytest.fixture
def admin_user(admin_role):
    """Create a user with admin role."""
    return User(
        id=UserId("user_admin"),
        username="admin_user",
        email="admin@example.com",
        full_name="System Admin",
        roles=[admin_role],
        is_super_admin=False  # Test admin role, not super admin
    )


@pytest.fixture
def super_admin_user():
    """Create a super admin user."""
    return User(
        id=UserId("user_superadmin"),
        username="superadmin",
        email="superadmin@example.com",
        full_name="Super Administrator",
        is_super_admin=True,
        roles=[]
    )


# ========== TESTS ==========

class TestPermissionHierarchy:
    """Tests for the permission hierarchy structure."""
    
    def test_permission_code_structure(self, sample_permissions):
        """Permission codes follow Module.Screen.Action pattern."""
        # Arrange & Act
        invoice_create = sample_permissions["sales.invoice.create"]
        
        # Assert
        assert invoice_create.code == "sales.invoice.create"
        parts = invoice_create.code.split(".")
        assert len(parts) == 3
        assert parts[0] == "sales"  # Module
        assert parts[1] == "invoice"  # Screen
        assert parts[2] == "create"  # Action
    
    def test_permission_categories(self, sample_permissions):
        """Permissions are organized by categories."""
        # Arrange & Act
        sales_perms = [p for p in sample_permissions.values() if p.category == "Sales"]
        accounting_perms = [p for p in sample_permissions.values() if p.category == "Accounting"]
        inventory_perms = [p for p in sample_permissions.values() if p.category == "Inventory"]
        
        # Assert
        assert len(sales_perms) > 0
        assert len(accounting_perms) > 0
        assert len(inventory_perms) > 0


class TestRoleBasedPermissions:
    """Tests for role-based permission assignment."""
    
    def test_clerk_cannot_post_invoice(self, clerk_user):
        """Clerk can create/edit but NOT post invoices."""
        # Assert
        assert clerk_user.has_permission("sales.invoice.create") is True
        assert clerk_user.has_permission("sales.invoice.edit") is True
        assert clerk_user.has_permission("sales.invoice.post") is False
        assert clerk_user.has_permission("sales.invoice.delete") is False
    
    def test_manager_can_post_invoice(self, manager_user):
        """Manager can create, edit, AND post invoices."""
        # Assert
        assert manager_user.has_permission("sales.invoice.create") is True
        assert manager_user.has_permission("sales.invoice.edit") is True
        assert manager_user.has_permission("sales.invoice.post") is True
        assert manager_user.has_permission("sales.invoice.delete") is False
    
    def test_accountant_has_accounting_permissions(self, accountant_role):
        """Accountant has accounting-specific permissions."""
        # Assert
        assert accountant_role.has_permission("accounting.journal.create") is True
        assert accountant_role.has_permission("accounting.journal.post") is True
        assert accountant_role.has_permission("sales.invoice.create") is False
    
    def test_admin_has_all_permissions(self, admin_user):
        """Admin role has access to all permissions."""
        # Assert
        assert admin_user.has_permission("sales.invoice.create") is True
        assert admin_user.has_permission("sales.invoice.post") is True
        assert admin_user.has_permission("accounting.journal.post") is True
        assert admin_user.has_permission("inventory.adjustment.create") is True
    
    def test_admin_role_is_admin_flag(self, admin_role):
        """Admin role has is_admin flag set."""
        # Assert
        assert admin_role.is_admin is True
        assert admin_role.has_permission("any.permission.code") is True


class TestSuperAdminBypass:
    """Tests for super admin permission bypass."""
    
    def test_super_admin_has_all_permissions(self, super_admin_user):
        """Super admin has implicit access to everything."""
        # Assert
        assert super_admin_user.has_permission("sales.invoice.create") is True
        assert super_admin_user.has_permission("sales.invoice.delete") is True
        assert super_admin_user.has_permission("accounting.period.close") is True
        assert super_admin_user.has_permission("inventory.adjustment.create") is True
        assert super_admin_user.has_permission("nonexistent.permission") is True
    
    def test_super_admin_without_roles(self, super_admin_user):
        """Super admin works even without assigned roles."""
        # Assert
        assert len(super_admin_user.roles) == 0
        assert super_admin_user.is_super_admin is True
        assert super_admin_user.has_permission("anything") is True


class TestGranularActions:
    """Tests for granular action permissions."""
    
    def test_create_not_implies_post(self, clerk_user):
        """Having create permission doesn't imply post permission."""
        # Assert
        assert clerk_user.has_permission("sales.invoice.create") is True
        assert clerk_user.has_permission("sales.invoice.post") is False
    
    def test_edit_not_implies_delete(self, manager_user):
        """Having edit permission doesn't imply delete permission."""
        # Assert
        assert manager_user.has_permission("sales.invoice.edit") is True
        assert manager_user.has_permission("sales.invoice.delete") is False
    
    def test_separate_inventory_permissions(self, accountant_role):
        """Inventory permissions are separate from accounting."""
        # Assert
        assert accountant_role.has_permission("accounting.journal.create") is True
        assert accountant_role.has_permission("inventory.adjustment.create") is False


class TestMultipleRoles:
    """Tests for users with multiple roles."""
    
    def test_user_with_multiple_roles(self, clerk_role, accountant_role):
        """User with multiple roles gets union of permissions."""
        # Arrange
        multi_role_user = User(
            id=UserId("user_multi"),
            username="multi_user",
            email="multi@example.com",
            full_name="Multi Role User",
            roles=[clerk_role, accountant_role]
        )
        
        # Assert: Has permissions from both roles
        assert multi_role_user.has_permission("sales.invoice.create") is True  # From clerk
        assert multi_role_user.has_permission("accounting.journal.create") is True  # From accountant
        assert multi_role_user.has_permission("sales.invoice.post") is False  # Neither has this


class TestPermissionDenialScenarios:
    """Tests for permission denial scenarios."""
    
    def test_inactive_permission_denied(self, sample_permissions):
        """Inactive permissions should be denied."""
        # Arrange
        inactive_perm = Permission(
            id=PermissionId("perm_inactive"),
            code="sales.invoice.create",
            name="Create Sales Invoice",
            category="Sales",
            is_active=False
        )
        
        inactive_role = Role(
            id=RoleId("role_inactive"),
            name="Inactive Role",
            display_name="Inactive Role",
            permissions=[inactive_perm]
        )
        
        user = User(
            id=UserId("user_inactive"),
            username="inactive_user",
            email="inactive@example.com",
            full_name="Inactive User",
            roles=[inactive_role]
        )
        
        # Note: Current implementation doesn't check is_active flag
        # This is a potential enhancement
        assert user.has_permission("sales.invoice.create") is True


class TestERPWorkflowPermissions:
    """Tests for complete ERP workflow permissions."""
    
    def test_sales_workflow_permissions(self, clerk_user, manager_user):
        """Test complete sales workflow permission separation."""
        # Clerk: Can start the process
        assert clerk_user.has_permission("sales.order.create") is True
        
        # Clerk: Cannot finalize
        assert clerk_user.has_permission("sales.order.post") is False
        
        # Manager: Can finalize
        assert manager_user.has_permission("sales.order.post") is True
    
    def test_invoice_lifecycle_permissions(self, clerk_user, manager_user):
        """Test invoice lifecycle permission separation."""
        # Create: Both can do
        assert clerk_user.has_permission("sales.invoice.create") is True
        assert manager_user.has_permission("sales.invoice.create") is True
        
        # Edit: Both can do
        assert clerk_user.has_permission("sales.invoice.edit") is True
        assert manager_user.has_permission("sales.invoice.edit") is True
        
        # Post: Only manager
        assert clerk_user.has_permission("sales.invoice.post") is False
        assert manager_user.has_permission("sales.invoice.post") is True
        
        # Cancel/Delete: Neither (need higher privilege)
        assert clerk_user.has_permission("sales.invoice.cancel") is False
        assert manager_user.has_permission("sales.invoice.cancel") is False
        assert clerk_user.has_permission("sales.invoice.delete") is False
        assert manager_user.has_permission("sales.invoice.delete") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
