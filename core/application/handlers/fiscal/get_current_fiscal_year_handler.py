"""Get Current Fiscal Year Query Handler - معالج استعلام جلب السنة المالية الحالية"""

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission


class GetCurrentFiscalYearHandler(BaseQueryHandler):
    """معالج استعلام جلب السنة المالية الحالية"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """تنفيذ جلب السنة المالية الحالية"""
        with self._uow:
            repo = self._uow.fiscal_years
            fiscal_year = repo.get_current()
            return fiscal_year