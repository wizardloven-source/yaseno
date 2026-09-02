# core/application/handlers/sites/set_default_site_handler.py
"""
Set Default Site Handler - معالج تعيين موقع كافتراضي
"""

import logging
from uuid import UUID

from core.domain.sites.value_objects import SiteId
from core.domain.sites.exceptions import SiteNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import SetDefaultSiteCommand
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class SetDefaultSiteHandler(BaseHandler[SetDefaultSiteCommand, SiteDTO]):
    """
    معالج تعيين موقع كافتراضي
    
    يقوم بتعيين موقع محدد كموقع افتراضي للنظام،
    مع إلغاء تعيين أي موقع افتراضي آخر.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: SetDefaultSiteCommand, user_context: UserContext) -> SiteDTO:
        """
        تنفيذ تعيين الموقع كافتراضي
        
        Args:
            command: أمر تعيين الموقع الافتراضي
            user_context: سياق المستخدم
        
        Returns:
            SiteDTO: بيانات الموقع بعد التعيين
        """
        logger.info(f"Setting default site: {command.site_id}")

        with self._uow:
            site_repo = self._uow.sites
            
            # جلب الموقع
            site = site_repo.get_by_id(UUID(str(command.site_id)))
            if not site:
                raise SiteNotFoundError(str(command.site_id))
            
            # إلغاء تعيين الموقع الافتراضي الحالي
            current_default = site_repo.get_default_site()
            if current_default and current_default.id != site.id:
                current_default.is_default = False
                site_repo.save(current_default)
            
            # تعيين الموقع الجديد كافتراضي
            site.is_default = True
            site.updated_by = user_context.user_id
            site_repo.save(site)
            
            self._commit()

        logger.info(f"Default site set to: {site.code} - {site.name}")

        return site_to_dto(site)