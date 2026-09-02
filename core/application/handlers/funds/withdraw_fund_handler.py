# core/application/handlers/funds/withdraw_fund_handler.py
"""
Withdraw Fund Handler - معالج سحب من صندوق
✅ محدث: Optimistic Locking لتحديث رصيد الصندوق
✅ محدث: التحقق من الإصدار قبل التحديث
"""

import logging
from decimal import Decimal

from core.domain.funds.value_objects import FundCode
from core.domain.funds.exceptions import (
    FundNotFoundError, 
    FundAlreadyInactiveError, 
    InsufficientFundsError
)
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import WithdrawFromFundCommand
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class WithdrawFundHandler(BaseHandler[WithdrawFromFundCommand, FundDTO]):
    """
    معالج سحب مبلغ من صندوق
    
    مسؤولياته:
        1. التحقق من وجود الصندوق
        2. التحقق من أن الصندوق نشط
        3. التحقق من كفاية الرصيد
        4. إجراء السحب (نقصان الرصيد) مع Optimistic Locking
        5. تسجيل الحركة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: WithdrawFromFundCommand, user_context: UserContext = None) -> FundDTO:
        with self._uow:
            repo = self._uow.funds
            
            # 1. جلب الصندوق
            fund = repo.get_by_id(command.fund_id)
            if not fund:
                raise FundNotFoundError(str(command.fund_id))
            
            # 2. التحقق من أن الصندوق نشط
            if not fund.is_active:
                raise FundAlreadyInactiveError(fund.code.value)
            
            # 3. التحقق من صحة المبلغ
            if command.amount <= 0:
                raise ValueError("مبلغ السحب يجب أن يكون أكبر من صفر")
            
            # 4. ✅ التحقق من كفاية الرصيد (باستخدام الرصيد المحسوب)
            current_balance = fund.current_balance.amount
            if current_balance < Decimal(str(command.amount)):
                raise InsufficientFundsError(
                    fund.code.value,
                    float(current_balance),
                    float(command.amount)
                )
            
            # 5. تحديد من قام بالسحب
            created_by = user_context.user_id if user_context else command.created_by
            
            # 6. إجراء السحب
            movement = fund.withdraw(
                amount=Money(amount=command.amount, currency=fund.currency),
                reason=command.reason,
                created_by=created_by,
                reference_id=command.reference_id
            )
            
            # 7. ✅ حفظ التغييرات مع Optimistic Locking
            try:
                repo.save(fund)  # الـ Repository سيتحقق من الإصدار
                self._commit()
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected for fund {fund.code.value}")
                raise
            
            logger.info(
                f"Withdraw from fund {fund.code.value}: {command.amount} {fund.currency} "
                f"by {created_by} - Reason: {command.reason}"
            )
            
            return fund_to_dto(fund)