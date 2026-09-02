# core/application/handlers/workflow/request_submitted_event_handler.py

"""
Request Submitted Event Handler - معالج حدث تقديم الطلب
"""

import logging

from core.domain.workflow.events import RequestSubmittedEvent
from core.domain.accounting.interfaces import IUnitOfWork

logger = logging.getLogger(__name__)


class RequestSubmittedEventHandler:
    """
    معالج حدث تقديم الطلب
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: RequestSubmittedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث تقديم الطلب
        """
        try:
            logger.info(f"Processing request submitted event: {event.request_id}")
            # منطق المعالجة هنا
        except Exception as e:
            logger.error(f"Error processing request submitted event: {e}")