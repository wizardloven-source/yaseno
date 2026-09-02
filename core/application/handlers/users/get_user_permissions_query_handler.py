# core/application/handlers/users/get_user_permissions_query_handler.py (الإصدار المُصحَّح)

"""
Get User Permissions Query Handler - معالج استعلام صلاحيات المستخدم
"""

from typing import List

from core.domain.auth.value_objects import UserId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.users.commands import GetUserPermissionsQuery


class GetUserPermissionsQueryHandler(BaseQueryHandler[GetUserPermissionsQuery, List[str]]):
    """معالج استعلام صلاحيات المستخدم"""
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    def handle(self, query: GetUserPermissionsQuery) -> List[str]:
        with self._uow:
            user_repo = self._uow.users
            user = user_repo.get_by_id(UserId.from_string(query.user_id))
            if not user:
                return []
            
            permissions = set()
            for role in user.roles:
                for perm in role.permissions:
                    permissions.add(perm.code)
            
            return list(permissions)