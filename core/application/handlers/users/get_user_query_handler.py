# core/application/handlers/users/get_user_query_handler.py

"""
Get User Query Handler - معالج استعلام جلب مستخدم
"""

from core.domain.auth.value_objects import UserId
from core.domain.auth.interfaces import IUserRepository
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.users.commands import GetUserQuery
from core.application.users.dtos import UserDTO
from core.application.users.converters import user_to_dto


class GetUserQueryHandler(BaseQueryHandler[GetUserQuery, UserDTO]):
    """معالج استعلام جلب مستخدم"""
    
    def __init__(self, user_repo: IUserRepository):
        self._user_repo = user_repo
    
    def handle(self, query: GetUserQuery) -> UserDTO:
        user = self._user_repo.get_by_id(UserId.from_string(query.user_id))
        if not user:
            return None
        
        return user_to_dto(user)