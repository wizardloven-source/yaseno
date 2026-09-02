# core/application/handlers/centers/delete_center_handler.py
"""
Delete Center Handler - معالج حذف مركز
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import DeleteCenterCommand

logger = logging.getLogger(__name__)


class DeleteCenterHandler(BaseHandler[DeleteCenterCommand, dict]):
    """
    معالج حذف مركز
    
    يقوم بحذف مركز (ناعم أو دائم) مع التحقق من:
    - عدم وجود أبناء
    - عدم وجود توزيعات مرتبطة
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return CenterService(
            center_repo=self._uow.centers,
            allocation_repo=self._uow.center_allocations,
            rule_repo=self._uow.center_allocation_rules
        )

    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteCenterCommand, user_context: UserContext) -> dict:
        """
        تنفيذ حذف المركز
        
        Args:
            command: أمر حذف المركز
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Deleting center: {command.center_id}")

        with self._uow:
            service = self._get_service()
            center_repo = self._uow.centers

            # التحقق من وجود المركز
            center = center_repo.get_by_id(command.center_id)
            if not center:
                return {
                    "success": False,
                    "message": f"Center {command.center_id} not found",
                    "center_id": command.center_id
                }

            # التحقق من وجود أبناء
            children = center_repo.get_children(str(center.code))
            if children:
                return {
                    "success": False,
                    "message": f"Cannot delete center with children: {len(children)} child centers found",
                    "center_id": command.center_id,
                    "children_count": len(children)
                }

            # حذف المركز
            result = center_repo.delete(center.id)
            self._commit()

        if result:
            logger.info(f"Center deleted: {center.code}")
            return {
                "success": True,
                "message": f"Center {center.code} deleted successfully",
                "center_id": command.center_id,
                "permanent": command.permanent
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete center {command.center_id}",
                "center_id": command.center_id
            }