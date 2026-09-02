# core/application/handlers/customers/search_customers_query_handler.py

"""
Search Customers Query Handler - استعلام للبحث عن العملاء
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import SearchCustomersQuery
from core.application.customers.dtos import CustomerDTO
from core.application.customers.converters import customer_to_dto

logger = logging.getLogger(__name__)


class SearchCustomersQueryHandler(BaseQueryHandler[SearchCustomersQuery, List[CustomerDTO]]):
    """
    معالج استعلام للبحث عن العملاء

    يقوم بالبحث عن العملاء باستخدام النص المدخل في الكود أو الاسم أو البريد الإلكتروني أو الهاتف.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: SearchCustomersQuery) -> List[CustomerDTO]:
        """
        تنفيذ البحث عن العملاء

        Args:
            query: استعلام البحث عن العملاء

        Returns:
            List[CustomerDTO]: قائمة العملاء المطابقين للبحث
        """
        logger.debug(f"Searching customers with text: {query.search_text}")

        with self._uow:
            customer_repo = self._uow.customers

            # البحث عن العملاء
            customers = customer_repo.search(
                search_text=query.search_text,
                limit=query.limit,
                offset=query.offset
            )

            logger.info(f"Found {len(customers)} customers matching '{query.search_text}'")

            return [customer_to_dto(customer) for customer in customers]