# core/application/handlers/sites/get_site_statistics_query_handler.py
"""
Get Site Statistics Query Handler - معالج استعلام إحصائيات الموقع
"""

import logging
from typing import Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import GetSiteStatisticsQuery

logger = logging.getLogger(__name__)


class GetSiteStatisticsQueryHandler(BaseQueryHandler[GetSiteStatisticsQuery, Dict[str, Any]]):
    """
    معالج استعلام إحصائيات الموقع
    
    يقوم بجلب إحصائيات الموقع مثل عدد الفواتير والمبيعات.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetSiteStatisticsQuery, user_context: UserContext = None) -> Dict[str, Any]:
        """
        تنفيذ جلب إحصائيات الموقع
        
        Args:
            query: استعلام إحصائيات الموقع
        
        Returns:
            Dict[str, Any]: إحصائيات الموقع
        """
        logger.debug(f"Fetching statistics for site: {query.site_id}")

        with self._uow:
            site_repo = self._uow.sites
            
            # جلب الموقع
            site = site_repo.get_by_id(query.site_id)
            if not site:
                return {
                    "success": False,
                    "message": f"Site '{query.site_id}' not found"
                }
            
            # جلب إحصائيات من الفواتير
            try:
                invoice_stats = self._uow.invoices.get_site_statistics(str(query.site_id))
            except Exception:
                invoice_stats = {
                    "total_invoices": 0,
                    "total_amount": 0,
                    "average_amount": 0
                }
            
            # جلب إحصائيات من أوامر الشراء
            try:
                purchase_stats = self._uow.purchase_orders.get_site_statistics(str(query.site_id))
            except Exception:
                purchase_stats = {
                    "total_orders": 0,
                    "total_amount": 0
                }
            
            return {
                "success": True,
                "site": {
                    "id": str(site.id),
                    "code": site.code.value,
                    "name": site.name,
                    "city": site.city,
                    "country": site.country,
                    "is_active": site.is_active,
                    "is_default": site.is_default
                },
                "statistics": {
                    "invoices": invoice_stats,
                    "purchase_orders": purchase_stats,
                    "total_transactions": invoice_stats.get("total_invoices", 0) + purchase_stats.get("total_orders", 0),
                    "total_amount": invoice_stats.get("total_amount", 0) + purchase_stats.get("total_amount", 0)
                }
            }