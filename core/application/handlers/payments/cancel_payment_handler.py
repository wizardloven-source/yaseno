# core/application/handlers/payments/cancel_payment_handler.py

"""
Cancel Payment Handler - معالج إلغاء دفعة
✅ مصحح: إصلاح توقيع المُنشئ (يأخذ uow فقط)
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import CancelPaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine


logger = logging.getLogger(__name__)


class CancelPaymentHandler(BaseHandler[CancelPaymentCommand, PaymentDTO]):
    """معالج إلغاء دفعة - مصحح: يأخذ uow فقط في المُنشئ"""
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine = None):
        # ✅ مصحح: معامل واحد فقط
        super().__init__(uow)
        self._posting_engine = posting_engine
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CancelPaymentCommand, user_context: UserContext) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments

            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)

            # إلغاء الدفعة
            cancelled_by = user_context.user_id if user_context else command.cancelled_by
            payment.cancel(cancelled_by, command.reason)

            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()

            logger.info(f"Payment {payment.code} cancelled by {cancelled_by}")

            return payment_to_dto(payment)