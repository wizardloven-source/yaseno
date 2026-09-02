# core/application/handlers/customers/get_customer_query_handler.py

"""
Get Customer Query Handler - استعلام لجلب عميل واحد
"""

import logging
from typing import Optional

from core.domain.customers.value_objects import CustomerId
from core.domain.customers.exceptions import CustomerNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.customers.commands import GetCustomerQuery
from core.application.customers.dtos import CustomerDTO
from core.application.customers.converters import customer_to_dto

logger = logging.getLogger(__name__)


class GetCustomerQueryHandler(BaseQueryHandler[GetCustomerQuery, Optional[CustomerDTO]]):
    """
    معالج استعلام لجلب عميل واحد بواسطة المعرف
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow

    def handle(self, query: GetCustomerQuery) -> Optional[CustomerDTO]:
        """
        تنفيذ جلب العميل
        
        Args:
            query: استعلام جلب العميل
        
        Returns:
            Optional[CustomerDTO]: بيانات العميل أو None
        """
        logger.debug(f"Fetching customer: {query.customer_id}")
        
        with self._uow:
            customer_repo = self._uow.customers
            customer_id = CustomerId.from_string(query.customer_id)
            customer = customer_repo.get_by_id(customer_id)
            
            if not customer:
                logger.warning(f"Customer not found: {query.customer_id}")
                return None
            
            return customer_to_dto(customer)