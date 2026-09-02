# core/application/handlers/payments/update_payment_handler.py
"""
Update Payment Handler - معالج تحديث دفعة موجودة
"""

import logging

from core.domain.payments.value_objects import PaymentId, PaymentMethod
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import UpdatePaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class UpdatePaymentHandler(BasePaymentHandler[UpdatePaymentCommand, PaymentDTO]):
    """
    معالج تحديث دفعة موجودة
    
    يستخدم Optimistic Locking عبر الـ version
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdatePaymentCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة من قاعدة البيانات
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # التحقق من التزامن (Optimistic Locking)
            if payment.version != command.version:
                raise ConcurrentModificationError(
                    "Payment",
                    str(command.payment_id),
                    command.version,
                    payment.version
                )
            
            # تحويل طريقة الدفع
            payment_method = None
            if command.payment_method:
                method_map = {
                    "cash": PaymentMethod.CASH,
                    "check": PaymentMethod.CHECK,
                    "transfer": PaymentMethod.TRANSFER,
                    "credit": PaymentMethod.CREDIT,
                    "card": PaymentMethod.CARD,
                }
                payment_method = method_map.get(command.payment_method)
            
            # تحديث البيانات
            updated_by = user_context.user_id if user_context else command.updated_by
            
            payment.update(
                notes=command.notes,
                payment_method=payment_method,
                fund_id=command.fund_id,
                updated_by=updated_by
            )
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Payment updated: {payment.code} (version {payment.version}) by {updated_by}")
            
            return payment_to_dto(payment)