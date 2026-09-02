"""List Fiscal Years Query Handler - معالج استعلام قائمة السنوات المالية"""

from typing import List
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission


class ListFiscalYearsHandler(BaseQueryHandler):
    """معالج استعلام قائمة السنوات المالية"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None) -> List:
        """تنفيذ جلب قائمة السنوات المالية"""
        with self._uow:
            repo = self._uow.fiscal_years
            fiscal_years = repo.get_all(
                include_closed=query.include_closed or False,
                include_archived=query.include_archived or False,
                limit=query.limit,
                offset=query.offset
            )
            return fiscal_years