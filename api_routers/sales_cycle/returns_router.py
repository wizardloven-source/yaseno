# api_routers/sales_cycle/returns_router.py
"""
YAseen ERP - Sales Returns Router
✅ جديد: API لإدارة إرجاع المبيعات ومذكرات الدائنة
"""

from decimal import Decimal
from typing import Optional, List
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Depends, status, HTTPException
from starlette.status import HTTP_201_CREATED

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="/sales-returns", tags=["sales_returns"])


# =============================================================================
# Request Models
# =============================================================================

class ReturnItemRequest:
    """طلب صنف إرجاع"""
    def __init__(
        self,
        product_code: str,
        product_name: str,
        quantity: float,
        unit_price: float,
        reason: Optional[str] = None,
        condition: str = "good",
        discount_percent: float = 0.0,
        tax_rate: float = 0.0,
        notes: Optional[str] = None,
    ):
        self.product_code = product_code
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price
        self.reason = reason
        self.condition = condition
        self.discount_percent = discount_percent
        self.tax_rate = tax_rate
        self.notes = notes


class CreateSalesReturnRequest:
    """طلب إنشاء إرجاع مبيعات"""
    def __init__(
        self,
        customer_id: str,
        customer_name: str,
        original_invoice_id: Optional[str] = None,
        original_invoice_number: Optional[str] = None,
        original_delivery_id: Optional[str] = None,
        return_date: Optional[str] = None,
        currency: str = "USD",
        items: List[ReturnItemRequest] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.original_invoice_id = original_invoice_id
        self.original_invoice_number = original_invoice_number
        self.original_delivery_id = original_delivery_id
        self.return_date = return_date
        self.currency = currency
        self.items = items or []
        self.reason = reason
        self.notes = notes


# =============================================================================
# Sales Returns Endpoints
# =============================================================================

@router.get("", response_model=ApiResponse)
async def list_sales_returns(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """
    قائمة عمليات إرجاع المبيعات
    
    - **customer_id**: تصفية حسب العميل
    - **status**: تصفية حسب الحالة (draft, submitted, approved, etc.)
    - **date_from**: من تاريخ
    - **date_to**: إلى تاريخ
    """
    try:
        from core.domain.sales.value_objects import ReturnStatus
        
        with bootstrap.uow() as uow:
            repo = uow.sales_returns
            
            # بناء الفلتر
            from core.domain.sales.interfaces import ReturnFilter
            filter_obj = ReturnFilter(
                customer_id=customer_id,
                status=ReturnStatus(status) if status else None,
                date_from=date.fromisoformat(date_from) if date_from else None,
                date_to=date.fromisoformat(date_to) if date_to else None,
                limit=limit,
                offset=offset,
            )
            
            returns = repo.find(filter_obj)
            
            result = []
            for ret in returns:
                result.append({
                    'id': str(ret.id.value),
                    'number': str(ret.number),
                    'return_date': ret.return_date.isoformat(),
                    'customer_id': ret.customer_id,
                    'customer_name': ret.customer_name,
                    'original_invoice_number': ret.original_invoice_number,
                    'status': ret.status.value,
                    'total_amount': float(ret.total_amount.amount),
                    'currency': ret.currency,
                    'credit_note_number': str(ret.credit_note_number) if ret.credit_note_number else None,
                })
            
            return ApiResponse(
                success=True, 
                message="تم جلب عمليات الإرجاع بنجاح", 
                data={'items': result, 'total': len(result)}
            )
    except Exception as e:
        logger.error(f"Error listing sales returns: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/{return_id}", response_model=ApiResponse)
async def get_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    الحصول على تفاصيل إرجاع مبيعات
    
    - **return_id**: معرف الإرجاع
    """
    try:
        from core.domain.sales.value_objects import ReturnId
        
        with bootstrap.uow() as uow:
            repo = uow.sales_returns
            ret = repo.get_by_id(ReturnId.from_string(return_id))
            
            if not ret:
                return ApiResponse(success=False, message="إرجاع المبيعات غير موجود")
            
            # تحويل الأسطر
            lines_data = []
            for line in ret.lines:
                lines_data.append({
                    'product_code': line.product_code,
                    'product_name': line.product_name,
                    'quantity': float(line.quantity),
                    'unit_price': float(line.unit_price.amount),
                    'reason': line.reason,
                    'condition': line.condition,
                    'discount_percent': float(line.discount_percent),
                    'tax_rate': float(line.tax_rate),
                    'total': float(line.total_with_tax.amount),
                })
            
            return ApiResponse(
                success=True,
                message="تم جلب تفاصيل الإرجاع بنجاح",
                data={
                    'id': str(ret.id.value),
                    'number': str(ret.number),
                    'return_date': ret.return_date.isoformat(),
                    'customer_id': ret.customer_id,
                    'customer_name': ret.customer_name,
                    'original_invoice_id': str(ret.original_invoice_id) if ret.original_invoice_id else None,
                    'original_invoice_number': ret.original_invoice_number,
                    'status': ret.status.value,
                    'reason': ret.reason,
                    'notes': ret.notes,
                    'currency': ret.currency,
                    'subtotal': float(ret.subtotal.amount),
                    'discount_amount': float(ret.total_discount.amount),
                    'tax_amount': float(ret.tax_amount.amount),
                    'total_amount': float(ret.total_amount.amount),
                    'lines': lines_data,
                    'credit_note_id': str(ret.credit_note_id.value) if ret.credit_note_id else None,
                    'credit_note_number': str(ret.credit_note_number) if ret.credit_note_number else None,
                    'journal_entry_id': ret.journal_entry_id,
                    'created_at': ret.created_at.isoformat(),
                    'created_by': ret.created_by,
                }
            )
    except Exception as e:
        logger.error(f"Error getting sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def create_sales_return(request: CreateSalesReturnRequest, current_user: dict = Depends(get_current_user)):
    """
    إنشاء إرجاع مبيعات جديد
    
    - **customer_id**: معرف العميل
    - **customer_name**: اسم العميل
    - **original_invoice_id**: معرف الفاتورة الأصلية (اختياري)
    - **items**: قائمة الأصناف المرتجعة
    - **reason**: سبب الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.create_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import CreateSalesReturnCommand, ReturnItemCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        # تحويل الأصناف
        items = []
        for item in request.items:
            items.append(ReturnItemCommand(
                product_code=item.product_code,
                product_name=item.product_name,
                quantity=Decimal(str(item.quantity)),
                unit_price=Decimal(str(item.unit_price)),
                reason=item.reason,
                condition=item.condition,
                discount_percent=Decimal(str(item.discount_percent)),
                tax_rate=Decimal(str(item.tax_rate)),
                notes=item.notes,
            ))
        
        # إنشاء أمر الإنشاء
        create_cmd = CreateSalesReturnCommand(
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            original_invoice_id=UUID(request.original_invoice_id) if request.original_invoice_id else None,
            original_invoice_number=request.original_invoice_number,
            original_delivery_id=request.original_delivery_id,
            currency=request.currency,
            items=items,
            reason=request.reason,
            notes=request.notes,
            created_by=current_user["username"],
        )
        
        result = command_bus.dispatch(create_cmd)
        
        return ApiResponse(
            success=True,
            message="تم إنشاء إرجاع المبيعات بنجاح",
            data={
                'id': str(result['return_id']),
                'number': result.get('return_number'),
            }
        )
    except Exception as e:
        logger.error(f"Error creating sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/submit", response_model=ApiResponse)
async def submit_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    تقديم إرجاع المبيعات للموافقة
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.submit_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import SubmitSalesReturnCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        submit_cmd = SubmitSalesReturnCommand(
            return_id=ReturnId.from_string(return_id),
            submitted_by=current_user["username"],
        )
        
        command_bus.dispatch(submit_cmd)
        
        return ApiResponse(success=True, message="تم تقديم إرجاع المبيعات بنجاح")
    except Exception as e:
        logger.error(f"Error submitting sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/approve", response_model=ApiResponse)
async def approve_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    الموافقة على إرجاع المبيعات
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.approve_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import ApproveSalesReturnCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        approve_cmd = ApproveSalesReturnCommand(
            return_id=ReturnId.from_string(return_id),
            approved_by=current_user["username"],
        )
        
        command_bus.dispatch(approve_cmd)
        
        return ApiResponse(success=True, message="تمت الموافقة على إرجاع المبيعات بنجاح")
    except Exception as e:
        logger.error(f"Error approving sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/receive", response_model=ApiResponse)
async def receive_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    استلام البضائع المرتجعة
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.receive_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import ReceiveSalesReturnCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        receive_cmd = ReceiveSalesReturnCommand(
            return_id=ReturnId.from_string(return_id),
            received_by=current_user["username"],
        )
        
        command_bus.dispatch(receive_cmd)
        
        return ApiResponse(success=True, message="تم استلام البضائع المرتجعة بنجاح")
    except Exception as e:
        logger.error(f"Error receiving sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/inspect", response_model=ApiResponse)
async def inspect_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    فحص البضائع المرتجعة
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.inspect_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import InspectSalesReturnCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        inspect_cmd = InspectSalesReturnCommand(
            return_id=ReturnId.from_string(return_id),
            inspected_by=current_user["username"],
        )
        
        command_bus.dispatch(inspect_cmd)
        
        return ApiResponse(success=True, message="تم فحص البضائع المرتجعة بنجاح")
    except Exception as e:
        logger.error(f"Error inspecting sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/complete", response_model=ApiResponse)
async def complete_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    إكمال إرجاع المبيعات وإنشاء مذكرة الدائن
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.complete_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.services import SalesReturnService
        from core.domain.sales.value_objects import ReturnId
        
        with bootstrap.uow() as uow:
            service = SalesReturnService(
                return_repo=uow.sales_returns,
                inventory_service=None,  # سيتم حقنها
                credit_note_service=None,  # سيتم حقنها
            )
            
            service.complete_return(ReturnId.from_string(return_id), current_user["username"])
            
            return ApiResponse(success=True, message="تم إكمال إرجاع المبيعات بنجاح")
    except Exception as e:
        logger.error(f"Error completing sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/{return_id}/cancel", response_model=ApiResponse)
async def cancel_sales_return(return_id: str, current_user: dict = Depends(get_current_user)):
    """
    إلغاء إرجاع المبيعات
    
    - **return_id**: معرف الإرجاع
    """
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("sales.cancel_return"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    
    try:
        from core.application.sales.commands import CancelSalesReturnCommand
        from core.domain.sales.value_objects import ReturnId
        
        command_bus = bootstrap.container.resolve("command_bus")
        
        cancel_cmd = CancelSalesReturnCommand(
            return_id=ReturnId.from_string(return_id),
            cancelled_by=current_user["username"],
        )
        
        command_bus.dispatch(cancel_cmd)
        
        return ApiResponse(success=True, message="تم إلغاء إرجاع المبيعات بنجاح")
    except Exception as e:
        logger.error(f"Error cancelling sales return: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


__all__ = ["router"]
