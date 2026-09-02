# core/application/handlers/workflow/request_approved_event_handler.py

"""
Request Approved Event Handler - معالج حدث الموافقة على الطلب
"""

import logging

from core.domain.workflow.events import RequestApprovedEvent
from core.domain.accounting.interfaces import IUnitOfWork

logger = logging.getLogger(__name__)


class RequestApprovedEventHandler:
    """
    معالج حدث الموافقة على الطلب
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: RequestApprovedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث الموافقة على الطلب
        """
        try:
            logger.info(f"Processing request approved event: {event.request_id}")
            # منطق المعالجة هنا
        except Exception as e:
            logger.error(f"Error processing request approved event: {e}")