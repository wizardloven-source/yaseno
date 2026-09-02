# core/application/handlers/customer_branch/search_branches_handler.py
"""Search Branches Handler - معالج استعلام البحث عن فروع"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.queries import SearchBranchesQuery
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branches_to_dto_list

logger = logging.getLogger(__name__)


class SearchBranchesHandler(BaseQueryHandler[SearchBranchesQuery, List[CustomerBranchDTO]]):
    """معالج استعلام البحث عن فروع"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: SearchBranchesQuery, user_context: UserContext = None) -> List[CustomerBranchDTO]:
        logger.debug(f"Searching branches with text: {query.search_text}")
        
        with self._uow:
            repo = self._uow.customer_branches
            branches = repo.search(
                search_text=query.search_text,
                customer_id=query.customer_id,
                limit=query.limit
            )
            
            logger.info(f"Found {len(branches)} branches matching '{query.search_text}'")
            
            return branches_to_dto_list(branches)