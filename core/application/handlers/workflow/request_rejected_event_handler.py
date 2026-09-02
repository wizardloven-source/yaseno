"""Request Rejected Event Handler - معالج حدث رفض الطلب"""

import logging

from core.domain.workflow.events import RequestRejectedEvent
from core.domain.accounting.interfaces import IUnitOfWork

logger = logging.getLogger(__name__)


class RequestRejectedEventHandler:
    """معالج حدث رفض الطلب"""

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: RequestRejectedEvent) -> None:
        """معالجة الحدث"""
        try:
            logger.info(f"Processing request rejected event: {event.request_id}")
            
            # هنا يمكن إضافة منطق إضافي مثل:
            # - إرسال إشعار للمقدم
            # - تحديث حالة الكيان المرتبط
            # - تسجيل في سجل التدقيق

            with self._uow:
                # منطق المعالجة هنا
                pass

        except Exception as e:
            logger.error(f"Error processing request rejected event: {e}")