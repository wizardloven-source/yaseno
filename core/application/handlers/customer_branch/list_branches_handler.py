# core/application/handlers/customer_branch/list_branches_handler.py
"""
List Branches Handler - معالج استعلام قائمة الفروع
"""

import logging
from typing import List

from core.domain.customer_branch.value_objects import BranchStatus
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.customer_branch.base_handler import BaseBranchQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.queries import ListBranchesQuery
from core.application.customer_branch.dtos import CustomerBranchDTO, BranchListDTO
from core.application.customer_branch.converters import branches_to_dto_list

logger = logging.getLogger(__name__)


class ListBranchesHandler(BaseBranchQueryHandler[ListBranchesQuery, BranchListDTO]):
    """
    معالج استعلام قائمة فروع العملاء
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._branch_repo: Optional[ICustomerBranchRepository] = None
    
    def _get_repo(self) -> ICustomerBranchRepository:
        if self._branch_repo is None:
            self._branch_repo = self._uow.customer_branches
        return self._branch_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListBranchesQuery, user_context: UserContext = None) -> BranchListDTO:
        """
        تنفيذ جلب قائمة الفروع
        """
        logger.debug(f"Listing branches: customer={query.customer_id}, status={query.status}")
        
        with self._uow:
            repo = self._get_repo()
            
            # 1. تحويل الحالة إلى Enum
            status = None
            if query.status:
                status = BranchStatus(query.status)
            
            # 2. إذا تم تحديد عميل، جلب فروع العميل
            if query.customer_id:
                branches = repo.get_by_customer(
                    customer_id=query.customer_id,
                    include_inactive=query.include_deleted or query.status != "active",
                    limit=query.limit,
                    offset=query.offset
                )
                total_count = repo.count_by_customer(query.customer_id)
            else:
                # 3. جلب جميع الفروع
                branches = repo.list_all(
                    status=status,
                    include_deleted=query.include_deleted,
                    limit=query.limit,
                    offset=query.offset
                )
                total_count = len(branches)  # مبسط، في الإنتاج يجب استخدام count()
            
            # 4. حساب معلومات الصفحة
            page = (query.offset // query.limit) + 1 if query.limit > 0 else 1
            page_size = query.limit
            
            logger.info(f"Found {len(branches)} branches (total: {total_count})")
            
            return BranchListDTO(
                branches=branches_to_dto_list(branches),
                total_count=total_count,
                page=page,
                page_size=page_size
            )