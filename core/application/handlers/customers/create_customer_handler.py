# core/application/handlers/customers/create_customer_handler.py
"""Create Customer Handler"""

import logging
from decimal import Decimal

from core.domain.customers.entities import Customer
from core.domain.customers.value_objects import CustomerCode, ContactInfo, Address
from core.domain.customers.exceptions import DuplicateCustomerCodeError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import CreateCustomerCommand
from core.application.customers.dtos import CustomerDTO
from core.application.customers.converters import customer_to_dto

logger = logging.getLogger(__name__)


class CreateCustomerHandler(BaseHandler[CreateCustomerCommand, CustomerDTO]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateCustomerCommand, user_context: UserContext) -> CustomerDTO:
        with self._uow:
            repo = self._uow.customers

            customer_code = CustomerCode(command.code)
            existing = repo.get_by_code(customer_code)
            if existing:
                raise DuplicateCustomerCodeError(command.code)

            contact_info = ContactInfo(
                email=command.email,
                phone=command.phone,
                mobile=command.mobile
            )

            address = Address(
                street=command.street,
                city=command.city,
                country=command.country
            )

            customer = Customer.create(
                code=customer_code,
                name=command.name,
                contact_info=contact_info,
                address=address,
                tax_number=command.tax_number,
                credit_limit=command.credit_limit,
                currency=command.currency,
                notes=command.notes,
                created_by=user_context.user_id
            )

            repo.save(customer)
            self._commit()

            logger.info(f"Customer created: {customer.code} - {customer.name}")

            return customer_to_dto(customer)