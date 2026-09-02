"""Get Fiscal Year Query Handler - معالج استعلام جلب سنة مالية"""

from core.domain.fiscal.value_objects import FiscalYearId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission


class GetFiscalYearHandler(BaseQueryHandler):
    """معالج استعلام جلب سنة مالية"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """تنفيذ جلب السنة المالية"""
        with self._uow:
            repo = self._uow.fiscal_years
            fiscal_year = repo.get_by_id(FiscalYearId(query.fiscal_year_id))
            return fiscal_year