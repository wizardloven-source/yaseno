# core/application/handlers/reports/delete_scheduled_report_handler.py
"""
Delete Scheduled Report Handler - معالج حذف جدولة تقرير
"""

import logging

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class DeleteScheduledReportHandler(BaseHandler):
    """
    معالج حذف جدولة تقرير
    """
    
    def __init__(self, uow):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ حذف جدولة تقرير
        
        Args:
            command: DeleteScheduledReportCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الحذف
        """
        logger.info(f"Deleting scheduled report: {command.schedule_id}")
        
        with self._uow:
            # جلب الجدولة
            schedule = self._uow.report_schedules.get_by_id(command.schedule_id)
            if not schedule:
                return {
                    "success": False,
                    "message": f"Scheduled report '{command.schedule_id}' not found"
                }
            
            # حذف الجدولة
            result = self._uow.report_schedules.delete(command.schedule_id)
            self._commit()
            
            logger.info(f"Scheduled report deleted: {command.schedule_id}")
            
            return {
                "success": result,
                "message": "Scheduled report deleted successfully" if result else "Failed to delete scheduled report"
            }