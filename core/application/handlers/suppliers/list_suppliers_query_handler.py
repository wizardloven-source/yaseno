# C:\Users\MTC\Desktop\erpya\core\application\handlers\suppliers\list_suppliers_query_handler.py
"""List Suppliers Query Handler - استعلام لجلب قائمة الموردين"""

import logging
from typing import List

from core.domain.suppliers.value_objects import SupplierStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.suppliers.commands import ListSuppliersQuery
from core.application.suppliers.dtos import SupplierDTO, SupplierListDTO
from core.application.suppliers.converters import supplier_to_dto

logger = logging.getLogger(__name__)


class ListSuppliersQueryHandler(BaseQueryHandler[ListSuppliersQuery, SupplierListDTO]):
    """Handler for listing suppliers with filtering and pagination"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListSuppliersQuery) -> SupplierListDTO:
        with self._uow:
            repo = self._uow.suppliers
            
            # تحويل حالة الفلتر
            status = None
            if query.status:
                status_map = {
                    "active": SupplierStatus.ACTIVE,
                    "inactive": SupplierStatus.INACTIVE,
                    "suspended": SupplierStatus.SUSPENDED,
                    "blocked": SupplierStatus.BLOCKED,
                }
                status = status_map.get(query.status)
            
            # جلب الموردين
            suppliers = repo.list_all(
                status=status,
                include_deleted=query.include_deleted,
                limit=query.limit,
                offset=query.offset
            )
            
            # حساب العدد الإجمالي
            total_count = repo.count(
                status=status,
                include_deleted=query.include_deleted
            )
            
            # حساب معلومات الصفحة
            page = (query.offset // query.limit) + 1 if query.limit > 0 else 1
            page_size = query.limit
            
            # تحويل إلى DTOs
            supplier_dtos = [supplier_to_dto(s) for s in suppliers if s]
            
            logger.debug(f"Listed {len(supplier_dtos)} suppliers (total: {total_count})")
            
            return SupplierListDTO(
                suppliers=supplier_dtos,
                total_count=total_count,
                page=page,
                page_size=page_size
            )