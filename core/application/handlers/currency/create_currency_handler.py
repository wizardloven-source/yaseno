# core/application/handlers/currency/create_currency_handler.py
"""
Create Currency Handler - معالج إنشاء عملة جديدة
"""

import logging
from uuid import uuid4

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.exceptions import CurrencyCodeAlreadyExistsError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import CreateCurrencyCommand
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class CreateCurrencyHandler(BaseHandler[CreateCurrencyCommand, CurrencyDTO]):
    """
    معالج إنشاء عملة جديدة
    
    مسؤولياته:
        1. التحقق من عدم وجود كود مكرر
        2. إذا كانت العملة الجديدة هي الأساس، تعطيل أي عملة أساسية أخرى
        3. إنشاء كيان العملة
        4. الحفظ عبر Repository
        5. إرجاع DTO للعملة الجديدة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateCurrencyCommand, user_context: UserContext = None) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            # التحقق من عدم وجود كود مكرر
            existing = repo.get_by_code(CurrencyCode(command.code.upper()))
            if existing:
                raise CurrencyCodeAlreadyExistsError(command.code)
            
            # إذا كانت هذه العملة هي الأساس، تعطيل أي عملة أساسية أخرى
            if command.is_base:
                base_currency = repo.get_base_currency()
                if base_currency:
                    base_currency.is_base = False
                    repo.save(base_currency)
            
            # تحديد من قام بالإنشاء
            created_by = user_context.user_id if user_context else command.created_by
            
            # إنشاء العملة الجديدة
            currency = Currency.create(
                code=command.code,
                name=command.name,
                symbol=command.symbol,
                decimal_places=command.decimal_places,
                is_base=command.is_base,
                created_by=created_by
            )
            
            # حفظ في قاعدة البيانات
            repo.save(currency)
            self._commit()
            
            logger.info(f"Currency created: {currency.code.value} - {currency.name} by {created_by}")
            
            return currency_to_dto(currency)