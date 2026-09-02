# core/application/handlers/customers/change_customer_status_handler.py
"""Change Customer Status Handler"""

import logging

from core.domain.customers.value_objects import CustomerId, CustomerStatus
from core.domain.customers.exceptions import CustomerNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import ChangeCustomerStatusCommand

logger = logging.getLogger(__name__)


class ChangeCustomerStatusHandler(BaseHandler[ChangeCustomerStatusCommand, dict]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ChangeCustomerStatusCommand, user_context: UserContext) -> dict:
        with self._uow:
            repo = self._uow.customers

            customer_id = CustomerId.from_string(command.customer_id)
            customer = repo.get_by_id(customer_id)

            if not customer:
                raise CustomerNotFoundError(command.customer_id)

            status_map = {
                "active": CustomerStatus.ACTIVE,
                "inactive": CustomerStatus.INACTIVE,
                "suspended": CustomerStatus.SUSPENDED,
                "blocked": CustomerStatus.BLOCKED,
            }
            new_status = status_map.get(command.new_status, CustomerStatus.ACTIVE)

            customer.change_status(new_status, command.reason, user_context.user_id)
            repo.save(customer)
            self._commit()

            logger.info(f"Customer status changed: {customer.code} -> {new_status.value}")

            return {
                "success": True,
                "customer_id": command.customer_id,
                "new_status": new_status.value,
                "message": f"Customer status changed to {new_status.value}"
            }