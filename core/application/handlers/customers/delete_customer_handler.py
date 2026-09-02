# core/application/handlers/customers/delete_customer_handler.py
"""Delete Customer Handler"""

import logging

from core.domain.customers.value_objects import CustomerId
from core.domain.customers.exceptions import CustomerNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import DeleteCustomerCommand

logger = logging.getLogger(__name__)


class DeleteCustomerHandler(BaseHandler[DeleteCustomerCommand, dict]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteCustomerCommand, user_context: UserContext) -> dict:
        with self._uow:
            repo = self._uow.customers

            customer_id = CustomerId.from_string(command.customer_id)
            customer = repo.get_by_id(customer_id)

            if not customer:
                raise CustomerNotFoundError(command.customer_id)

            if command.permanent:
                result = repo.delete(customer_id, permanent=True)
                message = "Customer permanently deleted"
            else:
                customer.soft_delete(user_context.user_id)
                repo.save(customer)
                result = True
                message = "Customer soft deleted"

            self._commit()

            logger.info(f"Customer deleted: {customer.code}")

            return {
                "success": result,
                "customer_id": command.customer_id,
                "permanent": command.permanent,
                "message": message
            }