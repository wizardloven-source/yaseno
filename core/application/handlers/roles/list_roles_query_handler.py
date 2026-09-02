# core/application/handlers/roles/list_roles_query_handler.py
"""List Roles Query Handler - معالج استعلام قائمة الأدوار"""

from typing import List
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

from core.application.roles.converters import role_to_dto


class ListRolesQueryHandler(BaseQueryHandler):
    """معالج استعلام قائمة الأدوار"""
    
    def __init__(self, role_repo):
        self._role_repo = role_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """تنفيذ جلب قائمة الأدوار"""
        roles = self._role_repo.list_all(
            include_inactive=query.include_inactive,
            limit=query.limit,
            offset=query.offset
        )
        
        return [role_to_dto(role) for role in roles]