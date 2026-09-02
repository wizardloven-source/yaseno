# core/application/handlers/customer_branch/get_branch_handler.py
"""
Get Branch Handler - معالج استعلام جلب فرع
"""

import logging
from typing import Optional

from core.domain.customer_branch.value_objects import BranchId
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.customer_branch.base_handler import BaseBranchQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.queries import GetBranchQuery
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class GetBranchHandler(BaseBranchQueryHandler[GetBranchQuery, Optional[CustomerBranchDTO]]):
    """
    معالج استعلام جلب فرع بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._branch_repo: Optional[ICustomerBranchRepository] = None
    
    def _get_repo(self) -> ICustomerBranchRepository:
        if self._branch_repo is None:
            self._branch_repo = self._uow.customer_branches
        return self._branch_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetBranchQuery, user_context: UserContext = None) -> Optional[CustomerBranchDTO]:
        """
        تنفيذ جلب الفرع
        """
        logger.debug(f"Fetching branch: {query.branch_id}")
        
        with self._uow:
            repo = self._get_repo()
            
            branch = repo.get_by_id(BranchId.from_string(query.branch_id))
            
            if not branch:
                logger.warning(f"Branch not found: {query.branch_id}")
                return None
            
            return branch_to_dto(branch)