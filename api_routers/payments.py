from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from api_routers.shared import bootstrap, logger, ApiResponse, CreatePaymentRequest, get_current_user

router = APIRouter(prefix="", tags=["payments"])


class PaymentReasonRequest(BaseModel):
    reason: str = ""


class AllocatePaymentRequest(BaseModel):
    invoice_id: str
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# PAYMENTS
# =============================================================================

@router.get("/api/payments", response_model=ApiResponse)
async def list_payments(
    payment_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            filters = {"limit": limit, "offset": offset}
            if payment_type:
                filters["payment_type"] = payment_type
            if status_filter:
                filters["status"] = status_filter
            payments = uow.payments.list_by_filters(filters)
            result = []
            for p in payments:
                result.append({
                    'id': str(p.id.value),
                    'code': str(p.code) if hasattr(p.code, 'value') else str(p.code),
                    'date': p.date.isoformat(),
                    'payment_type': p.payment_type.value if hasattr(p.payment_type, 'value') else str(p.payment_type),
                    'payment_method': p.payment_method.value if hasattr(p.payment_method, 'value') else str(p.payment_method),
                    'amount': float(p.amount.amount),
                    'currency': p.currency if hasattr(p, 'currency') else 'USD',
                    'status': p.status.value if hasattr(p.status, 'value') else str(p.status),
                    'customer_name': p.customer_name,
                    'supplier_name': p.supplier_name,
                })
            return ApiResponse(success=True, message="تم جلب المدفوعات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing payments: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(request: CreatePaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.entities import Payment
        from core.domain.payments.value_objects import PaymentType, PaymentMethod
        from core.domain.shared.value_objects import Money

        payment = Payment.create(
            payment_type=PaymentType(request.payment_type),
            amount=Money(request.amount, request.currency),
            payment_method=PaymentMethod(request.payment_method),
            customer_id=request.customer_id,
            supplier_id=request.supplier_id,
            fund_id=request.fund_id,
            notes=request.description or "",
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.payments.save(payment)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء الدفع بنجاح",
                           data={'id': str(payment.id.value), 'status': 'draft'})
    except Exception as e:
        logger.error(f"Error creating payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/payments/{payment_id}", response_model=ApiResponse)
async def get_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.value_objects import PaymentId
        with bootstrap.uow() as uow:
            payment = uow.payments.get_by_id(PaymentId.from_string(payment_id))
            if not payment:
                return ApiResponse(success=False, message="الدفع غير موجود")
            data = {
                'id': str(payment.id.value),
                'code': str(payment.code),
                'date': payment.date.isoformat(),
                'payment_type': payment.payment_type.value if hasattr(payment.payment_type, 'value') else str(payment.payment_type),
                'payment_method': payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method),
                'amount': float(payment.amount.amount),
                'currency': payment.currency if hasattr(payment, 'currency') else 'USD',
                'status': payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
                'customer_name': payment.customer_name,
                'supplier_name': payment.supplier_name,
                'notes': payment.notes if hasattr(payment, 'notes') else None,
                'version': payment.version,
            }
            return ApiResponse(success=True, message="تم جلب الدفع بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments/{payment_id}/submit", response_model=ApiResponse)
async def submit_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.value_objects import PaymentId
        with bootstrap.uow() as uow:
            payment = uow.payments.get_by_id(PaymentId.from_string(payment_id))
            if not payment:
                return ApiResponse(success=False, message="الدفع غير موجود")
            payment.submit(current_user["username"])
            uow.payments.save(payment)
            uow.commit()
        return ApiResponse(success=True, message="تم إرسال الدفع للاعتماد بنجاح",
                           data={'id': payment_id, 'status': 'pending'})
    except Exception as e:
        logger.error(f"Error submitting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments/{payment_id}/approve", response_model=ApiResponse)
async def approve_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import ApprovePaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = ApprovePaymentCommand(
            payment_id=payment_id,
            approved_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم اعتماد الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error approving payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments/{payment_id}/reject", response_model=ApiResponse)
async def reject_payment(payment_id: str, request: PaymentReasonRequest = None,
                         current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import RejectPaymentCommand
        if request is None:
            request = PaymentReasonRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = RejectPaymentCommand(
            payment_id=payment_id,
            rejected_by=current_user["username"],
            reason=request.reason,
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم رفض الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments/{payment_id}/complete", response_model=ApiResponse)
async def complete_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import CompletePaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = CompletePaymentCommand(
            payment_id=payment_id,
            completed_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        data = {
            'id': str(getattr(result, 'id', payment_id)),
            'status': getattr(result, 'status', None),
            'journal_entry_id': getattr(result, 'journal_entry_id', None),
        }
        return ApiResponse(success=True, message="تم إكمال الدفع بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error completing payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/payments/{payment_id}/cancel", response_model=ApiResponse)
async def cancel_payment(payment_id: str, request: PaymentReasonRequest = None,
                         current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import CancelPaymentCommand
        if request is None:
            request = PaymentReasonRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = CancelPaymentCommand(
            payment_id=payment_id,
            cancelled_by=current_user["username"],
            reason=request.reason,
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إلغاء الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/payments/{payment_id}", response_model=ApiResponse)
async def delete_draft_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import DeleteDraftPaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = DeleteDraftPaymentCommand(
            payment_id=payment_id,
            deleted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم حذف الدفع بنجاح",
                           data={'id': payment_id, 'result': result})
    except Exception as e:
        logger.error(f"Error deleting draft payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# PAYMENT ALLOCATION (توزيع الدفعات)
# =============================================================================

@router.post("/api/payments/{payment_id}/allocate", response_model=ApiResponse)
async def allocate_payment(payment_id: str, request: AllocatePaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            payment = uow.session.execute(text(
                "SELECT id, code, amount, currency, status FROM payments WHERE id::text = :pid"
            ), {"pid": payment_id}).mappings().first()
            if payment is None:
                return ApiResponse(success=False, message="الدفعة غير موجودة")

            invoice = uow.session.execute(text(
                "SELECT id, number, total_amount, status FROM invoices WHERE id::text = :iid"
            ), {"iid": request.invoice_id}).mappings().first()
            if invoice is None:
                return ApiResponse(success=False, message="الفاتورة غير موجودة")

            currency = request.currency or payment["currency"]
            amount = Decimal(str(request.amount))
            if amount > Decimal(str(payment["amount"])):
                return ApiResponse(success=False, message="مبلغ التوزيع أكبر من مبلغ الدفعة")

            allocation_id = uuid.uuid4()
            uow.session.execute(
                text("INSERT INTO payment_allocations "
                     "(id, payment_id, invoice_id, amount, currency, status, allocated_at, allocated_by, notes) "
                     "VALUES (:id, :pid, :iid, :amount, :currency, 'active', now(), :by, :notes)"),
                {
                    "id": allocation_id,
                    "pid": uuid.UUID(payment_id),
                    "iid": uuid.UUID(request.invoice_id),
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                    "notes": request.notes,
                },
            )
            uow.commit()

            return ApiResponse(success=True, message="تم توزيع الدفعة بنجاح",
                               data={
                                   "allocation_id": str(allocation_id),
                                   "payment_id": payment_id,
                                   "invoice_id": request.invoice_id,
                                   "amount": float(amount),
                                   "currency": currency,
                               })
    except Exception as e:
        logger.error(f"Error allocating payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
