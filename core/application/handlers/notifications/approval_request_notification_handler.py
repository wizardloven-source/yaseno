# core/application/handlers/notifications/approval_request_notification_handler.py
"""
Approval Request Notification Handler - معالج إشعار طلب الموافقة
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.workflow.events import RequestSubmittedEvent

logger = logging.getLogger(__name__)


class ApprovalRequestNotificationHandler:
    """
    معالج إشعار طلب الموافقة
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: RequestSubmittedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث تقديم طلب الموافقة
        """
        try:
            logger.info(f"Processing approval request notification: {event.request_id}")

            # جلب المستخدمين الذين يحتاجون إلى الموافقة
            with self._uow:
                # جلب المديرين أو المسؤولين عن الموافقات
                users = self._uow.users.list_by_role("approver")

                if not users:
                    logger.warning("No approvers found for approval request")
                    return

                # إرسال إشعار لكل مستخدم
                for user in users:
                    self._notification_service.send(
                        recipient=user.id,
                        title=f"طلب موافقة جديد - {event.title}",
                        message=f"تم تقديم طلب موافقة {event.title} من قبل {event.submitted_by}",
                        notification_type="approval_request",
                        data={
                            "request_id": str(event.request_id),
                            "entity_type": event.entity_type.value,
                            "entity_id": event.entity_id,
                            "title": event.title,
                            "submitted_by": event.submitted_by
                        }
                    )

            logger.info(f"Approval request notification sent for {event.request_id}")

        except Exception as e:
            logger.error(f"Error processing approval request notification: {e}")