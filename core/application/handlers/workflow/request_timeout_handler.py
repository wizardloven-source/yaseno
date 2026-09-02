"""
Request Timeout Handler - معالج انتهاء صلاحية الطلب
✅ مصحح: إضافة workflow_service كمعامل اختياري
"""

import logging

from core.domain.workflow.events import RequestExpiredEvent
from core.domain.accounting.interfaces import IUnitOfWork

logger = logging.getLogger(__name__)


class RequestTimeoutHandler:
    """
    معالج انتهاء صلاحية الطلب
    ✅ مصحح: يقبل workflow_service اختيارياً
    """

    def __init__(self, uow: IUnitOfWork, notification_service, workflow_service=None):
        """
        Args:
            uow: Unit of Work
            notification_service: خدمة الإشعارات
            workflow_service: خدمة سير العمل (اختياري)
        """
        self._uow = uow
        self._notification_service = notification_service
        self._workflow_service = workflow_service  # يمكن استخدامه لاحقاً

    def __call__(self, event: RequestExpiredEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث انتهاء صلاحية الطلب
        """
        try:
            logger.info(f"Processing request timeout event: {event.request_id}")

            # يمكن استخدام self._workflow_service هنا إذا لزم الأمر
            # مثلاً: self._workflow_service.handle_timeout(event.request_id)

            with self._uow:
                # منطق المعالجة هنا
                pass

        except Exception as e:
            logger.error(f"Error processing request timeout event: {e}")