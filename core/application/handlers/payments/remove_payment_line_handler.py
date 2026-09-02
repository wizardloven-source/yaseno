# core/application/handlers/payments/remove_payment_line_handler.py
"""
Remove Payment Line Handler - معالج حذف سطر دفعة
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import RemovePaymentLineCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto

logger = logging.getLogger(__name__)


class RemovePaymentLineHandler(BasePaymentHandler[RemovePaymentLineCommand, PaymentDTO]):
    """
    معالج حذف سطر دفعة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: RemovePaymentLineCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # التحقق من إمكانية التعديل
            if payment.is_completed:
                raise ValueError("Cannot remove line from completed payment")
            if payment.is_cancelled:
                raise ValueError("Cannot remove line from cancelled payment")
            
            # حذف السطر
            removed = payment.remove_line(command.line_id)
            if not removed:
                raise ValueError(f"Line {command.line_id} not found")
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Line {command.line_id} removed from payment {payment.code}")
            
            return payment_to_dto(payment)