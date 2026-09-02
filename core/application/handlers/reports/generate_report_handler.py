# core/application/handlers/reports/generate_report_handler.py
"""
Generate Report Handler - معالج توليد تقرير
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GenerateReportHandler(BaseHandler):
    """
    معالج توليد تقرير
    
    يقوم بتوليد تقرير بناءً على النوع والمعلمات المحددة
    """
    
    def __init__(self, uow, report_generator):
        super().__init__(uow)
        self._report_generator = report_generator
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير
        
        Args:
            command: GenerateReportCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: التقرير المولد
        """
        logger.info(f"Generating report: {command.report_type}")
        
        with self._uow:
            # توليد التقرير حسب النوع
            report = self._report_generator.generate(
                report_type=command.report_type,
                parameters=command.parameters,
                format=command.format,
                user_id=user_context.user_id if user_context else "system"
            )
            
            # حفظ التقرير إذا كان مطلوباً
            if command.save_report:
                self._uow.reports.save(report)
                self._commit()
            
            logger.info(f"Report generated: {report.get('id', 'unknown')}")
            return report