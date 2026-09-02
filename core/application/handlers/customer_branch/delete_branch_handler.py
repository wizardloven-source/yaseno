# core/application/handlers/customer_branch/delete_branch_handler.py
"""
Delete Branch Handler - معالج حذف فرع عميل
"""

import logging
from typing import Optional, Dict, Any

from core.domain.customer_branch.value_objects import BranchId
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.customer_branch.base_handler import BaseBranchHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.commands import DeleteBranchCommand

logger = logging.getLogger(__name__)


class DeleteBranchHandler(BaseBranchHandler[DeleteBranchCommand, Dict[str, Any]]):
    """
    معالج حذف فرع عميل
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._branch_repo: Optional[ICustomerBranchRepository] = None
    
    def _get_repo(self) -> ICustomerBranchRepository:
        if self._branch_repo is None:
            self._branch_repo = self._uow.customer_branches
        return self._branch_repo
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteBranchCommand, user_context: UserContext) -> Dict[str, Any]:
        """
        تنفيذ حذف فرع عميل
        """
        logger.info(f"Deleting branch: {command.branch_id} (permanent: {command.permanent})")
        
        with self._uow:
            repo = self._get_repo()
            
            # 1. جلب الفرع
            branch = repo.get_by_id(BranchId.from_string(command.branch_id))
            if not branch:
                return {
                    "success": False,
                    "message": f"Branch {command.branch_id} not found",
                    "branch_id": command.branch_id
                }
            
            # 2. حذف الفرع
            result = repo.delete(
                BranchId.from_string(command.branch_id),
                permanent=command.permanent
            )
            
            self._commit()
            
            if result:
                logger.info(f"Branch deleted: {branch.code} - {branch.name}")
                return {
                    "success": True,
                    "message": f"Branch {branch.code} deleted successfully",
                    "branch_id": command.branch_id,
                    "permanent": command.permanent
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to delete branch {command.branch_id}",
                    "branch_id": command.branch_id
                }