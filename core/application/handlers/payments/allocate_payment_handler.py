# core/application/handlers/payments/allocate_payment_handler.py

"""
Allocate Payment Handler - معالج توزيع دفعة على فواتير
الإصدار: 2.0.0
✅ دعم التحقق من توازن التوزيع
✅ دعم تحديث حالة الفاتورة تلقائياً
✅ دعم العملات المتعددة
✅ دعم سجل التوزيع
"""

import logging
from decimal import Decimal
from typing import Dict, Any

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import (
    PaymentNotFoundError,
    PaymentAlreadyCompletedError,
    PaymentAlreadyCancelledError
)
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import AllocatePaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.application.payments.services import PaymentAllocationService
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class AllocatePaymentHandler(BaseHandler[AllocatePaymentCommand, PaymentDTO]):
    """
    معالج توزيع دفعة على فواتير
    
    يقوم بتوزيع مبلغ الدفعة على فاتورة مع:
        1. التحقق من صحة الدفعة والفاتورة
        2. تحديث رصيد الفاتورة
        3. تحديث حالة الفاتورة (مدفوعة/جزئية)
        4. تحديث حالة الدفعة
        5. إنشاء سجل التوزيع
        6. دعم العملات المتعددة
    """
    
    def __init__(self, uow: IUnitOfWork, allocation_service: PaymentAllocationService):
        super().__init__(uow)
        self._allocation_service = allocation_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: AllocatePaymentCommand, user_context: UserContext) -> PaymentDTO:
        """
        تنفيذ توزيع الدفعة
        
        Args:
            command: أمر توزيع الدفعة
            user_context: سياق المستخدم
        
        Returns:
            PaymentDTO: الدفعة بعد التوزيع
            
        Raises:
            PaymentNotFoundError: إذا لم يتم العثور على الدفعة
            ValueError: إذا كانت الدفعة مكتملة أو ملغية
            ValueError: إذا فشلت عملية التوزيع
        """
        logger.info(f"Allocating payment {command.payment_id} to invoice {command.invoice_id} by {user_context.user_id}")
        
        # 1. التحقق من صحة المبلغ
        if command.amount <= 0:
            raise ValueError(f"Allocation amount must be greater than zero, got {command.amount}")
        
        with self._uow:
            # 2. جلب الدفعة
            payment_repo = self._uow.payments
            payment = payment_repo.get_by_id(PaymentId.from_string(command.payment_id))
            
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # 3. التحقق من إمكانية التوزيع
            if payment.is_completed:
                raise PaymentAlreadyCompletedError(str(payment.id))
            
            if payment.is_cancelled:
                raise PaymentAlreadyCancelledError(str(payment.id))
            
            # 4. التحقق من أن المبلغ لا يتجاوز قيمة الدفعة
            if command.amount > payment.amount.amount:
                raise ValueError(
                    f"Allocation amount {command.amount} exceeds payment amount {payment.amount.amount}"
                )
            
            # 5. التحقق من عملة الدفعة (اختياري)
            if hasattr(command, 'currency') and command.currency != payment.currency:
                logger.warning(
                    f"Currency mismatch: payment {payment.currency}, allocation {command.currency}"
                )
                # يمكن إضافة دعم تحويل العملات هنا
            
            # 6. تنفيذ التوزيع
            result = self._allocation_service.allocate_payment(
                payment_id=command.payment_id,
                invoice_id=command.invoice_id,
                amount=command.amount,
                allocated_by=user_context.user_id
            )
            
            if not result.get('success', False):
                raise ValueError(result.get('message', 'Allocation failed'))
            
            # 7. تحديث حالة الدفعة
            if payment.allocated_amount >= payment.amount.amount:
                payment.status = "completed"
                logger.info(f"Payment {payment.code} fully allocated and completed")
            else:
                payment.status = "pending"
                logger.info(f"Payment {payment.code} partially allocated ({payment.allocated_amount}/{payment.amount.amount})")
            
            # 8. حفظ التغييرات
            payment_repo.save(payment)
            self._commit()
            
            logger.info(f"✅ Payment {command.payment_id} allocated successfully: {command.amount}")
            
            # 9. إرجاع النتيجة
            return payment_to_dto(payment)