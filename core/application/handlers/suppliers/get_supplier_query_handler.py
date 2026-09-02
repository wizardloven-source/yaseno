# C:\Users\MTC\Desktop\erpya\core\application\handlers\suppliers\get_supplier_query_handler.py
"""Get Supplier Query Handler - استعلام لجلب مورد واحد"""

import logging

from core.domain.suppliers.value_objects import SupplierId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.suppliers.commands import GetSupplierQuery
from core.application.suppliers.dtos import SupplierDTO
from core.application.suppliers.converters import supplier_to_dto

logger = logging.getLogger(__name__)


class GetSupplierQueryHandler(BaseQueryHandler[GetSupplierQuery, SupplierDTO]):
    """Handler for retrieving a single supplier"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetSupplierQuery) -> SupplierDTO:
        with self._uow:
            repo = self._uow.suppliers
            supplier_id = SupplierId.from_string(query.supplier_id)
            supplier = repo.get_by_id(supplier_id)
            
            if not supplier:
                return None
            
            logger.debug(f"Retrieved supplier: {supplier.code}")
            return supplier_to_dto(supplier)