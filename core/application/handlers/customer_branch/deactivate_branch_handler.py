"""Deactivate Branch Handler - معالج تعطيل فرع عميل"""

import logging

from core.domain.customer_branch.value_objects import BranchId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.commands import DeactivateBranchCommand
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class DeactivateBranchHandler(BaseHandler[DeactivateBranchCommand, CustomerBranchDTO]):
    """معالج تعطيل فرع عميل"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: DeactivateBranchCommand, user_context: UserContext) -> CustomerBranchDTO:
        logger.info(f"Deactivating branch: {command.branch_id}")
        
        with self._uow:
            repo = self._uow.customer_branches
            
            branch = repo.get_by_id(BranchId.from_string(command.branch_id))
            if not branch:
                raise ValueError(f"Branch {command.branch_id} not found")
            
            branch.deactivate(user_context.user_id, command.reason)
            repo.save(branch)
            self._commit()
            
            logger.info(f"Branch deactivated: {branch.code} - {branch.name}")
            
            return branch_to_dto(branch)