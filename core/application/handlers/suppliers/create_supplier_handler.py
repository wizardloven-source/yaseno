# C:\Users\MTC\Desktop\erpya\core\application\handlers\suppliers\create_supplier_handler.py
"""Create Supplier Handler - إنشاء مورد جديد"""

import logging
from decimal import Decimal

from core.domain.suppliers.entities import Supplier
from core.domain.suppliers.value_objects import (
    SupplierCode, ContactInfo, Address
)
from core.domain.suppliers.exceptions import DuplicateSupplierCodeError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.suppliers.commands import CreateSupplierCommand
from core.application.suppliers.dtos import SupplierDTO
from core.application.suppliers.converters import supplier_to_dto

logger = logging.getLogger(__name__)


class CreateSupplierHandler(BaseHandler[CreateSupplierCommand, SupplierDTO]):
    """Handler for creating a new supplier"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateSupplierCommand, user_context: UserContext) -> SupplierDTO:
        with self._uow:
            repo = self._uow.suppliers
            
            # التحقق من عدم وجود كود مكرر
            supplier_code = SupplierCode(command.code)
            existing = repo.get_by_code(supplier_code)
            if existing:
                raise DuplicateSupplierCodeError(command.code)
            
            # إنشاء معلومات الاتصال
            contact_info = ContactInfo(
                email=command.email,
                phone=command.phone,
                mobile=command.mobile
            )
            
            # إنشاء العنوان
            address = Address(
                street=command.street,
                city=command.city,
                country=command.country
            )
            
            # إنشاء المورد
            supplier = Supplier.create(
                code=supplier_code,
                name=command.name,
                contact_info=contact_info,
                address=address,
                tax_number=command.tax_number,
                credit_limit=command.credit_limit,
                currency=command.currency,
                notes=command.notes,
                created_by=user_context.user_id
            )
            
            repo.save(supplier)
            self._commit()
            
            logger.info(f"Supplier created: {supplier.code} - {supplier.name} by {user_context.user_id}")
            
            return supplier_to_dto(supplier)