# core/application/handlers/sites/delete_site_handler.py
"""
Delete Site Handler - معالج حذف موقع (Soft Delete)
"""

import logging
from uuid import UUID

from core.domain.sites.value_objects import SiteCode
from core.domain.sites.exceptions import SiteNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import DeleteSiteCommand

logger = logging.getLogger(__name__)


class DeleteSiteHandler(BaseHandler[DeleteSiteCommand, dict]):
    """
    معالج حذف موقع
    
    ملاحظات:
        1. الحذف هو Soft Delete (تعطيل فقط) - يتم تعيين is_active = False, is_deleted = True
        2. يمكن استخدام الحذف الدائم في المستقبل إذا لزم الأمر
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteSiteCommand, user_context: UserContext = None) -> dict:
        with self._uow:
            repo = self._uow.sites
            
            # جلب الموقع
            site = repo.get_by_id(UUID(str(command.site_id)))
            if not site:
                return {
                    "success": False,
                    "message": f"الموقع {command.site_id} غير موجود",
                    "site_id": str(command.site_id)
                }
            
            deleted_by = user_context.user_id if user_context else command.deleted_by
            
            # حذف ناعم (تعطيل فقط)
            site.soft_delete(deleted_by)
            repo.save(site)
            self._commit()
            
            logger.info(f"Site deleted: {site.code.value} - {site.name} by {deleted_by}")
            
            return {
                "success": True,
                "message": f"تم حذف الموقع {site.code.value}",
                "site_id": str(command.site_id)
            }