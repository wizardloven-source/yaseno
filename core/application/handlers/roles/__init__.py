# core/application/handlers/roles/__init__.py
"""Roles Handlers - معالجات الأدوار والصلاحيات"""

from .create_role_handler import CreateRoleHandler
from .update_role_handler import UpdateRoleHandler
from .delete_role_handler import DeleteRoleHandler
from .assign_permission_handler import AssignPermissionHandler
from .get_role_query_handler import GetRoleQueryHandler
from .list_roles_query_handler import ListRolesQueryHandler

__all__ = [
    "CreateRoleHandler",
    "UpdateRoleHandler",
    "DeleteRoleHandler",
    "AssignPermissionHandler",
    "GetRoleQueryHandler",
    "ListRolesQueryHandler",
]