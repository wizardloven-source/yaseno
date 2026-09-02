# core/application/handlers/currency/delete_currency_handler.py
"""
Delete Currency Handler - معالج حذف عملة
"""

import logging
from uuid import UUID

from core.domain.currency.exceptions import CurrencyNotFoundError, CannotDeleteBaseCurrencyError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import DeleteCurrencyCommand

logger = logging.getLogger(__name__)


class DeleteCurrencyHandler(BaseHandler[DeleteCurrencyCommand, dict]):
    """
    معالج حذف عملة
    
    ملاحظات:
        1. لا يمكن حذف العملة الأساسية (Base Currency)
        2. الحذف هو Soft Delete (تعطيل فقط) - يتم تعيين is_active = False
        3. يمكن استخدام الحذف الدائم في المستقبل إذا لزم الأمر
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteCurrencyCommand, user_context: UserContext = None) -> dict:
        with self._uow:
            repo = self._uow.currencies
            
            # جلب العملة
            currency = repo.get_by_id(command.currency_id)
            if not currency:
                raise CurrencyNotFoundError(str(command.currency_id))
            
            # لا يمكن حذف العملة الأساسية
            if currency.is_base:
                raise CannotDeleteBaseCurrencyError(currency.code.value)
            
            deleted_by = user_context.user_id if user_context else command.deleted_by
            
            # حذف ناعم (تعطيل فقط)
            currency.update(is_active=False, updated_by=deleted_by)
            repo.save(currency)
            self._commit()
            
            logger.info(f"Currency deactivated: {currency.code.value} - {currency.name} by {deleted_by}")
            
            return {
                "success": True,
                "currency_id": str(command.currency_id),
                "message": f"Currency {currency.code.value} has been deactivated"
            }