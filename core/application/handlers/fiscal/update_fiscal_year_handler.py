"""Update Fiscal Year Handler - معالج تحديث سنة مالية"""

import logging

from core.domain.fiscal.value_objects import FiscalYearId, FiscalYearCode
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.shared.exceptions import ConcurrentModificationError


logger = logging.getLogger(__name__)


class UpdateFiscalYearHandler(BaseHandler):
    """معالج تحديث سنة مالية"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext):
        """تنفيذ تحديث سنة مالية"""
        with self._uow:
            repo = self._uow.fiscal_years
            
            fiscal_year = repo.get_by_id(FiscalYearId(command.fiscal_year_id))
            if not fiscal_year:
                raise ValueError(f"Fiscal year '{command.fiscal_year_id}' not found")
            
            # التحقق من الإصدار (Optimistic Locking)
            if fiscal_year.version != command.version:
                raise ConcurrentModificationError(
                    "FiscalYear",
                    command.fiscal_year_id,
                    command.version,
                    fiscal_year.version
                )
            
            # تحديث البيانات
            if command.name:
                fiscal_year.name = command.name
            if command.status:
                fiscal_year.status = command.status
            
            fiscal_year.updated_by = user_context.user_id
            repo.save(fiscal_year)
            self._commit()
            
            logger.info(f"Fiscal year updated: {fiscal_year.code} by {user_context.user_id}")
            return fiscal_year