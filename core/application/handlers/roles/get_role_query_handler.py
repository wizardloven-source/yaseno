# core/application/handlers/roles/get_role_query_handler.py
"""Get Role Query Handler - معالج استعلام جلب دور"""

from core.domain.auth.value_objects import RoleId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

from core.application.roles.converters import role_to_dto


class GetRoleQueryHandler(BaseQueryHandler):
    """معالج استعلام جلب دور"""
    
    def __init__(self, role_repo):
        self._role_repo = role_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """تنفيذ جلب الدور"""
        role = self._role_repo.get_by_id(RoleId.from_string(query.role_id))
        if not role:
            return None
        
        return role_to_dto(role)