# api_routers/suppliers.py
"""
YAseen ERP - Suppliers Router
"""

from decimal import Decimal
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query, Depends, status, HTTPException
from starlette.status import HTTP_201_CREATED

from api_routers.shared import (
    bootstrap, logger, ApiResponse, CreateSupplierRequest, get_current_user,
    filter_fields,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["suppliers"])


@router.get("/api/suppliers", response_model=ApiResponse)
async def list_suppliers(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            from core.domain.suppliers.value_objects import SupplierStatus
            suppliers = repo.list_all(
                status=SupplierStatus(status_filter) if status_filter else None,
                limit=limit,
                offset=offset,
            )
            result = []
            for s in suppliers:
                result.append({
                    'id': str(s.id.value),
                    'code': str(s.code),
                    'name': s.name,
                    'status': s.status.value if hasattr(s.status, 'value') else str(s.status),
                    'email': s.contact_info.email if hasattr(s, 'contact_info') else None,
                    'phone': s.contact_info.phone if hasattr(s, 'contact_info') else None,
                    'credit_limit': float(s.credit_limit) if hasattr(s, 'credit_limit') else 0,
                    'currency': s.currency if hasattr(s, 'currency') else 'USD',
                })
            return ApiResponse(success=True, message="تم جلب الموردين بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing suppliers: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/suppliers", response_model=ApiResponse, status_code=HTTP_201_CREATED)
async def create_supplier(request: CreateSupplierRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("suppliers.create_supplier"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.domain.suppliers.entities import Supplier
        from core.domain.suppliers.value_objects import SupplierCode, ContactInfo, Address

        supplier = Supplier.create(
            code=SupplierCode(request.code),
            name=request.name,
            contact_info=ContactInfo(email=request.email, phone=request.phone, mobile=request.mobile),
            address=Address(street=request.street, city=request.city, country=request.country),
            tax_number=request.tax_number,
            credit_limit=request.credit_limit,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.suppliers.save(supplier)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء المورد بنجاح",
                           data={'id': str(supplier.id.value), 'code': str(supplier.code), 'name': supplier.name})
    except Exception as e:
        logger.error(f"Error creating supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.suppliers.value_objects import SupplierId
        with bootstrap.uow() as uow:
            supplier = uow.suppliers.get_by_id(SupplierId.from_string(supplier_id))
            if not supplier:
                return ApiResponse(success=False, message="المورد غير موجود")
            data = {
                'id': str(supplier.id.value),
                'code': str(supplier.code),
                'name': supplier.name,
                'status': supplier.status.value if hasattr(supplier.status, 'value') else str(supplier.status),
                'email': supplier.contact_info.email if hasattr(supplier, 'contact_info') else None,
                'phone': supplier.contact_info.phone if hasattr(supplier, 'contact_info') else None,
                'tax_number': supplier.tax_number,
                'credit_limit': float(supplier.credit_limit) if hasattr(supplier, 'credit_limit') else 0,
                'currency': supplier.currency if hasattr(supplier, 'currency') else 'USD',
                'notes': supplier.notes,
                'version': supplier.version,
            }
            return ApiResponse(success=True, message="تم جلب المورد بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/suppliers/aging", response_model=ApiResponse)
async def supplier_aging_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        as_of = as_of_date or date.today()
        with bootstrap.uow() as uow:
            rows = uow.session.execute(text(
                "SELECT po.supplier_id AS sid, COALESCE(s.name, '') AS name, "
                "COALESCE(SUM(po.total_amount), 0) AS ordered, "
                "COALESCE((SELECT SUM(p.amount) FROM payments p "
                "          WHERE p.supplier_id = po.supplier_id AND p.payment_type = 'pay' "
                "            AND p.status NOT IN ('cancelled','rejected')), 0) AS paid "
                "FROM purchase_orders po LEFT JOIN suppliers s ON s.id::text = po.supplier_id "
                "WHERE po.status IN ('posted','partially_received','fully_received') "
                "GROUP BY po.supplier_id, s.name"
            )).mappings().all()

            items = []
            for r in rows:
                ordered = Decimal(r['ordered'])
                paid = Decimal(r['paid'])
                if ordered - paid <= 0:
                    continue
                po_rows = uow.session.execute(text(
                    "SELECT order_date, total_amount FROM purchase_orders "
                    "WHERE supplier_id = :sid AND status IN ('posted','partially_received','fully_received') "
                    "ORDER BY order_date"
                ), {"sid": r['sid']}).mappings().all()

                remaining = [Decimal(str(i['total_amount'])) for i in po_rows]
                to_allocate = paid
                idx = 0
                while to_allocate > 0 and idx < len(remaining):
                    if remaining[idx] > 0:
                        take = min(remaining[idx], to_allocate)
                        remaining[idx] -= take
                        to_allocate -= take
                    idx += 1

                cur_b = Decimal('0'); d30 = Decimal('0'); d60 = Decimal('0'); d90 = Decimal('0')
                for po, rem in zip(po_rows, remaining):
                    if rem <= 0:
                        continue
                    days = (as_of - po['order_date'].date()).days
                    if days <= 30:
                        cur_b += rem
                    elif days <= 60:
                        d30 += rem
                    elif days <= 90:
                        d60 += rem
                    else:
                        d90 += rem

                items.append({
                    'supplier_id': r['sid'],
                    'name': r['name'],
                    'current': float(cur_b),
                    'd30': float(d30),
                    'd60': float(d60),
                    'd90': float(d90),
                    'total': float(cur_b + d30 + d60 + d90),
                })
            return ApiResponse(success=True, message="تم جلب تقرير أعمار الموردين بنجاح",
                               data={'as_of': as_of.isoformat(), 'items': items})
    except Exception as e:
        logger.error(f"Error getting supplier aging report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def update_supplier(supplier_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("suppliers.update_supplier"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        data = filter_fields(request, [
            "name", "email", "phone",
        ])
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            supplier = repo.get_by_id(supplier_id) if hasattr(repo, 'get_by_id') else None
            if not supplier:
                return ApiResponse(success=False, message="المورد غير موجود")
            if 'name' in data:
                supplier.name = data['name']
            if 'email' in data or 'phone' in data:
                from core.domain.suppliers.value_objects import ContactInfo
                supplier.contact_info = ContactInfo(
                    email=data.get('email', supplier.contact_info.email),
                    phone=data.get('phone', supplier.contact_info.phone),
                    mobile=supplier.contact_info.mobile,
                )
            supplier.updated_by = current_user["username"]
            repo.save(supplier)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المورد بنجاح")
    except Exception as e:
        logger.error(f"Error updating supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("suppliers.delete_supplier"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            repo.delete(supplier_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المورد بنجاح")
    except Exception as e:
        logger.error(f"Error deleting supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/suppliers/{supplier_id}/statement", response_model=ApiResponse)
async def supplier_statement(
    supplier_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            supplier = uow.session.execute(text(
                "SELECT id, code, name FROM suppliers WHERE id::text = :sid"
            ), {"sid": supplier_id}).mappings().first()
            if supplier is None:
                return ApiResponse(success=False, message="المورد غير موجود")

            po_rows = uow.session.execute(text(
                "SELECT number, order_date, status, total_amount FROM purchase_orders "
                "WHERE supplier_id = :sid AND order_date::date <= :to ORDER BY order_date"
            ), {"sid": supplier_id, "to": to_date}).mappings().all()

            pay_rows = uow.session.execute(text(
                "SELECT code, payment_date, amount, status FROM payments "
                "WHERE supplier_id = :sid AND payment_type = 'pay' AND payment_date::date <= :to "
                "ORDER BY payment_date"
            ), {"sid": supplier_id, "to": to_date}).mappings().all()

            items = []
            for po in po_rows:
                if po["status"] == "cancelled":
                    items.append({"date": po["order_date"], "type": "cancel",
                                  "description": f"إلغاء أمر شراء {po['number']}",
                                  "debit": 0.0, "credit": float(po["total_amount"]), "reference": po["number"]})
                else:
                    items.append({"date": po["order_date"], "type": "purchase_order",
                                  "description": f"أمر شراء {po['number']}",
                                  "debit": float(po["total_amount"]), "credit": 0.0, "reference": po["number"]})
            for pay in pay_rows:
                if pay["status"] not in ("cancelled", "rejected"):
                    items.append({"date": pay["payment_date"], "type": "payment",
                                  "description": f"دفعة {pay['code']}",
                                  "debit": 0.0, "credit": float(pay["amount"]), "reference": pay["code"]})

            items.sort(key=lambda x: x["date"])
            opening = sum((Decimal(str(i["debit"])) - Decimal(str(i["credit"]))) for i in items
                          if from_date and i["date"] < from_date)
            filtered = [i for i in items if not from_date or i["date"] >= from_date]

            result_items = []
            if from_date and opening != 0:
                result_items.append({"date": from_date, "type": "opening", "description": "رصيد افتتاحي",
                                     "debit": 0.0, "credit": 0.0, "balance": float(opening)})
            running = opening
            for i in filtered:
                running += Decimal(str(i["debit"])) - Decimal(str(i["credit"]))
                result_items.append({**i, "balance": float(running)})

            return ApiResponse(success=True, message="تم جلب كشف حساب المورد بنجاح",
                               data={
                                   "supplier_id": supplier_id,
                                   "supplier_name": supplier["name"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": result_items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting supplier statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
