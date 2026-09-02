# core/application/handlers/customer_branch/get_branch_by_code_handler.py
"""Get Branch By Code Handler - معالج استعلام جلب فرع بالكود"""

import logging

from core.domain.customer_branch.value_objects import BranchCode
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.queries import GetBranchByCodeQuery
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class GetBranchByCodeHandler(BaseQueryHandler[GetBranchByCodeQuery, CustomerBranchDTO]):
    """معالج استعلام جلب فرع بواسطة الكود"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetBranchByCodeQuery, user_context: UserContext = None) -> CustomerBranchDTO:
        logger.debug(f"Fetching branch by code: {query.code}")
        
        with self._uow:
            repo = self._uow.customer_branches
            branch = repo.get_by_code(BranchCode(query.code))
            
            if not branch:
                logger.warning(f"Branch not found: {query.code}")
                return None
            
            return branch_to_dto(branch)