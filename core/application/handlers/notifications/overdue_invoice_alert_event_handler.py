# core/application/handlers/notifications/overdue_invoice_alert_event_handler.py
"""
Overdue Invoice Alert Event Handler - معالج حدث تنبيه الفواتير المتأخرة
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.invoicing.events import InvoiceOverdueEvent

logger = logging.getLogger(__name__)


class OverdueInvoiceAlertEventHandler:
    """
    معالج حدث تنبيه الفواتير المتأخرة
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: InvoiceOverdueEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث تنبيه الفواتير المتأخرة
        """
        try:
            logger.info(f"Processing overdue invoice alert: {event.invoice_number}")

            with self._uow:
                # جلب المستخدمين المستلمين للإشعار
                users = self._uow.users.list_by_role("finance_manager")

                # إرسال إشعار لكل مستخدم
                for user in users:
                    self._notification_service.send(
                        recipient=user.id,
                        title=f"تنبيه: فاتورة متأخرة - {event.invoice_number}",
                        message=f"الفاتورة {event.invoice_number} للعميل {event.customer_name} متأخرة. المبلغ: {event.amount} {event.currency}",
                        notification_type="overdue_invoice",
                        data={
                            "invoice_id": str(event.invoice_id),
                            "invoice_number": event.invoice_number,
                            "customer_name": event.customer_name,
                            "amount": event.amount,
                            "currency": event.currency,
                            "days_overdue": event.days_overdue
                        }
                    )

            logger.info(f"Overdue invoice alert sent for {event.invoice_number}")

        except Exception as e:
            logger.error(f"Error processing overdue invoice alert: {e}")