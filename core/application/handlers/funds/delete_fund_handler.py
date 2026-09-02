# core/application/handlers/funds/delete_fund_handler.py
"""
Delete Fund Handler - معالج حذف صندوق (Soft Delete)
"""

import logging

from core.domain.funds.value_objects import FundId
from core.domain.funds.exceptions import FundNotFoundError, CannotDeleteFundWithMovementsError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import DeleteFundCommand

logger = logging.getLogger(__name__)


class DeleteFundHandler(BaseHandler[DeleteFundCommand, dict]):
    """
    معالج حذف صندوق
    
    ملاحظات:
        1. الحذف هو Soft Delete (تعطيل فقط) - يتم تعيين status = INACTIVE
        2. لا يمكن حذف صندوق له حركات (movements)
        3. الحذف الدائم (permanent=True) يستخدم بحذر شديد
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteFundCommand, user_context: UserContext = None) -> dict:
        with self._uow:
            repo = self._uow.funds
            
            # 1. جلب الصندوق من قاعدة البيانات
            fund = repo.get_by_id(command.fund_id)
            if not fund:
                return {
                    "success": False,
                    "message": f"الصندوق {command.fund_id} غير موجود",
                    "fund_id": str(command.fund_id)
                }
            
            deleted_by = user_context.user_id if user_context else command.deleted_by
            
            # 2. الحذف الدائم (استخدام بحذر)
            if command.permanent:
                # التحقق من عدم وجود حركات
                if fund.movements:
                    raise CannotDeleteFundWithMovementsError(fund.code.value, len(fund.movements))
                
                result = repo.delete(fund.id, permanent=True)
                message = f"تم حذف الصندوق {fund.code.value} بشكل دائم"
                logger.warning(f"Fund permanently deleted: {fund.code.value} by {deleted_by}")
            else:
                # 3. الحذف الناعم (تعطيل فقط)
                fund.soft_delete(deleted_by, command.reason)
                repo.save(fund)
                result = True
                message = f"تم تعطيل الصندوق {fund.code.value}"
                logger.info(f"Fund soft deleted: {fund.code.value} by {deleted_by}")
            
            self._commit()
            
            return {
                "success": result,
                "message": message,
                "fund_id": str(command.fund_id),
                "permanent": command.permanent
            }