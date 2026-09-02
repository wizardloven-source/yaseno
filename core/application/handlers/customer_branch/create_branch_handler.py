# core/application/handlers/customer_branch/create_branch_handler.py
"""
Create Branch Handler - معالج إنشاء فرع عميل جديد
"""

import logging
from typing import Optional

from core.domain.customer_branch.entities import CustomerBranch
from core.domain.customer_branch.value_objects import (
    BranchId, BranchCode, BranchAddress, BranchContact, BranchGeoLocation
)
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.customer_branch.base_handler import BaseBranchHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.commands import CreateBranchCommand
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class CreateBranchHandler(BaseBranchHandler[CreateBranchCommand, CustomerBranchDTO]):
    """
    معالج إنشاء فرع عميل جديد
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._branch_repo: Optional[ICustomerBranchRepository] = None
    
    def _get_repo(self) -> ICustomerBranchRepository:
        if self._branch_repo is None:
            self._branch_repo = self._uow.customer_branches
        return self._branch_repo
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateBranchCommand, user_context: UserContext) -> CustomerBranchDTO:
        """
        تنفيذ إنشاء فرع عميل جديد
        """
        logger.info(f"Creating branch: {command.code} - {command.name} for customer {command.customer_id}")
        
        with self._uow:
            repo = self._get_repo()
            
            # 1. التحقق من عدم وجود كود مكرر
            if repo.exists_by_code(BranchCode(command.code)):
                raise ValueError(f"Branch code already exists: {command.code}")
            
            # 2. إنشاء الفرع
            branch = CustomerBranch.create(
                code=command.code,
                name=command.name,
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                customer_code=command.customer_code,
                address=BranchAddress(
                    street=command.street,
                    city=command.city,
                    country=command.country,
                    postal_code=command.postal_code
                ),
                contact=BranchContact(
                    email=command.email,
                    phone=command.phone,
                    mobile=command.mobile,
                    contact_person=command.contact_person
                ),
                geo_location=BranchGeoLocation(
                    latitude=command.latitude,
                    longitude=command.longitude
                ),
                tax_number=command.tax_number,
                is_default=command.is_default,
                notes=command.notes,
                working_hours=command.working_hours,
                branch_type=command.branch_type,
                created_by=user_context.user_id
            )
            
            # 3. إذا كان هذا الفرع افتراضي، إلغاء تعيين الفروع الافتراضية الأخرى
            if command.is_default:
                default_branch = repo.get_default_branch(command.customer_id)
                if default_branch and default_branch.id != branch.id:
                    default_branch.unset_default(user_context.user_id)
                    repo.save(default_branch)
            
            # 4. حفظ الفرع
            repo.save(branch)
            self._commit()
            
            logger.info(f"Branch created: {branch.code} - {branch.name} (ID: {branch.id})")
            
            return branch_to_dto(branch)