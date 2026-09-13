# api_routers/purchasing_returns_router.py
"""
Purchase Returns API Router - واجهة برمجة إرجاع المشتريات

✅ جديد: دعم كامل لدورة حياة إرجاع المشتريات
✅ جديد: 13 endpoint شامل
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from core.application.purchasing.commands import (
    CreatePurchaseReturnCommand,
    SubmitPurchaseReturnCommand,
    ApprovePurchaseReturnCommand,
    RejectPurchaseReturnCommand,
    ShipPurchaseReturnCommand,
    ReceiveBySupplierCommand,
    CompletePurchaseReturnCommand,
    CancelPurchaseReturnCommand,
    PurchaseReturnItemCommand,
)

from core.application.purchasing.handlers import (
    CreatePurchaseReturnHandler,
    SubmitPurchaseReturnHandler,
    ApprovePurchaseReturnHandler,
    RejectPurchaseReturnHandler,
    ShipPurchaseReturnHandler,
    ReceiveBySupplierHandler,
    CompletePurchaseReturnHandler,
    CancelPurchaseReturnHandler,
)

from core.domain.purchasing.interfaces import IPurchaseReturnRepository
from core.infrastructure.db.postgres.purchase_return_repository import PostgresPurchaseReturnRepository
from core.infrastructure.db.uow import DatabaseUnitOfWorkFactory


router = APIRouter(prefix="/api/purchasing/returns", tags=["Purchase Returns"])


def get_return_repo() -> IPurchaseReturnRepository:
    """الحصول على مستودع إرجاع المشتريات"""
    uow = DatabaseUnitOfWorkFactory.get_uow()
    return PostgresPurchaseReturnRepository(uow)


# ==================== CRUD Operations ====================

@router.get("/", response_model=List[dict])
async def list_purchase_returns(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """قائمة إرجاعات المشتريات مع فلترة اختيارية"""
    repo = get_return_repo()
    
    try:
        if status:
            returns = repo.list_by_status(status, limit, offset)
        elif supplier_id:
            returns = repo.list_by_supplier(supplier_id, limit, offset)
        else:
            returns = repo.list_all(limit, offset)
        
        return [r.to_dict() for r in returns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{return_id}", response_model=dict)
async def get_purchase_return(return_id: str):
    """الحصول على تفاصيل إرجاع مشتريات محدد"""
    repo = get_return_repo()
    
    purchase_return = repo.get_by_id(return_id)
    if not purchase_return:
        raise HTTPException(status_code=404, detail="Purchase Return not found")
    
    return purchase_return.to_dict()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_purchase_return(return_data: dict):
    """إنشاء إرجاع مشتريات جديد"""
    repo = get_return_repo()
    
    try:
        # تحويل البيانات إلى Command
        lines_data = return_data.pop("lines", [])
        lines = [
            PurchaseReturnItemCommand(
                product_code=line["product_code"],
                product_name=line["product_name"],
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line["unit_price"])),
                reason=line.get("reason", ""),
                condition=line.get("condition", "good"),
                batch_number=line.get("batch_number"),
                serial_numbers=line.get("serial_numbers", []),
                expiry_date=datetime.fromisoformat(line["expiry_date"]) if line.get("expiry_date") else None,
                discount_percent=Decimal(str(line.get("discount_percent", "0"))),
                discount_amount=Decimal(str(line.get("discount_amount", "0"))),
                tax_rate=Decimal(str(line.get("tax_rate", "0"))),
            )
            for line in lines_data
        ]
        
        command = CreatePurchaseReturnCommand(
            purchase_order_id=return_data["purchase_order_id"],
            purchase_order_number=return_data["purchase_order_number"],
            supplier_id=return_data["supplier_id"],
            supplier_name=return_data["supplier_name"],
            site_id=return_data.get("site_id"),
            site_name=return_data.get("site_name"),
            warehouse_id=return_data.get("warehouse_id"),
            currency=return_data.get("currency", "USD"),
            notes=return_data.get("notes", ""),
            reason=return_data.get("reason", ""),
            shipping_method=return_data.get("shipping_method"),
            lines=lines,
            created_by=return_data.get("created_by", "system"),
        )
        
        handler = CreatePurchaseReturnHandler(repo)
        purchase_return = handler.handle(command)
        
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Workflow Operations ====================

@router.post("/{return_id}/submit", response_model=dict)
async def submit_purchase_return(return_id: str, user: dict = None):
    """تقديم إرجاع المشتريات للموافقة"""
    repo = get_return_repo()
    
    command = SubmitPurchaseReturnCommand(
        return_id=return_id,
        submitted_by=user.get("user_id", "system") if user else "system",
    )
    
    handler = SubmitPurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/approve", response_model=dict)
async def approve_purchase_return(return_id: str, user: dict = None):
    """الموافقة على إرجاع المشتريات"""
    repo = get_return_repo()
    
    command = ApprovePurchaseReturnCommand(
        return_id=return_id,
        approved_by=user.get("user_id", "system") if user else "system",
    )
    
    handler = ApprovePurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/reject", response_model=dict)
async def reject_purchase_return(return_id: str, reason: str, user: dict = None):
    """رفض إرجاع المشتريات"""
    repo = get_return_repo()
    
    command = RejectPurchaseReturnCommand(
        return_id=return_id,
        rejected_by=user.get("user_id", "system") if user else "system",
        reason=reason,
    )
    
    handler = RejectPurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/ship", response_model=dict)
async def ship_purchase_return(return_id: str, shipping_data: dict, user: dict = None):
    """شحن إرجاع المشتريات للمورد"""
    repo = get_return_repo()
    
    command = ShipPurchaseReturnCommand(
        return_id=return_id,
        shipped_by=user.get("user_id", "system") if user else "system",
        shipping_method=shipping_data.get("shipping_method"),
        tracking_number=shipping_data.get("tracking_number"),
    )
    
    handler = ShipPurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/receive", response_model=dict)
async def receive_by_supplier(return_id: str, user: dict = None):
    """تأكيد استلام المورد للإرجاع"""
    repo = get_return_repo()
    
    command = ReceiveBySupplierCommand(
        return_id=return_id,
        received_by=user.get("user_id", "system") if user else "system",
    )
    
    handler = ReceiveBySupplierHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/complete", response_model=dict)
async def complete_purchase_return(return_id: str, auto_create_debit_note: bool = True, user: dict = None):
    """إكمال إرجاع المشتريات وإنشاء Debit Note"""
    repo = get_return_repo()
    
    command = CompletePurchaseReturnCommand(
        return_id=return_id,
        completed_by=user.get("user_id", "system") if user else "system",
        auto_create_debit_note=auto_create_debit_note,
    )
    
    handler = CompletePurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_id}/cancel", response_model=dict)
async def cancel_purchase_return(return_id: str, reason: str, user: dict = None):
    """إلغاء إرجاع المشتريات"""
    repo = get_return_repo()
    
    command = CancelPurchaseReturnCommand(
        return_id=return_id,
        cancelled_by=user.get("user_id", "system") if user else "system",
        reason=reason,
    )
    
    handler = CancelPurchaseReturnHandler(repo)
    try:
        purchase_return = handler.handle(command)
        return purchase_return.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
