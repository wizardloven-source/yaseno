# core/application/handlers/payments/delete_draft_payment_handler.py
"""
Delete Draft Payment Handler - معالج حذف دفعة مسودة
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import DeleteDraftPaymentCommand
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class DeleteDraftPaymentHandler(BasePaymentHandler[DeleteDraftPaymentCommand, dict]):
    """
    معالج حذف دفعة مسودة (غير مكتملة)
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteDraftPaymentCommand, user_context: UserContext = None) -> dict:
        with self._uow:
            repo = self._uow.payments
            
            # جلب الدفعة
            payment_id = PaymentId.from_string(command.payment_id)
            payment = repo.get_by_id(payment_id)
            
            if not payment:
                return {
                    "success": False,
                    "message": f"Payment {command.payment_id} not found",
                    "payment_id": command.payment_id
                }
            
            # التحقق من إمكانية الحذف (فقط المسودة)
            if payment.status != "draft":
                return {
                    "success": False,
                    "message": f"Cannot delete payment in status '{payment.status}'",
                    "payment_id": command.payment_id
                }
            
            # حذف الدفعة
            result = repo.delete_draft(payment_id)
            
            if result:
                self._commit()
                logger.info(f"Draft payment {payment.code} deleted by {user_context.user_id if user_context else 'system'}")
            
            return {
                "success": result,
                "message": "Payment deleted successfully" if result else "Failed to delete payment",
                "payment_id": command.payment_id
            }