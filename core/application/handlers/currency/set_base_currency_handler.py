# core/application/handlers/currency/set_base_currency_handler.py
"""
Set Base Currency Handler - معالج تعيين العملة الأساسية
"""

import logging
from uuid import UUID

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import SetBaseCurrencyCommand
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class SetBaseCurrencyHandler(BaseHandler[SetBaseCurrencyCommand, CurrencyDTO]):
    """
    معالج تعيين العملة الأساسية للنظام
    
    مسؤولياته:
        1. التحقق من وجود العملة
        2. تعطيل العملة الأساسية الحالية
        3. تعيين العملة الجديدة كأساس
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: SetBaseCurrencyCommand, user_context: UserContext = None) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            # 1. جلب العملة
            currency = repo.get_by_id(command.currency_id)
            if not currency:
                raise ValueError(f"Currency {command.currency_id} not found")
            
            # 2. تعطيل العملة الأساسية الحالية
            current_base = repo.get_base_currency()
            if current_base and current_base.id != currency.id:
                current_base.is_base = False
                repo.save(current_base)
            
            # 3. تعيين العملة الجديدة كأساس
            currency.is_base = True
            repo.save(currency)
            self._commit()
            
            logger.info(f"Base currency set to: {currency.code.value} - {currency.name}")
            
            return currency_to_dto(currency)