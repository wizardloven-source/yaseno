# core/application/handlers/customer_branch/get_default_branch_handler.py
"""Get Default Branch Handler - معالج استعلام جلب الفرع الافتراضي"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.queries import GetDefaultBranchQuery
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class GetDefaultBranchHandler(BaseQueryHandler[GetDefaultBranchQuery, CustomerBranchDTO]):
    """معالج استعلام جلب الفرع الافتراضي لعميل"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetDefaultBranchQuery, user_context: UserContext = None) -> CustomerBranchDTO:
        logger.debug(f"Fetching default branch for customer: {query.customer_id}")
        
        with self._uow:
            repo = self._uow.customer_branches
            branch = repo.get_default_branch(query.customer_id)
            
            if not branch:
                logger.warning(f"No default branch for customer: {query.customer_id}")
                return None
            
            return branch_to_dto(branch)