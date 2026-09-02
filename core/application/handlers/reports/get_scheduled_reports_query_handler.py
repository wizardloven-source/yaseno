# core/application/handlers/reports/get_scheduled_reports_query_handler.py
"""
Get Scheduled Reports Query Handler - معالج استعلام التقارير المجدولة
"""

import logging
from typing import List

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetScheduledReportsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام التقارير المجدولة
    """
    
    def __init__(self, report_schedule_repo):
        self._report_schedule_repo = report_schedule_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None) -> List[dict]:
        """
        تنفيذ جلب التقارير المجدولة
        
        Args:
            query: GetScheduledReportsQuery
            user_context: سياق المستخدم
        
        Returns:
            List[dict]: قائمة التقارير المجدولة
        """
        logger.debug(f"Listing scheduled reports")
        
        # جلب الجداول من المستودع
        schedules = self._report_schedule_repo.list_all(
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset
        )
        
        return [{
            'id': schedule.id,
            'report_type': schedule.report_type,
            'frequency': schedule.frequency,
            'parameters': schedule.parameters,
            'format': schedule.format,
            'recipients': schedule.recipients,
            'start_date': schedule.start_date.isoformat() if schedule.start_date else None,
            'end_date': schedule.end_date.isoformat() if schedule.end_date else None,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
            'is_active': schedule.is_active,
            'created_at': schedule.created_at.isoformat() if schedule.created_at else None
        } for schedule in schedules]