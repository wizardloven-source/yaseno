# core/application/handlers/purchasing/get_supplier_orders_query_handler.py
"""
Get Supplier Orders Query Handler - استعلام لجلب أوامر شراء مورد معين
"""

import logging
from typing import List
from uuid import UUID

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.purchasing.interfaces import IPurchaseOrderRepository
from core.domain.purchasing.entities import PurchaseOrder

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import GetSupplierOrdersQuery
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class GetSupplierOrdersQueryHandler(BaseQueryHandler[GetSupplierOrdersQuery, List[PurchaseOrderDTO]]):
    """
    معالج استعلام لجلب أوامر شراء مورد معين
    
    يقوم بجلب جميع أوامر الشراء لمورد محدد مع خيارات التصفية والترقيم.
    """
    
    def __init__(self, purchase_order_repo: IPurchaseOrderRepository):
        self._purchase_order_repo = purchase_order_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetSupplierOrdersQuery) -> List[PurchaseOrderDTO]:
        """
        تنفيذ جلب أوامر شراء المورد
        
        Args:
            query: استعلام جلب أوامر شراء المورد
        
        Returns:
            List[PurchaseOrderDTO]: قائمة أوامر الشراء
        """
        logger.debug(f"Fetching purchase orders for supplier: {query.supplier_id}")
        
        # جلب أوامر الشراء من المستودع
        orders = self._purchase_order_repo.list_by_supplier(
            supplier_id=query.supplier_id,
            limit=query.limit,
            offset=query.offset
        )
        
        # تصفية حسب الحالة إذا تم تحديدها
        if query.status:
            orders = [o for o in orders if o.status.value == query.status]
        
        logger.info(f"Found {len(orders)} purchase orders for supplier {query.supplier_id}")
        
        return [order_to_dto(order) for order in orders]