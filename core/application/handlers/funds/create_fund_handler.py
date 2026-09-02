# core/application/handlers/funds/create_fund_handler.py
"""
Create Fund Handler - معالج إنشاء صندوق جديد
"""

import logging
from decimal import Decimal
from uuid import uuid4

from core.domain.funds.entities import Fund
from core.domain.funds.value_objects import FundCode, FundType, FundStatus
from core.domain.funds.exceptions import DuplicateFundCodeError, InvalidFundTypeError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.exceptions import InvalidAccountError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import CreateFundCommand
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class CreateFundHandler(BaseHandler[CreateFundCommand, FundDTO]):
    """
    معالج إنشاء صندوق جديد
    
    مسؤولياته:
        1. التحقق من صحة نوع الصندوق
        2. التحقق من عدم وجود كود مكرر
        3. التحقق من صحة الحساب المرتبط (نوعه Asset)
        4. إنشاء كيان الصندوق
        5. الحفظ عبر Repository
        6. إرجاع DTO للصندوق الجديد
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateFundCommand, user_context: UserContext = None) -> FundDTO:
        with self._uow:
            repo = self._uow.funds
            
            # 1. التحقق من صحة نوع الصندوق
            try:
                fund_type = FundType(command.fund_type)
            except ValueError:
                raise InvalidFundTypeError(command.fund_type)
            
            # 2. التحقق من عدم وجود كود مكرر
            existing = repo.get_by_code(FundCode(command.code))
            if existing:
                raise DuplicateFundCodeError(command.code)
            
            # 3. التحقق من صحة الحساب المرتبط
            account = self._uow.accounts.get_by_code(command.account_code)
            if not account:
                raise InvalidAccountError(command.account_code, "الحساب غير موجود")
            
            if account.account_type != 'asset':
                raise InvalidAccountError(
                    command.account_code,
                    f"الحساب المرتبط يجب أن يكون من نوع 'asset'، النوع الحالي: {account.account_type}"
                )
            
            # 4. تحديد من قام بالإنشاء
            created_by = user_context.user_id if user_context else command.created_by
            
            # 5. إنشاء الصندوق الجديد
            from core.domain.shared.value_objects import Money
            fund = Fund.create(
                code=command.code,
                name=command.name,
                account_code=command.account_code,
                fund_type=fund_type,
                currency=command.currency,
                created_by=created_by,
                daily_limit=command.daily_limit,
                monthly_limit=command.monthly_limit,
                min_balance_alert=command.min_balance_alert,
                max_balance_alert=command.max_balance_alert,
                opening_balance=(
                    Money(command.opening_balance, command.currency)
                    if command.opening_balance else None
                )
            )
            
            # 6. حفظ في قاعدة البيانات
            repo.save(fund)
            self._commit()
            
            logger.info(f"Fund created: {fund.code.value} - {fund.name} by {created_by}")
            
            return fund_to_dto(fund)