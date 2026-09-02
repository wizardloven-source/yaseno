# core/application/handlers/funds/update_fund_handler.py
"""
Update Fund Handler - معالج تحديث صندوق موجود
✅ محدث: Optimistic Locking صارم
✅ محدث: التحقق من الإصدار قبل التحديث
✅ محدث: إعادة حساب الرصيد من الحركات
"""

import logging
from decimal import Decimal
from typing import Optional

from core.domain.funds.value_objects import FundCode, FundId
from core.domain.funds.exceptions import FundNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.exceptions import InvalidAccountError
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import UpdateFundCommand
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class UpdateFundHandler(BaseHandler[UpdateFundCommand, FundDTO]):
    """
    معالج تحديث صندوق موجود مع Optimistic Locking صارم
    
    المبادئ:
        1. التحقق من الإصدار قبل أي تحديث
        2. في حالة التعارض، رفع ConcurrentModificationError
        3. إعادة حساب الرصيد من الحركات للحفاظ على الدقة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateFundCommand, user_context: UserContext = None) -> FundDTO:
        with self._uow:
            repo = self._uow.funds
            
            fund_id = command.fund_id
            
            # التحقق من صحة النوع
            if not isinstance(fund_id, FundId):
                logger.error(f"Invalid fund_id type: {type(fund_id)}")
                raise ValueError(f"Invalid fund_id type: {type(fund_id)}")
            
            # 1. جلب الصندوق من قاعدة البيانات
            fund = repo.get_by_id(fund_id)
            if not fund:
                raise FundNotFoundError(str(fund_id))
            
            # 2. ✅ التحقق من الإصدار (Optimistic Locking)
            if fund.version != command.version:
                raise ConcurrentModificationError(
                    "Fund",
                    str(fund_id),
                    command.version,
                    fund.version
                )
            
            # 3. التحقق من صحة الحساب المرتبط (إذا تغير)
            if command.account_code and command.account_code != fund.account_code:
                account = self._uow.accounts.get_by_code(command.account_code)
                if not account:
                    raise InvalidAccountError(command.account_code, "الحساب غير موجود")
                
                if account.account_type != 'asset':
                    raise InvalidAccountError(
                        command.account_code,
                        f"الحساب المرتبط يجب أن يكون من نوع 'asset'، النوع الحالي: {account.account_type}"
                    )
            
            # 4. تحديد من قام بالتحديث
            updated_by = user_context.user_id if user_context else command.updated_by
            
            # 5. تحديث بيانات الصندوق
            fund.update(
                name=command.name,
                account_code=command.account_code,
                currency=command.currency,
                daily_limit=command.daily_limit,
                monthly_limit=command.monthly_limit,
                min_balance_alert=command.min_balance_alert,
                max_balance_alert=command.max_balance_alert,
                updated_by=updated_by
            )
            
            # 6. ✅ إعادة حساب الرصيد من الحركات
            try:
                movements = self._uow.fund_movements.get_by_fund_code(fund.code.value)
                
                total = Decimal('0.0')
                for movement in movements:
                    amount = Decimal(str(movement.amount)) if not isinstance(movement.amount, Decimal) else movement.amount
                    total += amount
                
                # تحديث الرصيد في كائن الصندوق
                fund._cached_balance = Money(total, fund.currency) if hasattr(fund, '_cached_balance') else None
                
                logger.info(f"✅ Recalculated balance for {fund.code.value}: {total} (from {len(movements)} movements)")
                
            except Exception as e:
                logger.error(f"❌ Failed to recalculate balance for {fund.code.value}: {e}")
            
            # 7. ✅ حفظ مع Optimistic Locking
            try:
                repo.save(fund)  # الـ Repository سيتحقق من الإصدار
                self._commit()
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected for fund {fund.code.value}")
                raise
            
            logger.info(f"✅ Fund updated: {fund.code.value} - {fund.name} (version {fund.version}) by {updated_by}")
            
            return fund_to_dto(fund)