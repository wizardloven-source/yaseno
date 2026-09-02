# api_routers/invoices.py
"""
YAseen ERP - Invoices Router
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, Depends, status
from starlette.status import HTTP_201_CREATED

from api_routers.shared import (
    bootstrap, logger, ApiResponse, CreateInvoiceRequest,
    InvoiceLineRequest, PostInvoiceRequest, CancelInvoiceRequest,
    ReturnInvoiceRequest, get_current_user,
)

router = APIRouter(prefix="", tags=["invoices"])


@router.get("/api/invoices", response_model=ApiResponse)
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.invoices

            if status_filter:
                invoices = repo.list_by_status(status_filter, limit=limit)
            else:
                invoices = repo.list_all(limit=limit, offset=offset)

            result = []
            for inv in invoices:
                result.append({
                    'id': str(inv.id) if hasattr(inv, 'id') else None,
                    'number': str(inv.number) if hasattr(inv, 'number') else None,
                    'date': inv.date.isoformat() if hasattr(inv, 'date') else None,
                    'customer_name': inv.customer_name if hasattr(inv, 'customer_name') else '',
                    'total': float(inv.total.amount) if hasattr(inv, 'total') else 0,
                    'currency': inv.currency if hasattr(inv, 'currency') else 'USD',
                    'status': inv.status.value if hasattr(inv, 'status') else 'draft',
                })

            return ApiResponse(success=True, message="تم جلب الفواتير بنجاح", data={'items': result})
    except Exception as e:
        logger.error(f"Error listing invoices: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/invoices", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def create_invoice(request: CreateInvoiceRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import CreateInvoiceCommand, AddInvoiceLineCommand

        command_bus = bootstrap.container.resolve("command_bus")

        create_cmd = CreateInvoiceCommand(
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            site_id=request.site_id,
            site_name=request.site_name,
            currency=request.currency,
            payment_type=request.payment_type,
            payment_currency=request.payment_currency,
            fund_id=request.fund_id,
            notes=request.notes or "",
            created_by=current_user["username"],
        )
        result = command_bus.dispatch(create_cmd)

        invoice_id = None
        if isinstance(result, dict):
            invoice_id = result.get('id')
        elif hasattr(result, 'id'):
            invoice_id = result.id

        for line in request.lines:
            line_cmd = AddInvoiceLineCommand(
                invoice_id=invoice_id,
                product_code=line.get('product_code') or '',
                product_name=line.get('product_name') or '',
                quantity=Decimal(str(line.get('quantity', 0))),
                unit_price=Decimal(str(line.get('unit_price', 0))),
                currency=line.get('currency', request.currency),
                notes=line.get('notes') or '',
            )
            command_bus.dispatch(line_cmd)

        return ApiResponse(success=True, message="تم إنشاء الفاتورة بنجاح",
                           data={'id': invoice_id, 'lines_added': len(request.lines)})
    except Exception as e:
        logger.error(f"Error creating invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/invoices/{invoice_id}", response_model=ApiResponse)
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.invoicing.value_objects import InvoiceId
        from uuid import UUID as _UUID
        with bootstrap.uow() as uow:
            invoice = uow.invoices.get_by_id(InvoiceId(_UUID(invoice_id)))
            if not invoice:
                return ApiResponse(success=False, message="الفاتورة غير موجودة")
            data = {
                'id': str(invoice.id.value),
                'number': str(invoice.number) if invoice.number else None,
                'date': invoice.date.isoformat(),
                'customer_id': invoice.customer_id,
                'customer_name': invoice.customer_name,
                'site_id': invoice.site_id,
                'site_name': invoice.site_name,
                'currency': invoice.currency,
                'payment_currency': getattr(invoice, 'payment_currency', invoice.currency),
                'payment_type': invoice.payment_type.value if hasattr(invoice.payment_type, 'value') else str(invoice.payment_type),
                'fund_id': invoice.fund_id,
                'status': invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
                'subtotal': float(invoice.subtotal.amount),
                'tax_amount': float(invoice.tax_amount.amount),
                'total': float(invoice.total.amount),
                'journal_entry_id': invoice.journal_entry_id,
                'notes': invoice.notes,
                'lines': [
                    {
                        'line_id': line.line_id,
                        'product_code': line.product_code,
                        'product_name': line.product_name,
                        'quantity': float(line.quantity),
                        'unit_price': float(line.unit_price.amount),
                        'total': float(line.total.amount),
                        'currency': line.unit_price.currency,
                        'notes': line.notes,
                    }
                    for line in invoice.lines
                ],
                'version': invoice.version,
            }
            return ApiResponse(success=True, message="تم جلب الفاتورة بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/invoices/{invoice_id}/post", response_model=ApiResponse)
async def post_invoice(invoice_id: str, request: PostInvoiceRequest = None, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import PostInvoiceCommand

        if request is None:
            request = PostInvoiceRequest(force=False)

        if request.force:
            from core.application.handlers.invoicing.post_invoice_handler import PostInvoiceHandler
            with bootstrap.container.scope() as scope:
                handler = scope.resolve("post_invoice_handler")
                handler.set_force_post(True)
                command = PostInvoiceCommand(
                    invoice_id=invoice_id,
                    posted_by=current_user["username"],
                )
                result = handler.handle(command)
            return ApiResponse(success=True, message="تم ترحيل الفاتورة بنجاح", data=result)

        command_bus = bootstrap.container.resolve("command_bus")
        command = PostInvoiceCommand(
            invoice_id=invoice_id,
            posted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)

        if isinstance(result, dict) and result.get('success') is False:
            if result.get('requires_confirmation'):
                return ApiResponse(
                    success=False,
                    message=result.get('message', 'تحقق من المخزون مطلوب'),
                    data={'requires_confirmation': True, 'inventory_check': result.get('inventory_check')},
                    errors=[result.get('confirmation_message', '')],
                )
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل ترحيل الفاتورة'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )

        return ApiResponse(success=True, message="تم ترحيل الفاتورة بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/invoices/{invoice_id}/lines", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def add_invoice_line(invoice_id: str, request: InvoiceLineRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import AddInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = AddInvoiceLineCommand(
            invoice_id=invoice_id,
            product_code=request.product_code,
            product_name=request.product_name,
            quantity=request.quantity,
            unit_price=request.unit_price,
            currency=request.currency,
            notes=request.notes or "",
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إضافة السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error adding invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.patch("/api/invoices/{invoice_id}/lines/{line_id}", response_model=ApiResponse)
async def update_invoice_line(invoice_id: str, line_id: str, request: InvoiceLineRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import UpdateInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateInvoiceLineCommand(
            invoice_id=invoice_id,
            line_id=line_id,
            quantity=request.quantity,
            unit_price=request.unit_price,
            notes=request.notes or "",
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error updating invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/invoices/{invoice_id}/lines/{line_id}", response_model=ApiResponse)
async def remove_invoice_line(invoice_id: str, line_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import RemoveInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = RemoveInvoiceLineCommand(invoice_id=invoice_id, line_id=line_id)
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم حذف السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error removing invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/invoices/{invoice_id}/cancel", response_model=ApiResponse)
async def cancel_invoice(invoice_id: str, request: CancelInvoiceRequest = None, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import CancelInvoiceCommand
        reason = request.reason if request else None
        command_bus = bootstrap.container.resolve("command_bus")
        command = CancelInvoiceCommand(
            invoice_id=invoice_id,
            reason=reason,
            cancelled_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إلغاء الفاتورة بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error cancelling invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/invoices/{invoice_id}/return", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def return_invoice(invoice_id: str, request: ReturnInvoiceRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import ReturnInvoiceCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = ReturnInvoiceCommand(
            invoice_id=invoice_id,
            reason=request.reason,
            created_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء فاتورة المرتجع بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error returning invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
