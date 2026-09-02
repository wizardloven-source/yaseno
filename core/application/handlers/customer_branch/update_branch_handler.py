# core/application/handlers/customer_branch/update_branch_handler.py
"""
Update Branch Handler - معالج تحديث فرع عميل
"""

import logging
from typing import Optional

from core.domain.customer_branch.entities import CustomerBranch
from core.domain.customer_branch.value_objects import (
    BranchId, BranchCode, BranchStatus, BranchAddress, BranchContact, BranchGeoLocation
)
from core.domain.customer_branch.interfaces import ICustomerBranchRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.customer_branch.base_handler import BaseBranchHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customer_branch.commands import UpdateBranchCommand
from core.application.customer_branch.dtos import CustomerBranchDTO
from core.application.customer_branch.converters import branch_to_dto

logger = logging.getLogger(__name__)


class UpdateBranchHandler(BaseBranchHandler[UpdateBranchCommand, CustomerBranchDTO]):
    """
    معالج تحديث فرع عميل موجود
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._branch_repo: Optional[ICustomerBranchRepository] = None
    
    def _get_repo(self) -> ICustomerBranchRepository:
        if self._branch_repo is None:
            self._branch_repo = self._uow.customer_branches
        return self._branch_repo
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateBranchCommand, user_context: UserContext) -> CustomerBranchDTO:
        """
        تنفيذ تحديث فرع عميل
        """
        logger.info(f"Updating branch: {command.branch_id}")
        
        with self._uow:
            repo = self._get_repo()
            
            # 1. جلب الفرع
            branch = repo.get_by_id(BranchId.from_string(command.branch_id))
            if not branch:
                raise ValueError(f"Branch not found: {command.branch_id}")
            
            # 2. التحقق من الإصدار (Optimistic Locking)
            if branch.version != command.version:
                raise ConcurrentModificationError(
                    "CustomerBranch",
                    command.branch_id,
                    command.version,
                    branch.version
                )
            
            # 3. تحويل status إلى Enum
            status = None
            if command.status:
                status = BranchStatus(command.status)
            
            # 4. تحديث العنوان إذا تغير
            address = None
            if any([command.street, command.city, command.country, command.postal_code]):
                address = BranchAddress(
                    street=command.street or branch.address.street,
                    city=command.city or branch.address.city,
                    country=command.country or branch.address.country,
                    postal_code=command.postal_code or branch.address.postal_code
                )
            
            # 5. تحديث معلومات الاتصال إذا تغيرت
            contact = None
            if any([command.email, command.phone, command.mobile, command.contact_person]):
                contact = BranchContact(
                    email=command.email or branch.contact.email,
                    phone=command.phone or branch.contact.phone,
                    mobile=command.mobile or branch.contact.mobile,
                    contact_person=command.contact_person or branch.contact.contact_person
                )
            
            # 6. تحديث الموقع الجغرافي إذا تغير
            geo_location = None
            if command.latitude is not None or command.longitude is not None:
                geo_location = BranchGeoLocation(
                    latitude=command.latitude or branch.geo_location.latitude,
                    longitude=command.longitude or branch.geo_location.longitude
                )
            
            # 7. تحديث الفرع
            branch.update(
                name=command.name,
                address=address,
                contact=contact,
                geo_location=geo_location,
                tax_number=command.tax_number,
                is_default=command.is_default,
                notes=command.notes,
                working_hours=command.working_hours,
                branch_type=command.branch_type,
                status=status,
                updated_by=user_context.user_id
            )
            
            # 8. إذا تم تعيين الفرع كافتراضي
            if command.is_default:
                # إلغاء تعيين الفروع الافتراضية الأخرى للعميل
                default_branch = repo.get_default_branch(branch.customer_id)
                if default_branch and default_branch.id != branch.id:
                    default_branch.unset_default(user_context.user_id)
                    repo.save(default_branch)
            
            # 9. حفظ التغييرات
            repo.save(branch)
            self._commit()
            
            logger.info(f"Branch updated: {branch.code} - {branch.name} (version {branch.version})")
            
            return branch_to_dto(branch)