# core/application/handlers/payments/add_payment_line_handler.py
"""
Add Payment Line Handler - معالج إضافة سطر دفعة
"""

import logging
from decimal import Decimal

from core.domain.payments.entities import Payment, PaymentLine
from core.domain.payments.value_objects import PaymentId, Money
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import AddPaymentLineCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class AddPaymentLineHandler(BasePaymentHandler[AddPaymentLineCommand, PaymentDTO]):
    """
    معالج إضافة سطر دفعة
    
    مسؤولياته:
        1. التحقق من وجود الدفعة
        2. التحقق من إمكانية التعديل
        3. إضافة السطر
        4. حفظ التغييرات
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: AddPaymentLineCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # التحقق من إمكانية التعديل
            if payment.is_completed:
                raise ValueError("Cannot add line to completed payment")
            if payment.is_cancelled:
                raise ValueError("Cannot add line to cancelled payment")
            
            # إضافة السطر
            payment.add_line(
                reference_type=command.reference_type,
                reference_id=command.reference_id,
                amount=Money(command.amount, command.currency),
                notes=command.notes
            )
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Line added to payment {payment.code} by {user_context.user_id if user_context else 'system'}")
            
            return payment_to_dto(payment)