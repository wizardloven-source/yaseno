# core/application/handlers/currency/set_exchange_rate_handler.py
"""
Set Exchange Rate Handler - معالج تعيين سعر الصرف
"""

import logging

from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.exceptions import CurrencyNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import SetExchangeRateCommand
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class SetExchangeRateHandler(BaseHandler[SetExchangeRateCommand, CurrencyDTO]):
    """
    معالج تعيين سعر الصرف لعملة معينة
    
    يحدد سعر الصرف من العملة الحالية إلى عملة أخرى
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: SetExchangeRateCommand, user_context: UserContext = None) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            # جلب العملة المصدر
            currency = repo.get_by_id(command.from_currency_id)
            if not currency:
                raise CurrencyNotFoundError(str(command.from_currency_id))
            
            updated_by = user_context.user_id if user_context else command.updated_by
            
            # تعيين سعر الصرف
            currency.set_exchange_rate(command.to_currency_code, command.rate, updated_by)
            
            # حفظ التغييرات
            repo.save(currency)
            self._commit()
            
            logger.info(
                f"Exchange rate set: 1 {currency.code.value} = {command.rate} {command.to_currency_code} "
                f"by {updated_by}"
            )
            
            return currency_to_dto(currency)