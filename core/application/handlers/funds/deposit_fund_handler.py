# core/application/handlers/funds/deposit_fund_handler.py
"""
Deposit Fund Handler - معالج إيداع في صندوق
✅ محدث: Optimistic Locking لتحديث رصيد الصندوق
✅ محدث: التحقق من الإصدار قبل التحديث
"""

import logging
from decimal import Decimal
from core.domain.funds.value_objects import FundCode
from core.domain.funds.exceptions import FundNotFoundError, FundAlreadyInactiveError
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import DepositToFundCommand
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class DepositFundHandler(BaseHandler[DepositToFundCommand, FundDTO]):
    """
    معالج إيداع مبلغ في صندوق
    
    مسؤولياته:
        1. التحقق من وجود الصندوق
        2. التحقق من أن الصندوق نشط
        3. إجراء الإيداع (زيادة الرصيد) مع Optimistic Locking
        4. تسجيل الحركة
        5. إنشاء قيد محاسبي (اختياري)
    """
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine = None):
        super().__init__(uow)
        self._posting_engine = posting_engine
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: DepositToFundCommand, user_context: UserContext = None) -> FundDTO:
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
                raise ValueError("مبلغ الإيداع يجب أن يكون أكبر من صفر")
            
            # 4. تحديد من قام بالإيداع
            created_by = user_context.user_id if user_context else command.created_by
            
            # 5. إجراء الإيداع
            movement = fund.deposit(
                amount=Money(amount=command.amount, currency=fund.currency),
                reason=command.reason,
                created_by=created_by,
                reference_id=command.reference_id
            )
            
            # 6. ✅ حفظ التغييرات مع Optimistic Locking
            try:
                repo.save(fund)  # الـ Repository سيتحقق من الإصدار
                self._commit()
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected for fund {fund.code.value}")
                raise
            
            logger.info(
                f"Deposit to fund {fund.code.value}: {command.amount} {fund.currency} "
                f"by {created_by} - Reason: {command.reason}"
            )
            
            return fund_to_dto(fund)