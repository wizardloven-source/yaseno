# core/application/handlers/fiscal/close_fiscal_year_handler.py

"""
Close Fiscal Year Handler - معالج إغلاق سنة مالية
"""

import logging

from core.domain.fiscal.value_objects import FiscalYearId
from core.domain.fiscal.interfaces import IFiscalYearRepository
from core.domain.accounting.services import ClosingService
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission


logger = logging.getLogger(__name__)


class CloseFiscalYearHandler(BaseHandler):
    """معالج إغلاق سنة مالية"""

    def __init__(self, uow: IUnitOfWork, closing_service: ClosingService):
        super().__init__(uow)
        self._closing_service = closing_service

    @require_permission(Permission.CLOSE_PERIOD)
    def handle(self, command, user_context: UserContext):
        """تنفيذ إغلاق سنة مالية"""
        with self._uow:
            fiscal_repo = self._uow.fiscal_years

            fiscal_year = fiscal_repo.get_by_id(FiscalYearId(command.fiscal_year_id))
            if not fiscal_year:
                raise ValueError(f"Fiscal year '{command.fiscal_year_id}' not found")

            # إغلاق جميع الفترات المفتوحة
            open_periods = [p for p in fiscal_year.periods if not p.is_closed]
            for period in open_periods:
                self._closing_service.close_period(str(period.reference), user_context.user_id)

            # إغلاق السنة المالية
            fiscal_year.close(user_context.user_id)
            fiscal_repo.save(fiscal_year)
            self._commit()

            logger.info(f"Fiscal year closed: {fiscal_year.code} by {user_context.user_id}")
            return {"success": True, "fiscal_year_id": command.fiscal_year_id}