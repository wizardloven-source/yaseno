# core/application/handlers/payments/create_payment_handler.py
"""
Create Payment Handler - معالج إنشاء دفعة جديدة
"""

import logging
from decimal import Decimal
from uuid import uuid4
from core.domain.accounting.posting_engine import PostingEngine  # ✅ إضافة

from core.domain.payments.entities import Payment, PaymentLine
from core.domain.payments.value_objects import (
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    PaymentReference,
    Money
)
from core.domain.payments.exceptions import (
    DuplicatePaymentCodeError,
    PaymentAmountError
)
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import CreatePaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class CreatePaymentHandler(BasePaymentHandler[CreatePaymentCommand, PaymentDTO]):
    """
    معالج إنشاء دفعة جديدة
    
    مسؤولياته:
        1. التحقق من صحة البيانات
        2. إنشاء كيان الدفعة
        3. الحفظ عبر Repository
        4. إرجاع DTO للدفعة الجديدة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreatePaymentCommand, user_context: UserContext = None) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            # التحقق من صحة المبلغ
            if command.amount <= 0:
                raise PaymentAmountError("المبلغ يجب أن يكون أكبر من صفر")
            
            # تحويل نوع الدفع
            payment_type_map = {
                "receive": PaymentType.RECEIVE,
                "pay": PaymentType.PAY,
                "transfer": PaymentType.TRANSFER,
            }
            payment_type = payment_type_map.get(command.payment_type, PaymentType.RECEIVE)
            
            # تحويل طريقة الدفع
            payment_method_map = {
                "cash": PaymentMethod.CASH,
                "check": PaymentMethod.CHECK,
                "transfer": PaymentMethod.TRANSFER,
                "credit": PaymentMethod.CREDIT,
                "card": PaymentMethod.CARD,
            }
            payment_method = payment_method_map.get(command.payment_method, PaymentMethod.CASH)
            
            # تحديد من قام بالإنشاء
            created_by = user_context.user_id if user_context else command.created_by
            
            # إنشاء الدفعة
            payment = Payment.create(
                payment_type=payment_type,
                amount=Money(command.amount, command.currency),
                payment_method=payment_method,
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                supplier_id=command.supplier_id,
                supplier_name=command.supplier_name,
                fund_id=command.fund_id,
                reference=PaymentReference(command.reference_type, command.reference_id) if command.reference_type and command.reference_id else None,
                notes=command.notes,
                created_by=created_by
            )
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Payment created: {payment.code} - {payment.payment_type.value} by {created_by}")
            
            return payment_to_dto(payment)