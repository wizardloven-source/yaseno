# core/application/handlers/notifications/payment_completed_notification_handler.py
"""
Payment Completed Notification Handler - معالج إشعار إكمال الدفعة
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.payments.events import PaymentCompletedEvent

logger = logging.getLogger(__name__)


class PaymentCompletedNotificationHandler:
    """
    معالج إشعار إكمال الدفعة
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: PaymentCompletedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث إكمال الدفعة
        """
        try:
            logger.info(f"Processing payment completed notification: {event.payment_code}")

            # تحديد المستلم
            recipient = None
            if event.customer_id:
                recipient = event.customer_id
            elif event.supplier_id:
                recipient = event.supplier_id

            if not recipient:
                logger.warning(f"No recipient found for payment {event.payment_code}")
                return

            # إرسال إشعار
            self._notification_service.send(
                recipient=recipient,
                title=f"تم إكمال الدفعة - {event.payment_code}",
                message=f"تم إكمال الدفعة {event.payment_code} بقيمة {event.amount} {event.currency}",
                notification_type="payment_completed",
                data={
                    "payment_id": str(event.payment_id),
                    "payment_code": event.payment_code,
                    "amount": event.amount,
                    "currency": event.currency,
                    "fund_id": event.fund_id
                }
            )

            logger.info(f"Payment completed notification sent for {event.payment_code}")

        except Exception as e:
            logger.error(f"Error processing payment completed notification: {e}")