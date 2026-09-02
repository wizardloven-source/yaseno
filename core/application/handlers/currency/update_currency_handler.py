# core/application/handlers/currency/update_currency_handler.py
"""
Update Currency Handler - معالج تحديث عملة موجودة
"""

import logging
from uuid import UUID

from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.exceptions import CurrencyNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import UpdateCurrencyCommand
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class UpdateCurrencyHandler(BaseHandler[UpdateCurrencyCommand, CurrencyDTO]):
    """
    معالج تحديث عملة موجودة
    
    يستخدم Optimistic Locking عبر الـ version
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateCurrencyCommand, user_context: UserContext = None) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            # جلب العملة من قاعدة البيانات
            currency = repo.get_by_id(command.currency_id)
            if not currency:
                raise CurrencyNotFoundError(str(command.currency_id))
            
            # التحقق من التزامن (Optimistic Locking)
            if currency.version != command.version:
                raise ConcurrentModificationError(
                    "Currency",
                    str(command.currency_id),
                    command.version,
                    currency.version
                )
            
            # تحديث البيانات
            updated_by = user_context.user_id if user_context else command.updated_by
            
            currency.update(
                name=command.name,
                symbol=command.symbol,
                decimal_places=command.decimal_places,
                is_active=command.is_active,
                updated_by=updated_by
            )
            
            # إذا تم تغيير العملة إلى الأساس، تعطيل العملات الأساسية الأخرى
            if command.is_base and not currency.is_base:
                base_currency = repo.get_base_currency()
                if base_currency and base_currency.id != currency.id:
                    base_currency.is_base = False
                    repo.save(base_currency)
                currency.is_base = True
            
            # حفظ التغييرات
            repo.save(currency)
            self._commit()
            
            logger.info(f"Currency updated: {currency.code.value} - {currency.name} (version {currency.version})")
            
            return currency_to_dto(currency)