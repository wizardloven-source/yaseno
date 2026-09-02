# core/application/handlers/fiscal/create_fiscal_year_handler.py
"""Create Fiscal Year Handler - معالج إنشاء سنة مالية جديدة"""

import logging
from datetime import date

from core.domain.fiscal.entities import FiscalYear
from core.domain.fiscal.value_objects import FiscalYearCode, FiscalPeriodType
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CreateFiscalYearHandler(BaseHandler):
    """معالج إنشاء سنة مالية جديدة"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext):
        """تنفيذ إنشاء سنة مالية جديدة"""
        with self._uow:
            repo = self._uow.fiscal_years
            
            # التحقق من عدم وجود سنة مالية بنفس الكود
            existing = repo.get_by_code(FiscalYearCode(command.code))
            if existing:
                raise ValueError(f"Fiscal year with code '{command.code}' already exists")
            
            # إنشاء السنة المالية
            fiscal_year = FiscalYear.create(
                code=command.code,
                name=command.name,
                start_date=command.start_date,
                end_date=command.end_date,
                periods_per_year=command.periods_per_year or 12,
                period_type=FiscalPeriodType(command.period_type or "month"),
                created_by=user_context.user_id
            )
            
            repo.save(fiscal_year)
            self._commit()
            
            logger.info(f"Fiscal year created: {fiscal_year.code} by {user_context.user_id}")
            return fiscal_year