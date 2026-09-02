# core/application/handlers/payments/reverse_allocation_handler.py

"""
Reverse Allocation Handler - معالج إلغاء توزيع دفعة
الإصدار: 2.0.0
✅ دعم إنشاء قيد عكسي
✅ دعم استعادة رصيد الفاتورة
✅ دعم تحديث حالة الفاتورة
✅ دعم سجل الإلغاء
"""

import logging
from typing import Dict, Any

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode, Money

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import ReverseAllocationCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.application.payments.services import PaymentAllocationService

logger = logging.getLogger(__name__)


class ReverseAllocationHandler(BaseHandler[ReverseAllocationCommand, PaymentDTO]):
    """
    معالج إلغاء توزيع دفعة
    
    يقوم بإلغاء توزيع دفعة على فاتورة مع:
        1. استعادة رصيد الفاتورة
        2. تحديث حالة الفاتورة
        3. إنشاء قيد عكسي في المحاسبة
        4. تحديث حالة الدفعة
        5. تسجيل سبب الإلغاء
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        allocation_service: PaymentAllocationService,
        posting_engine: PostingEngine
    ):
        super().__init__(uow)
        self._allocation_service = allocation_service
        self._posting_engine = posting_engine
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ReverseAllocationCommand, user_context: UserContext) -> PaymentDTO:
        """
        تنفيذ إلغاء توزيع الدفعة
        
        Args:
            command: أمر إلغاء التوزيع
            user_context: سياق المستخدم
        
        Returns:
            PaymentDTO: الدفعة بعد إلغاء التوزيع
        """
        logger.info(f"Reversing allocation {command.allocation_id} by {user_context.user_id}")
        
        with self._uow:
            # 1. جلب الدفعة
            payment_repo = self._uow.payments
            payment = payment_repo.get_by_id(PaymentId.from_string(command.payment_id))
            
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # 2. التحقق من إمكانية الإلغاء
            if payment.is_completed:
                raise ValueError("Cannot reverse allocation on completed payment")
            
            if payment.is_cancelled:
                raise ValueError("Cannot reverse allocation on cancelled payment")
            
            # 3. التحقق من وجود التوزيع
            allocation = self._allocation_service.get_allocation(command.allocation_id)
            if not allocation:
                raise ValueError(f"Allocation {command.allocation_id} not found")
            
            # 4. تنفيذ إلغاء التوزيع
            result = self._allocation_service.reverse_allocation(
                allocation_id=command.allocation_id,
                reversed_by=user_context.user_id,
                reason=command.reason
            )
            
            if not result.get('success', False):
                raise ValueError(result.get('message', 'Reversal failed'))
            
            # 5. إنشاء قيد عكسي إذا كان مطلوباً
            if command.create_reversal_entry:
                self._create_reversal_entry(payment, allocation, user_context)
            
            # 6. تحديث حالة الدفعة
            if payment.allocated_amount <= 0:
                payment.status = "draft"
                logger.info(f"Payment {payment.code} allocation fully reversed")
            else:
                payment.status = "pending"
                logger.info(f"Payment {payment.code} partially reversed")
            
            # 7. حفظ التغييرات
            payment_repo.save(payment)
            self._commit()
            
            logger.info(f"✅ Allocation {command.allocation_id} reversed successfully")
            
            return payment_to_dto(payment)
    
    def _create_reversal_entry(
        self,
        payment,
        allocation: Dict[str, Any],
        user_context: UserContext
    ) -> str:
        """
        إنشاء قيد عكسي لإلغاء التوزيع
        
        Args:
            payment: كائن الدفعة
            allocation: بيانات التوزيع
            user_context: سياق المستخدم
        
        Returns:
            str: معرف القيد المحاسبي
        """
        logger.info(f"Creating reversal journal entry for allocation {allocation.get('id')}")
        
        # بناء أسطر القيد العكسي
        lines = []
        
        # حساب العكسي: عكس القيد الأصلي
        for line_data in allocation.get('journal_lines', []):
            lines.append(JournalLine(
                account_code=AccountCode(line_data['account_code']),
                debit=Money(line_data['credit'], line_data['currency']),
                credit=Money(line_data['debit'], line_data['currency'])
            ))
        
        # إنشاء القيد
        entry = JournalEntry(
            date=self._uow.clock.now(),
            description=f"Reversal of allocation {allocation.get('id')} - {user_context.user_id}",
            lines=lines
        )
        
        # ترحيل القيد
        result = self._posting_engine.post(entry, user_context.user_id)
        
        if not result.success:
            raise ValueError(f"Failed to create reversal entry: {result.message}")
        
        logger.info(f"✅ Reversal journal entry created: {entry.id}")
        return str(entry.id)