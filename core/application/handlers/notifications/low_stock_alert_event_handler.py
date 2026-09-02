# core/application/handlers/notifications/low_stock_alert_event_handler.py
"""
Low Stock Alert Event Handler - معالج حدث تنبيه المخزون المنخفض
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.products.events import LowStockAlertEvent

logger = logging.getLogger(__name__)


class LowStockAlertEventHandler:
    """
    معالج حدث تنبيه المخزون المنخفض
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: LowStockAlertEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث تنبيه المخزون المنخفض
        """
        try:
            logger.info(f"Processing low stock alert for product: {event.product_code}")

            # جلب المستخدمين المستلمين للإشعار
            with self._uow:
                # جلب المديرين أو المسؤولين عن المخزون
                users = self._uow.users.list_by_role("inventory_manager")

                if not users:
                    logger.warning("No inventory managers found for low stock alert")
                    return

                # إرسال إشعار لكل مستخدم
                for user in users:
                    self._notification_service.send(
                        recipient=user.id,
                        title=f"تنبيه: مخزون منخفض - {event.product_code}",
                        message=f"المنتج {event.product_name} وصل إلى حد التحذير. الكمية الحالية: {event.current_quantity}",
                        notification_type="low_stock",
                        data={
                            "product_id": str(event.product_id),
                            "product_code": event.product_code,
                            "product_name": event.product_name,
                            "current_quantity": event.current_quantity,
                            "threshold": event.threshold
                        }
                    )

            logger.info(f"Low stock alert sent for {event.product_code}")

        except Exception as e:
            logger.error(f"Error processing low stock alert: {e}")