# core/application/handlers/reports/run_scheduled_report_handler.py
"""
Run Scheduled Report Handler - معالج تنفيذ تقرير مجدول
"""

import logging

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class RunScheduledReportHandler(BaseHandler):
    """
    معالج تنفيذ تقرير مجدول
    
    يقوم بتشغيل تقرير مجدول يدوياً
    """
    
    def __init__(self, uow, report_generator, report_export_service):
        super().__init__(uow)
        self._report_generator = report_generator
        self._export_service = report_export_service
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تقرير مجدول
        
        Args:
            command: RunScheduledReportCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة التنفيذ
        """
        logger.info(f"Running scheduled report: {command.schedule_id}")
        
        with self._uow:
            # جلب الجدولة
            schedule = self._uow.report_schedules.get_by_id(command.schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "message": f"Scheduled report '{command.schedule_id}' not found"
                }
            
            # توليد التقرير
            report = self._report_generator.generate(
                report_type=schedule.report_type,
                parameters=schedule.parameters,
                format=schedule.format,
                user_id=user_context.user_id if user_context else "system"
            )
            
            # تصدير التقرير إذا كان مطلوباً
            export_result = None
            if schedule.auto_export:
                export_result = self._export_service.export(
                    report=report,
                    format=schedule.format,
                    user_id=user_context.user_id if user_context else "system"
                )
            
            # تحديث آخر تنفيذ
            schedule.last_run = datetime.now()
            self._uow.report_schedules.save(schedule)
            self._commit()
            
            logger.info(f"Scheduled report executed: {command.schedule_id}")
            
            return {
                "success": True,
                "report": report,
                "export": export_result,
                "message": "Scheduled report executed successfully"
            }