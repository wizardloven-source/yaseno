# core/application/handlers/payments/approve_payment_handler.py
"""
Approve Payment Handler - معالج اعتماد دفعة
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import ApprovePaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class ApprovePaymentHandler(BasePaymentHandler[ApprovePaymentCommand, PaymentDTO]):
    """
    معالج اعتماد دفعة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ApprovePaymentCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # التحقق من إمكانية الاعتماد
            if payment.is_completed:
                raise ValueError("Cannot approve completed payment")
            if payment.is_cancelled:
                raise ValueError("Cannot approve cancelled payment")
            
            # اعتماد الدفعة
            approved_by = user_context.user_id if user_context else command.approved_by
            payment.approve(approved_by)
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Payment {payment.code} approved by {approved_by}")
            
            return payment_to_dto(payment)