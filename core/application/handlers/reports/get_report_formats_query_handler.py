# core/application/handlers/reports/get_report_formats_query_handler.py

"""
Get Report Formats Query Handler - معالج استعلام صيغ التقارير
"""

import logging
from typing import List, Dict, Any

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.reports.commands import GetReportFormatsQuery

logger = logging.getLogger(__name__)


class GetReportFormatsQueryHandler(BaseQueryHandler[GetReportFormatsQuery, List[Dict[str, Any]]]):
    """
    معالج استعلام صيغ التقارير المدعومة    """

    def __init__(self):
        # لا يحتاج إلى UoW لأنه لا يتصل بقاعدة البيانات
        # ولكن يجب استدعاء super() مع uow=None
        pass

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetReportFormatsQuery) -> List[Dict[str, Any]]:
        """
        تنفيذ جلب صيغ التقارير المدعومة

        Args:
            query: استعلام صيغ التقارير

        Returns:
            List[Dict[str, Any]]: قائمة الصيغ المدعومة
        """
        logger.debug("Getting supported report formats")

        return [
            {
                'id': 'pdf',
                'name': 'PDF',
                'description': 'Portable Document Format',
                'extension': '.pdf',
                'icon': '📄',
                'supports_landscape': True,
                'supports_portrait': True
            },
            {
                'id': 'excel',
                'name': 'Excel',
                'description': 'Microsoft Excel Spreadsheet',
                'extension': '.xlsx',
                'icon': '📊',
                'supports_formulas': True,
                'supports_charts': True
            },
            {
                'id': 'csv',
                'name': 'CSV',
                'description': 'Comma Separated Values',
                'extension': '.csv',
                'icon': '📋',
                'supports_export': True
            },
            {
                'id': 'json',
                'name': 'JSON',
                'description': 'JavaScript Object Notation',
                'extension': '.json',
                'icon': '📦',
                'supports_api': True
            },
            {
                'id': 'html',
                'name': 'HTML',
                'description': 'HyperText Markup Language',
                'extension': '.html',
                'icon': '🌐',
                'supports_web_view': True
            }
        ]