"""Update Customer Handler"""

import logging

from core.domain.customers.value_objects import CustomerId, ContactInfo, Address
from core.domain.customers.exceptions import CustomerNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import UpdateCustomerCommand
from core.application.customers.dtos import CustomerDTO
from core.application.customers.converters import customer_to_dto

logger = logging.getLogger(__name__)


class UpdateCustomerHandler(BaseHandler[UpdateCustomerCommand, CustomerDTO]):

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateCustomerCommand, user_context: UserContext) -> CustomerDTO:
        with self._uow:
            repo = self._uow.customers

            customer_id = CustomerId.from_string(command.customer_id)
            customer = repo.get_by_id(customer_id)

            if not customer:
                raise CustomerNotFoundError(command.customer_id)

            # ✅ التحقق من version - تأكد أن العميل لم يتغير منذ تحميله
            # هذا التحقق إضافي وليس بديلاً عن التحقق في Repository
            if customer.version != command.version:
                raise ConcurrentModificationError(
                    "Customer",
                    str(customer_id),
                    command.version,
                    customer.version
                )

            # تحديث معلومات الاتصال إذا تغير أي حقل
            if any([command.email, command.phone, command.mobile]):
                contact_info = ContactInfo(
                    email=command.email or customer.contact_info.email,
                    phone=command.phone or customer.contact_info.phone,
                    mobile=command.mobile or customer.contact_info.mobile
                )
            else:
                contact_info = None

            # تحديث العنوان إذا تغير أي حقل
            if any([command.street, command.city, command.country]):
                address = Address(
                    street=command.street or customer.address.street,
                    city=command.city or customer.address.city,
                    country=command.country or customer.address.country
                )
            else:
                address = None

            # تحديث بيانات العميل (لا تزيد version)
            customer.update(
                name=command.name,
                contact_info=contact_info,
                address=address,
                tax_number=command.tax_number,
                credit_limit=command.credit_limit,
                currency=command.currency,
                notes=command.notes,
                updated_by=user_context.user_id
            )

            # ✅ Repository سيتحقق من version مرة أخرى ويزيده
            repo.save(customer)
            self._commit()

            logger.info(f"Customer updated: {customer.code} (version {customer.version})")

            return customer_to_dto(customer)