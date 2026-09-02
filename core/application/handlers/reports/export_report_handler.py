# core/application/handlers/reports/export_report_handler.py
"""
Export Report Handler - معالج تصدير تقرير
"""

import logging
import json
import csv
from pathlib import Path

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ExportReportHandler(BaseHandler):
    """
    معالج تصدير تقرير
    
    يقوم بتصدير التقرير إلى صيغ مختلفة (PDF, Excel, CSV, JSON)
    """
    
    def __init__(self, uow, report_export_service):
        super().__init__(uow)
        self._export_service = report_export_service
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تصدير تقرير
        
        Args:
            command: ExportReportCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة التصدير
        """
        logger.info(f"Exporting report: {command.report_id} as {command.format}")
        
        with self._uow:
            # جلب التقرير
            report = self._uow.reports.get_by_id(command.report_id)
            if not report:
                return {
                    "success": False,
                    "message": f"Report '{command.report_id}' not found"
                }
            
            # تصدير التقرير
            result = self._export_service.export(
                report=report,
                format=command.format,
                export_path=command.export_path,
                include_details=command.include_details,
                user_id=user_context.user_id if user_context else "system"
            )
            
            self._commit()
            
            logger.info(f"Report exported: {result.get('file_path', 'unknown')}")
            return result