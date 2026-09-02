# core/application/handlers/suppliers/search_suppliers_query_handler.py
"""
Search Suppliers Query Handler - استعلام للبحث عن الموردين
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.suppliers.commands import SearchSuppliersQuery
from core.application.suppliers.dtos import SupplierDTO
from core.application.suppliers.converters import supplier_to_dto

logger = logging.getLogger(__name__)


class SearchSuppliersQueryHandler:
    """
    معالج استعلام للبحث عن الموردين
    
    يقوم بالبحث عن الموردين باستخدام النص المدخل في الكود أو الاسم أو البريد الإلكتروني أو الهاتف.
    """

    def __init__(self, uow: IUnitOfWork):
        self._uow = uow

    def handle(self, query: SearchSuppliersQuery) -> List[SupplierDTO]:
        """
        تنفيذ البحث عن الموردين
        
        Args:
            query: استعلام البحث عن الموردين
        
        Returns:
            List[SupplierDTO]: قائمة الموردين المطابقين للبحث
        """
        logger.debug(f"Searching suppliers with text: {query.search_text}")

        with self._uow:
            supplier_repo = self._uow.suppliers

            suppliers = supplier_repo.search(
                search_text=query.search_text,
                limit=query.limit,
                offset=query.offset
            )

            logger.info(f"Found {len(suppliers)} suppliers matching '{query.search_text}'")

            return [supplier_to_dto(supplier) for supplier in suppliers]