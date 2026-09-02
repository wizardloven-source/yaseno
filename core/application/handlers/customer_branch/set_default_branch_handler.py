"""Set Default Branch Handler - معالج تعيين فرع كافتراضي"""

import logging

from core.domain.customer_branch.value_objects import BranchId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.commands import SetDefaultBranchCommand
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class SetDefaultBranchHandler(BaseHandler[SetDefaultBranchCommand, CustomerBranchDTO]):
    """معالج تعيين فرع كافتراضي"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: SetDefaultBranchCommand, user_context: UserContext) -> CustomerBranchDTO:
        logger.info(f"Setting default branch: {command.branch_id} for customer {command.customer_id}")
        
        with self._uow:
            repo = self._uow.customer_branches
            
            # 1. إلغاء تعيين الفرع الافتراضي الحالي
            current_default = repo.get_default_branch(command.customer_id)
            if current_default:
                current_default.unset_default(user_context.user_id)
                repo.save(current_default)
            
            # 2. تعيين الفرع الجديد كافتراضي
            branch = repo.get_by_id(BranchId.from_string(command.branch_id))
            if not branch:
                raise ValueError(f"Branch {command.branch_id} not found")
            
            branch.set_as_default(user_context.user_id)
            repo.save(branch)
            self._commit()
            
            logger.info(f"Default branch set: {branch.code} - {branch.name}")
            
            return branch_to_dto(branch)