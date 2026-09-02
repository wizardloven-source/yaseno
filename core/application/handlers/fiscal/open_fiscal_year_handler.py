"""Open Fiscal Year Handler - معالج فتح سنة مالية"""

import logging

from core.domain.fiscal.value_objects import FiscalYearId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission


logger = logging.getLogger(__name__)


class OpenFiscalYearHandler(BaseHandler):
    """معالج فتح سنة مالية"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext):
        """تنفيذ فتح سنة مالية"""
        with self._uow:
            repo = self._uow.fiscal_years
            
            fiscal_year = repo.get_by_id(FiscalYearId(command.fiscal_year_id))
            if not fiscal_year:
                raise ValueError(f"Fiscal year '{command.fiscal_year_id}' not found")
            
            # فتح السنة المالية
            fiscal_year.open(user_context.user_id)
            repo.save(fiscal_year)
            self._commit()
            
            logger.info(f"Fiscal year opened: {fiscal_year.code} by {user_context.user_id}")
            return {"success": True, "fiscal_year_id": command.fiscal_year_id}