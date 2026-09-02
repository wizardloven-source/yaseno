# core/application/handlers/customers/list_customers_query_handler.py
"""List Customers Query Handler"""

from typing import List

from core.domain.customers.value_objects import CustomerStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.customers.commands import ListCustomersQuery
from core.application.customers.dtos import CustomerDTO, CustomerListDTO
from core.application.customers.converters import customer_to_dto


class ListCustomersQueryHandler(BaseQueryHandler[ListCustomersQuery, CustomerListDTO]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def handle(self, query: ListCustomersQuery) -> CustomerListDTO:
        with self._uow:
            repo = self._uow.customers

            status = None
            if query.status:
                status_map = {
                    "active": CustomerStatus.ACTIVE,
                    "inactive": CustomerStatus.INACTIVE,
                    "suspended": CustomerStatus.SUSPENDED,
                    "blocked": CustomerStatus.BLOCKED,
                }
                status = status_map.get(query.status)

            customers = repo.list_all(
                status=status,
                include_deleted=query.include_deleted,
                limit=query.limit,
                offset=query.offset
            )

            total_count = len(customers)

            customer_dtos = [customer_to_dto(c) for c in customers if c]

            return CustomerListDTO(
                customers=customer_dtos,
                total_count=total_count,
                page=(query.offset // query.limit) + 1 if query.limit > 0 else 1,
                page_size=query.limit
            )