"""Update Supplier Handler - تحديث مورد موجود"""

import logging

from core.domain.suppliers.value_objects import SupplierId, ContactInfo, Address
from core.domain.suppliers.exceptions import SupplierNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.suppliers.commands import UpdateSupplierCommand
from core.application.suppliers.dtos import SupplierDTO
from core.application.suppliers.converters import supplier_to_dto

logger = logging.getLogger(__name__)


class UpdateSupplierHandler(BaseHandler[UpdateSupplierCommand, SupplierDTO]):
    """Handler for updating an existing supplier with Optimistic Locking"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateSupplierCommand, user_context: UserContext) -> SupplierDTO:
        with self._uow:
            repo = self._uow.suppliers
            
            # الحصول على المورد
            supplier_id = SupplierId.from_string(command.supplier_id)
            supplier = repo.get_by_id(supplier_id)
            if not supplier:
                raise SupplierNotFoundError(command.supplier_id)
            
            # ✅ التحقق من التزامن (Optimistic Locking) - استخدام الاستثناء الموحد
            if supplier.version != command.version:
                raise ConcurrentModificationError(
                    "Supplier",
                    str(supplier_id),
                    command.version,
                    supplier.version
                )
            
            # تحديث معلومات الاتصال
            contact_info = None
            if any([command.email, command.phone, command.mobile]):
                contact_info = ContactInfo(
                    email=command.email or supplier.contact_info.email,
                    phone=command.phone or supplier.contact_info.phone,
                    mobile=command.mobile or supplier.contact_info.mobile
                )
            
            # تحديث العنوان
            address = None
            if any([command.street, command.city, command.country]):
                address = Address(
                    street=command.street or supplier.address.street,
                    city=command.city or supplier.address.city,
                    country=command.country or supplier.address.country
                )
            
            # تحديث المورد (لا تزيد version)
            supplier.update(
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
            repo.save(supplier)
            self._commit()
            
            logger.info(f"Supplier updated: {supplier.code} - {supplier.name} (version {supplier.version}) by {user_context.user_id}")
            
            return supplier_to_dto(supplier)