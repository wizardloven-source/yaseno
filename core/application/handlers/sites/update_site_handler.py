# core/application/handlers/sites/update_site_handler.py
"""
Update Site Handler - معالج تحديث موقع موجود
"""

import logging
from uuid import UUID

from core.domain.sites.value_objects import SiteCode, SiteType
from core.domain.sites.exceptions import SiteNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import UpdateSiteCommand
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class UpdateSiteHandler(BaseHandler[UpdateSiteCommand, SiteDTO]):
    """
    معالج تحديث موقع موجود
    
    يستخدم Optimistic Locking عبر الـ version
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateSiteCommand, user_context: UserContext = None) -> SiteDTO:
        with self._uow:
            repo = self._uow.sites
            
            # جلب الموقع من قاعدة البيانات
            site = repo.get_by_id(UUID(str(command.site_id)))
            if not site:
                raise SiteNotFoundError(str(command.site_id))
            
            # التحقق من التزامن (Optimistic Locking)
            if site.version != command.version:
                raise ConcurrentModificationError(
                    "Site",
                    str(command.site_id),
                    command.version,
                    site.version
                )
            
            # تحديث البيانات
            updated_by = user_context.user_id if user_context else command.updated_by
            
            site.update(
                name=command.name,
                site_type=command.site_type,
                street=command.street,
                city=command.city,
                country=command.country,
                phone=command.phone,
                mobile=command.mobile,
                email=command.email,
                contact_person=command.contact_person,
                notes=command.notes,
                is_active=command.is_active,
                updated_by=updated_by
            )
            
            # حفظ التغييرات
            repo.save(site)
            self._commit()
            
            logger.info(f"Site updated: {site.code.value} - {site.name} (version {site.version}) by {updated_by}")
            
            return site_to_dto(site)