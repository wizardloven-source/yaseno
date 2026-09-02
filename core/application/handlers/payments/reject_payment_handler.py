# core/application/handlers/payments/reject_payment_handler.py
"""
Reject Payment Handler - معالج رفض دفعة
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import RejectPaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto

logger = logging.getLogger(__name__)


class RejectPaymentHandler(BasePaymentHandler[RejectPaymentCommand, PaymentDTO]):
    """
    معالج رفض دفعة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: RejectPaymentCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # رفض الدفعة
            rejected_by = user_context.user_id if user_context else command.rejected_by
            payment.reject(rejected_by, command.reason)
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Payment {payment.code} rejected by {rejected_by}")
            
            return payment_to_dto(payment)