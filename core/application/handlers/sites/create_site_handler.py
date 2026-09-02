# core/application/handlers/sites/create_site_handler.py
"""
Create Site Handler - معالج إنشاء موقع جديد
"""

import logging
from uuid import uuid4

from core.domain.sites.entities import Site
from core.domain.sites.value_objects import SiteCode, SiteType
from core.domain.sites.exceptions import DuplicateSiteCodeError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import CreateSiteCommand
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class CreateSiteHandler(BaseHandler[CreateSiteCommand, SiteDTO]):
    """
    معالج إنشاء موقع جديد
    
    مسؤولياته:
        1. التحقق من عدم وجود كود مكرر
        2. إنشاء كيان الموقع
        3. الحفظ عبر Repository
        4. إرجاع DTO للموقع الجديد
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateSiteCommand, user_context: UserContext = None) -> SiteDTO:
        with self._uow:
            repo = self._uow.sites
            
            # التحقق من عدم وجود كود مكرر
            existing = repo.get_by_code(SiteCode(command.code))
            if existing:
                raise DuplicateSiteCodeError(command.code)
            
            # تحديد من قام بالإنشاء
            created_by = user_context.user_id if user_context else command.created_by
            
            # إنشاء الموقع الجديد
            site = Site.create(
                code=command.code,
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
                is_default=command.is_default,
                created_by=created_by
            )
            
            # حفظ في قاعدة البيانات
            repo.save(site)
            self._commit()
            
            logger.info(f"Site created: {site.code.value} - {site.name} by {created_by}")
            
            return site_to_dto(site)