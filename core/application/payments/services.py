# core/application/payments/services.py

"""
Payment Services - Business Logic Layer
خدمات الدفعات - طبقة منطق الأعمال
الإصدار: 2.0.0
✅ دعم توزيع الدفعات على الفواتير
✅ دعم إلغاء التوزيع
✅ دعم العملات المتعددة
✅ دعم سجل التوزيعات
✅ دعم البحث عن التوزيعات
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from sqlalchemy import select

from core.infrastructure.db.models.payment_model import PaymentModel
from core.infrastructure.db.models.invoice_model import InvoiceModel
from core.infrastructure.db.models.payment_allocation_model import PaymentAllocationModel

logger = logging.getLogger(__name__)


class PaymentService:
    """
    خدمة الدفعات
    إدارة إنشاء وتعديل الدفعات
    """

    def __init__(self, session: Session):
        self._session = session

    def generate_payment_number(self) -> str:
        """
        توليد رقم دفعة جديد
        """
        last_payment = (
            self._session
            .query(PaymentModel)
            .order_by(PaymentModel.created_at.desc())
            .first()
        )

        if last_payment and last_payment.number:
            try:
                last_number = int(last_payment.number.replace("PAY-", ""))
                next_number = last_number + 1
            except Exception:
                next_number = 1
        else:
            next_number = 1

        return f"PAY-{next_number:05d}"

    def create_payment(
        self,
        customer_id: str,
        customer_name: str,
        amount: Decimal,
        currency: str = "USD",
        payment_method: str = "cash",
        notes: str = "",
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        إنشاء دفعة جديدة
        """
        number = self.generate_payment_number()

        payment = PaymentModel(
            id=uuid4(),
            number=number,
            customer_id=customer_id,
            customer_name=customer_name,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            status="draft",
            notes=notes,
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )

        self._session.add(payment)
        self._session.flush()

        return {
            "id": str(payment.id),
            "number": payment.number,
            "customer_id": payment.customer_id,
            "customer_name": payment.customer_name,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "status": payment.status
        }

    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        جلب دفعة
        """
        payment = (
            self._session
            .query(PaymentModel)
            .filter(PaymentModel.id == payment_id)
            .first()
        )

        if not payment:
            return None

        return {
            "id": str(payment.id),
            "number": payment.number,
            "customer_id": payment.customer_id,
            "customer_name": payment.customer_name,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "status": payment.status
        }

    def update_payment(
        self,
        payment_id: str,
        notes: Optional[str] = None,
        payment_method: Optional[str] = None,
        fund_id: Optional[str] = None,
        updated_by: str = "system",
        version: int = 1
    ) -> Dict[str, Any]:
        """
        تحديث دفعة
        """
        payment = (
            self._session
            .query(PaymentModel)
            .filter(PaymentModel.id == payment_id)
            .first()
        )

        if not payment:
            raise ValueError("الدفعة غير موجودة")

        if payment.status in ["completed", "cancelled"]:
            raise ValueError(f"لا يمكن تحديث دفعة في حالة {payment.status}")

        if notes is not None:
            payment.notes = notes
        if payment_method is not None:
            payment.payment_method = payment_method
        if fund_id is not None:
            payment.fund_id = fund_id

        payment.updated_by = updated_by
        payment.updated_at = datetime.now(timezone.utc)
        payment.version = version + 1

        self._session.flush()

        return {
            "id": str(payment.id),
            "number": payment.number,
            "status": payment.status,
            "version": payment.version
        }

    def complete_payment(self, payment_id: str, completed_by: str = "system") -> Dict[str, Any]:
        """
        إكمال دفعة
        """
        payment = (
            self._session
            .query(PaymentModel)
            .filter(PaymentModel.id == payment_id)
            .first()
        )

        if not payment:
            raise ValueError("الدفعة غير موجودة")

        if payment.status == "completed":
            raise ValueError("الدفعة مكتملة مسبقاً")

        if payment.status == "cancelled":
            raise ValueError("لا يمكن إكمال دفعة ملغية")

        # التحقق من وجود صندوق للدفع النقدي
        if payment.payment_method == "cash" and not payment.fund_id:
            raise ValueError("الصندوق مطلوب للدفع النقدي")

        payment.status = "completed"
        payment.completed_at = datetime.now(timezone.utc)
        payment.completed_by = completed_by
        payment.version += 1

        self._session.flush()

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "completed_at": payment.completed_at.isoformat()
        }

    def cancel_payment(
        self,
        payment_id: str,
        cancelled_by: str = "system",
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        إلغاء دفعة
        """
        payment = (
            self._session
            .query(PaymentModel)
            .filter(PaymentModel.id == payment_id)
            .first()
        )

        if not payment:
            raise ValueError("الدفعة غير موجودة")

        if payment.status == "completed":
            raise ValueError("لا يمكن إلغاء دفعة مكتملة")

        if payment.status == "cancelled":
            raise ValueError("الدفعة ملغية مسبقاً")

        payment.status = "cancelled"
        payment.cancelled_by = cancelled_by
        payment.cancelled_at = datetime.now(timezone.utc)
        payment.cancellation_reason = reason
        payment.version += 1

        self._session.flush()

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "cancelled_at": payment.cancelled_at.isoformat()
        }

    def delete_draft_payment(self, payment_id: str, deleted_by: str = "system") -> bool:
        """
        حذف دفعة مسودة
        """
        payment = (
            self._session
            .query(PaymentModel)
            .filter(PaymentModel.id == payment_id)
            .first()
        )

        if not payment:
            return False

        if payment.status != "draft":
            raise ValueError(f"لا يمكن حذف دفعة في حالة {payment.status}")

        self._session.delete(payment)
        self._session.flush()

        return True


# =============================================================================
# PaymentAllocationService - الخدمة المطورة بالكامل
# =============================================================================

class PaymentAllocationService:
    """
    خدمة توزيع الدفعات على الفواتير
    
    مسؤولياته:
        1. توزيع مبلغ دفعة على فاتورة
        2. تحديث رصيد الفاتورة
        3. تحديث حالة الفاتورة (مدفوعة/جزئية)
        4. إلغاء توزيعات الدفعات
        5. دعم العملات المتعددة
        6. إنشاء سجل التوزيعات
        7. البحث عن التوزيعات
    """

    def __init__(self, session: Session, payment_repo=None, invoice_repo=None):
        """
        Args:
            session: جلسة قاعدة البيانات
            payment_repo: مستودع الدفعات (اختياري)
            invoice_repo: مستودع الفواتير (اختياري)
        """
        self._session = session
        self._payment_repo = payment_repo
        self._invoice_repo = invoice_repo

    def allocate_payment(
        self,
        payment_id: str,
        invoice_id: str,
        amount: Decimal,
        allocated_by: str = "system"
    ) -> Dict[str, Any]:
        """
        توزيع مبلغ دفعة على فاتورة
        
        Args:
            payment_id: معرف الدفعة
            invoice_id: معرف الفاتورة
            amount: المبلغ المراد توزيعه
            allocated_by: من قام بالتوزيع
        
        Returns:
            Dict[str, Any]: نتيجة التوزيع
        """
        logger.info(f"Allocating payment {payment_id} to invoice {invoice_id}: {amount}")
        
        try:
            # 1. جلب الدفعة
            payment = self._session.execute(
                select(PaymentModel).where(PaymentModel.id == payment_id)
            ).scalar_one_or_none()
            
            if not payment:
                return {
                    "success": False,
                    "message": f"Payment {payment_id} not found"
                }
            
            # 2. جلب الفاتورة
            invoice = self._session.execute(
                select(InvoiceModel).where(InvoiceModel.id == invoice_id)
            ).scalar_one_or_none()
            
            if not invoice:
                return {
                    "success": False,
                    "message": f"Invoice {invoice_id} not found"
                }
            
            # 3. التحقق من المبلغ
            if amount <= 0:
                return {
                    "success": False,
                    "message": "Amount must be greater than zero"
                }
            
            # 4. التحقق من عملة الدفعة والفاتورة
            if payment.currency != invoice.currency:
                logger.warning(
                    f"Currency mismatch: payment {payment.currency}, invoice {invoice.currency}"
                )
                # يمكن إضافة دعم تحويل العملات هنا
            
            # 5. حساب المبلغ المتبقي للفاتورة
            paid_amount = invoice.paid_amount or Decimal('0')
            remaining = invoice.total_amount - paid_amount
            
            if amount > remaining:
                return {
                    "success": False,
                    "message": f"Amount {amount} exceeds remaining invoice amount {remaining}"
                }
            
            if amount > payment.amount:
                return {
                    "success": False,
                    "message": f"Amount {amount} exceeds payment amount {payment.amount}"
                }
            
            # 6. تحديث رصيد الفاتورة
            invoice.paid_amount = paid_amount + amount
            
            # 7. تحديث حالة الفاتورة
            if invoice.paid_amount >= invoice.total_amount:
                invoice.payment_status = "paid"
            else:
                invoice.payment_status = "partial"
            
            # 8. تحديث الدفعة
            payment.allocated_amount = (payment.allocated_amount or Decimal('0')) + amount
            
            if payment.allocated_amount >= payment.amount:
                payment.status = "completed"
            
            # 9. إنشاء سجل التوزيع
            allocation = PaymentAllocationModel(
                id=uuid4(),
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount=amount,
                currency=payment.currency,
                allocated_by=allocated_by,
                allocated_at=datetime.now(timezone.utc),
                status="active"
            )
            self._session.add(allocation)
            
            # 10. حفظ التغييرات
            self._session.flush()
            
            logger.info(f"✅ Allocation successful: {amount} to invoice {invoice_id}")
            
            return {
                "success": True,
                "payment_id": str(payment.id),
                "invoice_id": str(invoice.id),
                "allocated_amount": float(amount),
                "payment_status": payment.status,
                "invoice_payment_status": invoice.payment_status,
                "remaining_invoice_amount": float(remaining - amount),
                "allocation_id": str(allocation.id)
            }
            
        except Exception as e:
            logger.error(f"Error allocating payment: {e}")
            self._session.rollback()
            return {
                "success": False,
                "message": f"Allocation failed: {str(e)}"
            }

    def reverse_allocation(
        self,
        allocation_id: str,
        reversed_by: str = "system",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        إلغاء توزيع دفعة
        
        Args:
            allocation_id: معرف التوزيع
            reversed_by: من قام بالإلغاء
            reason: سبب الإلغاء
        
        Returns:
            Dict[str, Any]: نتيجة الإلغاء
        """
        logger.info(f"Reversing allocation {allocation_id} by {reversed_by}")
        
        try:
            # 1. جلب التوزيع
            allocation = self._session.execute(
                select(PaymentAllocationModel).where(
                    PaymentAllocationModel.id == allocation_id
                )
            ).scalar_one_or_none()
            
            if not allocation:
                return {
                    "success": False,
                    "message": f"Allocation {allocation_id} not found"
                }
            
            if allocation.status == "reversed":
                return {
                    "success": False,
                    "message": f"Allocation {allocation_id} already reversed"
                }
            
            # 2. جلب الدفعة
            payment = self._session.execute(
                select(PaymentModel).where(PaymentModel.id == allocation.payment_id)
            ).scalar_one_or_none()
            
            if not payment:
                return {
                    "success": False,
                    "message": f"Payment {allocation.payment_id} not found"
                }
            
            # 3. جلب الفاتورة
            invoice = self._session.execute(
                select(InvoiceModel).where(InvoiceModel.id == allocation.invoice_id)
            ).scalar_one_or_none()
            
            if not invoice:
                return {
                    "success": False,
                    "message": f"Invoice {allocation.invoice_id} not found"
                }
            
            # 4. تحديث رصيد الفاتورة
            invoice.paid_amount = (invoice.paid_amount or Decimal('0')) - allocation.amount
            
            # 5. تحديث حالة الفاتورة
            if invoice.paid_amount <= 0:
                invoice.payment_status = "unpaid"
            elif invoice.paid_amount < invoice.total_amount:
                invoice.payment_status = "partial"
            else:
                invoice.payment_status = "paid"
            
            # 6. تحديث الدفعة
            payment.allocated_amount = (payment.allocated_amount or Decimal('0')) - allocation.amount
            
            if payment.allocated_amount <= 0:
                payment.status = "draft"
            elif payment.allocated_amount < payment.amount:
                payment.status = "pending"
            else:
                payment.status = "completed"
            
            # 7. تحديث سجل التوزيع
            allocation.status = "reversed"
            allocation.reversed_by = reversed_by
            allocation.reversed_at = datetime.now(timezone.utc)
            allocation.reversal_reason = reason
            
            self._session.flush()
            
            logger.info(f"✅ Allocation {allocation_id} reversed successfully")
            
            return {
                "success": True,
                "allocation_id": allocation_id,
                "payment_id": str(payment.id),
                "invoice_id": str(invoice.id),
                "reversed_amount": float(allocation.amount),
                "payment_status": payment.status,
                "invoice_payment_status": invoice.payment_status,
                "message": "Allocation reversed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error reversing allocation: {e}")
            self._session.rollback()
            return {
                "success": False,
                "message": f"Reversal failed: {str(e)}"
            }

    def get_allocation(self, allocation_id: str) -> Optional[Dict[str, Any]]:
        """
        الحصول على تفاصيل توزيع
        
        Args:
            allocation_id: معرف التوزيع
        
        Returns:
            Optional[Dict[str, Any]]: تفاصيل التوزيع
        """
        allocation = self._session.execute(
            select(PaymentAllocationModel).where(
                PaymentAllocationModel.id == allocation_id
            )
        ).scalar_one_or_none()
        
        if not allocation:
            return None
        
        return {
            'id': str(allocation.id),
            'payment_id': str(allocation.payment_id),
            'invoice_id': str(allocation.invoice_id),
            'amount': float(allocation.amount),
            'currency': allocation.currency,
            'status': allocation.status,
            'allocated_at': allocation.allocated_at.isoformat() if allocation.allocated_at else None,
            'allocated_by': allocation.allocated_by,
            'reversed_at': allocation.reversed_at.isoformat() if allocation.reversed_at else None,
            'reversed_by': allocation.reversed_by,
            'reversal_reason': allocation.reversal_reason
        }

    def get_payment_allocations(
        self,
        payment_id: str,
        include_cancelled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        الحصول على جميع توزيعات دفعة
        
        Args:
            payment_id: معرف الدفعة
            include_cancelled: تضمين التوزيعات الملغاة
        
        Returns:
            List[Dict[str, Any]]: قائمة التوزيعات
        """
        query = select(PaymentAllocationModel).where(
            PaymentAllocationModel.payment_id == payment_id
        )
        
        if not include_cancelled:
            query = query.where(PaymentAllocationModel.status == "active")
        
        allocations = self._session.execute(query).scalars().all()
        
        return [
            {
                'id': str(a.id),
                'payment_id': str(a.payment_id),
                'invoice_id': str(a.invoice_id),
                'amount': float(a.amount),
                'currency': a.currency,
                'status': a.status,
                'allocated_at': a.allocated_at.isoformat() if a.allocated_at else None,
                'allocated_by': a.allocated_by,
                'reversed_at': a.reversed_at.isoformat() if a.reversed_at else None,
                'reversed_by': a.reversed_by,
                'reversal_reason': a.reversal_reason
            }
            for a in allocations
        ]

    def get_invoice_allocations(
        self,
        invoice_id: str,
        include_cancelled: bool = False
    ) -> List[Dict[str, Any]]:
        """
        الحصول على جميع توزيعات فاتورة
        
        Args:
            invoice_id: معرف الفاتورة
            include_cancelled: تضمين التوزيعات الملغاة
        
        Returns:
            List[Dict[str, Any]]: قائمة التوزيعات
        """
        query = select(PaymentAllocationModel).where(
            PaymentAllocationModel.invoice_id == invoice_id
        )
        
        if not include_cancelled:
            query = query.where(PaymentAllocationModel.status == "active")
        
        allocations = self._session.execute(query).scalars().all()
        
        return [
            {
                'id': str(a.id),
                'payment_id': str(a.payment_id),
                'invoice_id': str(a.invoice_id),
                'amount': float(a.amount),
                'currency': a.currency,
                'status': a.status,
                'allocated_at': a.allocated_at.isoformat() if a.allocated_at else None,
                'allocated_by': a.allocated_by,
                'reversed_at': a.reversed_at.isoformat() if a.reversed_at else None,
                'reversed_by': a.reversed_by,
                'reversal_reason': a.reversal_reason
            }
            for a in allocations
        ]

    def get_customer_allocations(
        self,
        customer_id: str
    ) -> List[Dict[str, Any]]:
        """
        جلب توزيع دفعات العميل
        
        Args:
            customer_id: معرف العميل
        
        Returns:
            List[Dict[str, Any]]: قائمة توزيعات العميل
        """
        invoices = self._session.execute(
            select(InvoiceModel).where(InvoiceModel.customer_id == customer_id)
        ).scalars().all()

        result = []
        for invoice in invoices:
            # جلب توزيعات الفاتورة
            allocations = self.get_invoice_allocations(str(invoice.id))
            total_allocated = sum(a['amount'] for a in allocations if a['status'] == 'active')
            
            result.append({
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.number,
                "total": float(invoice.total_amount),
                "paid": float(invoice.paid_amount or 0),
                "allocated": float(total_allocated),
                "remaining": float((invoice.total_amount - (invoice.paid_amount or 0))),
                "payment_status": invoice.payment_status or "unpaid",
                "allocations": allocations
            })

        return result