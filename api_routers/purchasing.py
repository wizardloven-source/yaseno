from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field

from api_routers.shared import bootstrap, logger, ApiResponse, CreatePurchaseOrderRequest, get_current_user
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["purchasing"])


class ReceivePurchaseOrderRequest(BaseModel):
    batch_numbers: Optional[Dict[str, str]] = None
    serial_numbers: Optional[Dict[str, List[str]]] = None
    expiry_dates: Optional[Dict[str, datetime]] = None
    locations: Optional[Dict[str, str]] = None


# =============================================================================
# PURCHASE ORDERS
# =============================================================================

@router.get("/api/purchase-orders", response_model=ApiResponse)
async def list_purchase_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.purchase_orders
            from core.domain.purchasing.value_objects import PurchaseOrderStatus
            if status_filter:
                orders = repo.list_by_status(PurchaseOrderStatus(status_filter), limit=limit, offset=offset)
            else:
                orders = repo.list_by_filters(limit=limit, offset=offset)
            result = []
            for o in orders:
                result.append({
                    'id': str(o.id.value),
                    'number': str(o.number) if o.number else None,
                    'date': o.date.isoformat(),
                    'supplier_id': o.supplier_id,
                    'supplier_name': o.supplier_name,
                    'status': o.status.value if hasattr(o.status, 'value') else str(o.status),
                    'currency': o.currency,
                    'total': float(o.total.amount),
                })
            return ApiResponse(success=True, message="تم جلب أوامر الشراء بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing purchase orders: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/purchase-orders", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(request: CreatePurchaseOrderRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("purchasing.create_order"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.domain.purchasing.entities import PurchaseOrder, PurchaseLine
        from core.domain.shared.value_objects import Money

        supplier_name = request.supplier_name or ""
        if not supplier_name:
            try:
                from core.domain.suppliers.value_objects import SupplierId
                with bootstrap.uow() as uow:
                    supplier = uow.suppliers.get_by_id(SupplierId.from_string(request.supplier_id))
                    if supplier:
                        supplier_name = supplier.name
            except Exception:
                pass

        order = PurchaseOrder(
            supplier_id=request.supplier_id,
            supplier_name=supplier_name,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"],
        )
        if request.expected_delivery_date:
            from datetime import datetime as _dt
            order.expected_delivery_date = _dt.combine(request.expected_delivery_date, _dt.min.time())
        for line_req in request.lines:
            line = PurchaseLine(
                product_code=line_req.product_code,
                product_name=line_req.product_name,
                quantity=line_req.quantity,
                unit_price=Money(line_req.unit_price, request.currency),
                notes=line_req.notes or "",
            )
            order.add_line(line)

        with bootstrap.uow() as uow:
            uow.purchase_orders.save(order)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء أمر الشراء بنجاح",
                           data={'id': str(order.id.value), 'status': 'draft'})
    except Exception as e:
        logger.error(f"Error creating purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/purchase-orders/{order_id}", response_model=ApiResponse)
async def get_purchase_order(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.purchasing.value_objects import PurchaseOrderId
        with bootstrap.uow() as uow:
            order = uow.purchase_orders.get_by_id(PurchaseOrderId.from_string(order_id))
            if not order:
                return ApiResponse(success=False, message="أمر الشراء غير موجود")
            data = {
                'id': str(order.id.value),
                'number': str(order.number) if order.number else None,
                'date': order.date.isoformat(),
                'supplier_id': order.supplier_id,
                'supplier_name': order.supplier_name,
                'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                'currency': order.currency,
                'total': float(order.total.amount),
                'lines': [
                    {
                        'product_code': ln.product_code,
                        'product_name': ln.product_name,
                        'quantity': float(ln.quantity),
                        'unit_price': float(ln.unit_price.amount),
                        'received_quantity': float(ln.received_quantity),
                    }
                    for ln in order.lines
                ],
                'version': order.version,
            }
            return ApiResponse(success=True, message="تم جلب أمر الشراء بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/purchase-orders/{order_id}/post", response_model=ApiResponse)
async def post_purchase_order(order_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("purchasing.post_order"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.application.purchasing.commands import PostPurchaseOrderCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = PostPurchaseOrderCommand(
            order_id=order_id,
            posted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)

        if isinstance(result, dict) and result.get('success') is False:
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل ترحيل أمر الشراء'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )
        return ApiResponse(success=True, message="تم ترحيل أمر الشراء بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/purchase-orders/{order_id}/receive", response_model=ApiResponse)
async def receive_purchase_order(order_id: str, request: ReceivePurchaseOrderRequest = None,
                                 current_user: dict = Depends(get_current_user)):
    try:
        from core.application.purchasing.commands import ReceivePurchaseOrderCommand
        if request is None:
            request = ReceivePurchaseOrderRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = ReceivePurchaseOrderCommand(
            order_id=order_id,
            received_by=current_user["username"],
            batch_numbers=request.batch_numbers,
            serial_numbers=request.serial_numbers,
            expiry_dates=request.expiry_dates,
            locations=request.locations,
        )
        result = command_bus.dispatch(command)

        if isinstance(result, dict) and result.get('success') is False:
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل استلام أمر الشراء'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )
        data = {
            'id': getattr(result, 'id', None),
            'number': getattr(result, 'number', None),
            'status': getattr(result, 'status', None),
            'is_fully_received': result.is_fully_received if hasattr(result, 'is_fully_received') else None,
            'stock_movements': getattr(result, 'stock_movements', []),
            'lines': [
                {
                    'line_id': ln.line_id,
                    'product_code': ln.product_code,
                    'quantity': float(ln.quantity),
                    'received_quantity': float(ln.received_quantity),
                    'is_fully_received': ln.is_fully_received,
                }
                for ln in result.lines
            ],
        }
        return ApiResponse(success=True, message="تم استلام أمر الشراء بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error receiving purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class ReturnPurchaseOrderRequest(BaseModel):
    reason: str = Field(..., min_length=2)


@router.post("/api/purchase-orders/{order_id}/return", response_model=ApiResponse)
async def return_purchase_order(
    order_id: str,
    request: ReturnPurchaseOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.domain.purchasing.entities import PurchaseOrder, PurchaseLine
        from core.domain.purchasing.value_objects import PurchaseOrderId
        from core.domain.shared.value_objects import Money

        with bootstrap.uow() as uow:
            repo = uow.purchase_orders
            original = repo.get_by_id(PurchaseOrderId.from_string(order_id))
            if not original:
                return ApiResponse(success=False, message="أمر الشراء غير موجود")
            if not original.is_posted:
                return ApiResponse(success=False, message="لا يمكن إنشاء مرتجع لأمر شراء غير مرحل")

            return_order = PurchaseOrder(
                supplier_id=original.supplier_id,
                supplier_name=original.supplier_name,
                currency=original.currency,
                notes=f"مرتجع من أمر الشراء {original.number} - {request.reason}",
                created_by=current_user["username"],
            )
            for line in original.lines:
                pline = PurchaseLine(
                    product_code=line.product_code,
                    product_name=line.product_name,
                    quantity=-line.quantity,
                    unit_price=Money(line.unit_price.amount, original.currency),
                    notes=f"مرتجع - {request.reason}",
                )
                return_order.add_line(pline)

            repo.save(return_order)
            uow.commit()

        return ApiResponse(
            success=True,
            message="تم إنشاء مرتجع أمر الشراء بنجاح",
            data={
                'id': str(return_order.id.value),
                'status': 'draft',
                'reason': request.reason,
            },
        )
    except Exception as e:
        logger.error(f"Error returning purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
