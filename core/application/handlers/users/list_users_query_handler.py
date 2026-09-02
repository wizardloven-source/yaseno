# core/application/handlers/users/list_users_query_handler.py

"""
List Users Query Handler - معالج استعلام قائمة المستخدمين
"""

from typing import List

from core.domain.auth.interfaces import IUserRepository
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.users.commands import ListUsersQuery
from core.application.users.dtos import UserDTO
from core.application.users.converters import user_to_dto


class ListUsersQueryHandler(BaseQueryHandler[ListUsersQuery, List[UserDTO]]):
    """معالج استعلام قائمة المستخدمين"""
    
    def __init__(self, user_repo: IUserRepository):
        self._user_repo = user_repo
    
    def handle(self, query: ListUsersQuery) -> List[UserDTO]:
        users = self._user_repo.list_all(
            include_inactive=query.include_inactive,
            limit=query.limit,
            offset=query.offset
        )
        
        return [user_to_dto(u) for u in users]