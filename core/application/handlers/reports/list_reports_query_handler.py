# core/application/handlers/reports/list_reports_query_handler.py
"""
List Reports Query Handler - معالج استعلام قائمة التقارير
"""

import logging
from typing import List

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ListReportsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام قائمة التقارير المتاحة
    """
    
    def __init__(self, report_repo):
        self._report_repo = report_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None) -> List[dict]:
        """
        تنفيذ جلب قائمة التقارير
        
        Args:
            query: ListReportsQuery
            user_context: سياق المستخدم
        
        Returns:
            List[dict]: قائمة التقارير
        """
        logger.debug(f"Listing reports: category={query.category}")
        
        # جلب التقارير من المستودع
        reports = self._report_repo.list_all(
            category=query.category,
            limit=query.limit,
            offset=query.offset
        )
        
        return [{
            'id': report.id,
            'name': report.name,
            'description': report.description,
            'type': report.report_type,
            'category': report.category,
            'format': report.format,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'created_by': report.created_by
        } for report in reports]