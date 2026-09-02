# core/application/handlers/tax/close_tax_period_handler.py
"""
Close Tax Period Handler - معالج إغلاق فترة ضريبية
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CloseTaxPeriodHandler(BaseTaxHandler):
    """
    معالج إغلاق فترة ضريبية
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CLOSE_PERIOD)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ إغلاق فترة ضريبية
        
        Args:
            command: CloseTaxPeriodCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Closing tax period: {command.period_id}")
        
        with self._uow:
            period_repo = self._uow.tax_periods
            
            # جلب الفترة
            period = period_repo.get_by_id(command.period_id)
            if not period:
                return {
                    "success": False,
                    "message": f"Tax period '{command.period_id}' not found",
                    "period_id": command.period_id
                }
            
            closed_by = user_context.user_id if user_context else command.closed_by
            
            # إغلاق الفترة
            period.close(closed_by)
            period_repo.save(period)
            self._commit()
            
            logger.info(f"Tax period closed: {period.code} by {closed_by}")
            
            return {
                "success": True,
                "message": f"Tax period {period.code} closed successfully",
                "period_id": command.period_id
            }