# core/application/handlers/reports/schedule_report_handler.py
"""
Schedule Report Handler - معالج جدولة تقرير
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ScheduleReportHandler(BaseHandler):
    """
    معالج جدولة تقرير
    
    يقوم بجدولة تقرير ليتم توليده تلقائياً في وقت محدد
    """
    
    def __init__(self, uow, report_schedule_service):
        super().__init__(uow)
        self._schedule_service = report_schedule_service
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ جدولة تقرير
        
        Args:
            command: ScheduleReportCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الجدولة
        """
        logger.info(f"Scheduling report: {command.report_type}")
        
        with self._uow:
            # إنشاء جدولة جديدة
            schedule = self._schedule_service.create_schedule(
                report_type=command.report_type,
                parameters=command.parameters,
                frequency=command.frequency,
                start_date=command.start_date,
                end_date=command.end_date,
                recipients=command.recipients,
                format=command.format,
                user_id=user_context.user_id if user_context else "system"
            )
            
            self._uow.report_schedules.save(schedule)
            self._commit()
            
            logger.info(f"Report scheduled: {schedule.id}")
            
            return {
                "success": True,
                "schedule_id": schedule.id,
                "message": f"Report scheduled successfully with frequency: {command.frequency}"
            }