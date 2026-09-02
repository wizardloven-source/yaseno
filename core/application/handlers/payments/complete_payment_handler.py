# core/application/handlers/payments/complete_payment_handler.py
"""
Complete Payment Handler - معالج إكمال دفعة
✅ محدث: استخدام Accounting Orchestrator المركزي
✅ محدث: دعم إنشاء القيد المحاسبي للدفعات (قبض ودفع)
✅ محدث: دعم العملات المتعددة
✅ محدث: Optimistic Locking للصندوق
✅ محدث: معالجة الأخطاء الموحدة
"""

import logging
from decimal import Decimal
from datetime import datetime, timezone

from core.domain.payments.value_objects import PaymentId, PaymentType, PaymentMethod
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.domain.shared.value_objects import Money, AccountCode
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد Accounting Orchestrator
from core.application.accounting.orchestrator import (
    AccountingOrchestrator,
    JournalEntryRequest,
    JournalEntryResult
)

# ✅ استيراد خدمات الصندوق
from core.infrastructure.db.models.fund_model import FundModel, FundMovementModel
from sqlalchemy import select, update
from uuid import UUID, uuid4

from .base_handler import BasePaymentHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import CompletePaymentCommand
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class CompletePaymentHandler(BasePaymentHandler[CompletePaymentCommand, PaymentDTO]):
    """
    معالج إكمال دفعة - النسخة النهائية المتكاملة
    
    مسؤولياته:
        1. التحقق من وجود الدفعة
        2. التحقق من إمكانية الإكمال
        3. إكمال الدفعة
        4. ✅ إنشاء قيد محاسبي عبر Accounting Orchestrator
        5. ✅ تحديث رصيد الصندوق مع Optimistic Locking
        6. معالجة الأخطاء الموحدة
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        accounting_orchestrator: AccountingOrchestrator,
        posting_engine: PostingEngine = None,
        payment_allocation_service=None
    ):
        super().__init__(uow)
        self._orchestrator = accounting_orchestrator
        self._posting_engine = posting_engine
        self._payment_allocation_service = payment_allocation_service
    
    # =========================================================================
    # ✅ بناء طلب القيد المحاسبي لـ Accounting Orchestrator
    # =========================================================================
    
    def _build_journal_entry_request(self, payment) -> JournalEntryRequest:
        """
        بناء طلب قيد محاسبي من الدفعة
        
        ✅ يدعم نوعين من الدفعات:
            - قبض (Receive): زيادة الصندوق، نقص المدينين
            - دفع (Pay): نقص الصندوق، نقص الدائنون
        ✅ يدعم العملات المتعددة
        ✅ يدعم طرق الدفع المختلفة
        """
        lines = []
        
        # الحصول على إعدادات الحسابات
        cash_account = AccountCode("1010")      # حساب الصندوق
        receivables_account = AccountCode("1020")  # حساب المدينين
        payables_account = AccountCode("2010")   # حساب الدائنون
        
        amount = payment.amount.amount
        currency = payment.currency
        
        if payment.payment_type == PaymentType.RECEIVE:
            # ========== قبض: زيادة الصندوق، نقص المدينين ==========
            
            # 1. سطر المدين: الصندوق
            lines.append({
                "account_code": cash_account.code,
                "debit": float(amount),
                "currency": currency
            })
            
            # 2. سطر الدائن: المدينون (العميل)
            lines.append({
                "account_code": receivables_account.code,
                "credit": float(amount),
                "currency": currency
            })
            
            description = f"قبض من {payment.customer_name or 'عميل'} - {payment.code}"
            
        elif payment.payment_type == PaymentType.PAY:
            # ========== دفع: نقص الصندوق، نقص الدائنون ==========
            
            # 1. سطر المدين: الدائنون (المورد)
            lines.append({
                "account_code": payables_account.code,
                "debit": float(amount),
                "currency": currency
            })
            
            # 2. سطر الدائن: الصندوق
            lines.append({
                "account_code": cash_account.code,
                "credit": float(amount),
                "currency": currency
            })
            
            description = f"دفع إلى {payment.supplier_name or 'مورد'} - {payment.code}"
            
        else:
            # تحويل بين الصناديق - يتم التعامل معه في TransferFundsHandler
            raise ValueError(f"Unsupported payment type for journal entry: {payment.payment_type}")
        
        # بناء الطلب
        return JournalEntryRequest(
            entity_type="payment",
            entity_id=str(payment.id),
            description=description,
            lines=lines,
            date=payment.date,
            transaction_type=payment.payment_type.value,
            created_by=payment.created_by,
            reference_number=payment.code.value if hasattr(payment.code, 'value') else str(payment.code),
            metadata={
                "payment_code": str(payment.code),
                "payment_type": payment.payment_type.value,
                "payment_method": payment.payment_method.value,
                "customer_id": payment.customer_id,
                "customer_name": payment.customer_name,
                "supplier_id": payment.supplier_id,
                "supplier_name": payment.supplier_name,
                "fund_id": payment.fund_id,
                "fund_code": payment.fund_code,
                "currency": payment.currency,
                "amount": float(amount),
                "lines_count": len(payment.lines) if payment.lines else 0,
                "reference_type": payment.reference.reference_type if payment.reference else None,
                "reference_id": payment.reference.reference_id if payment.reference else None,
            }
        )
    
    # =========================================================================
    # ✅ تحديث رصيد الصندوق مع Optimistic Locking
    # =========================================================================
    
    def _update_fund_balance(self, payment) -> bool:
        """
        تحديث رصيد الصندوق مع Optimistic Locking
        
        ✅ يدعم الإيداع والسحب حسب نوع الدفعة
        ✅ يستخدم Optimistic Locking لمنع التعديل المتزامن
        """
        try:
            if not payment.fund_id:
                logger.warning(f"No fund for payment {payment.code}")
                return True
            
            # جلب الصندوق
            fund = self._uow.session.execute(
                select(FundModel)
                .where(FundModel.id == UUID(payment.fund_id))
                .where(FundModel.status == 'active')
            ).scalar_one_or_none()
            
            if not fund:
                logger.error(f"Fund {payment.fund_id} not found or inactive")
                return False
            
            # حساب التغيير في الرصيد
            amount = float(payment.amount.amount)
            
            if payment.payment_type == PaymentType.RECEIVE:
                # قبض: زيادة الرصيد
                old_balance = float(fund.balance or 0)
                new_balance = old_balance + amount
                movement_type = "deposit"
                reason = f"قبض من {payment.customer_name or 'عميل'} - {payment.code}"
            elif payment.payment_type == PaymentType.PAY:
                # دفع: نقص الرصيد
                old_balance = float(fund.balance or 0)
                if old_balance < amount:
                    logger.warning(f"Insufficient fund balance: {old_balance} < {amount}")
                    return False
                new_balance = old_balance - amount
                movement_type = "withdraw"
                reason = f"دفع إلى {payment.supplier_name or 'مورد'} - {payment.code}"
            else:
                return True
            
            # تحديث مع Optimistic Locking
            new_version = fund.version + 1
            result = self._uow.session.execute(
                update(FundModel)
                .where(
                    FundModel.id == fund.id,
                    FundModel.version == fund.version
                )
                .values(
                    balance=new_balance,
                    updated_at=datetime.now(timezone.utc),
                    version=new_version
                )
            )
            
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    entity_type="Fund",
                    entity_id=str(fund.id),
                    expected_version=fund.version,
                    actual_version=fund.version
                )
            
            fund.version = new_version
            fund.balance = new_balance
            
            # إنشاء حركة الصندوق
            movement = FundMovementModel(
                id=uuid4(),
                fund_id=fund.id,
                movement_type=movement_type,
                amount=amount,
                currency=fund.currency,
                balance_before=old_balance,
                balance_after=new_balance,
                reason=reason,
                reference_id=str(payment.id),
                created_by=payment.completed_by or "system",
                created_at=datetime.now(timezone.utc)
            )
            self._uow.session.add(movement)
            
            logger.info(
                f"Fund balance updated for {fund.code}: "
                f"{old_balance:,.2f} → {new_balance:,.2f} ({movement_type})"
            )
            return True
            
        except ConcurrentModificationError:
            raise
        except Exception as e:
            logger.error(f"Error updating fund balance: {e}", exc_info=True)
            return False
    
    # =========================================================================
    # ✅ المعالج الرئيسي - المحسّن بالكامل
    # =========================================================================
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CompletePaymentCommand, user_context: UserContext = None) -> PaymentDTO:
        """
        معالج إكمال الدفعة مع إنشاء قيد محاسبي وتحديث الصندوق
        
        ✅ يستخدم Accounting Orchestrator لإنشاء القيد المحاسبي
        ✅ يستخدم Optimistic Locking للصندوق
        ✅ معالجة الأخطاء الموحدة
        """
        with self._uow:
            # ✅ ربط الـ Orchestrator ومحرك الترحيل بجلسة الـ UoW الحالية
            # (نفس إصلاح الفواتير: منع deadlock بين جلسة الحاوية وجلسة الـ UoW)
            orchestrator = self._orchestrator
            orchestrator._uow = self._uow
            if self._posting_engine is not None:
                engine = self._posting_engine
                engine._journal_repo = self._uow.journal_entries
                engine._ledger_repo = self._uow.ledger
                engine._period_repo = self._uow.periods
                engine._account_repo = self._uow.accounts
                engine._uow = self._uow

            repo = self._uow.payments
            
            # جلب الدفعة
            payment = repo.get_by_id(PaymentId.from_string(command.payment_id))
            if not payment:
                raise PaymentNotFoundError(command.payment_id)
            
            # تحديد من قام بالإكمال
            completed_by = user_context.user_id if user_context else command.completed_by
            
            # ========== التحقق 1: إمكانية الإكمال ==========
            can_complete, errors = payment.can_complete()
            if not can_complete:
                raise ValueError(f"Cannot complete payment: {', '.join(errors)}")
            
            # ========== التحقق 2: وجود صندوق للدفع النقدي ==========
            if payment.payment_method == PaymentMethod.CASH and not payment.fund_id:
                raise ValueError("Fund required for cash payment")
            
            # ========== ✅ إنشاء القيد المحاسبي عبر Accounting Orchestrator ==========
            try:
                # 1. بناء طلب القيد من الدفعة
                journal_request = self._build_journal_entry_request(payment)
                
                # 2. تنفيذ الطلب عبر الـ Orchestrator
                orchestrator_result = self._orchestrator.create_journal_entry(
                    request=journal_request,
                    posted_by=completed_by
                )
                
                if not orchestrator_result.success:
                    raise ValueError(
                        f"Failed to create journal entry: {orchestrator_result.message}\n"
                        f"Errors: {', '.join(orchestrator_result.errors)}"
                    )
                
                journal_entry_id = orchestrator_result.journal_entry_id
                logger.info(f"Journal entry created for payment {payment.code}: {journal_entry_id}")
                
            except Exception as e:
                logger.error(f"Error creating journal entry via orchestrator: {e}", exc_info=True)
                raise ValueError(f"فشل إنشاء القيد المحاسبي: {str(e)}")
            
            # ========== ✅ تحديث رصيد الصندوق ==========
            try:
                fund_success = self._update_fund_balance(payment)
                if not fund_success:
                    raise ValueError("Failed to update fund balance")
                    
            except ConcurrentModificationError as e:
                logger.warning(f"Fund concurrent modification: {e}")
                raise ValueError(
                    "تم تعديل رصيد الصندوق بواسطة مستخدم آخر. الرجاء إعادة المحاولة."
                )
            except Exception as e:
                logger.error(f"Error updating fund balance: {e}", exc_info=True)
                raise ValueError(f"فشل تحديث رصيد الصندوق: {str(e)}")
            
            # ========== إكمال الدفعة ==========
            payment.complete(completed_by)
            
            # حفظ في قاعدة البيانات
            repo.save(payment)
            self._commit()
            
            logger.info(f"Payment completed: {payment.code} by {completed_by}")
            
            # تحويل النتيجة إلى DTO
            from dataclasses import replace
            result_dto = replace(payment_to_dto(payment), journal_entry_id=journal_entry_id)
            
            return result_dto