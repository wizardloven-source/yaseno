from fastapi import APIRouter, Query, Depends, status, HTTPException
from typing import Optional
from datetime import date
from decimal import Decimal

from api_routers.shared import (
    bootstrap, logger, ApiResponse,
    CreateCustomerRequest, CreateBranchRequest,
    get_current_user, filter_fields,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["customers"])


# =============================================================================
# 5. CUSTOMERS
# =============================================================================

@router.get("/api/customers", response_model=ApiResponse)
async def list_customers(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.customers
            
            if status_filter:
                customers = repo.list_by_status(status_filter, limit=limit)
            else:
                customers = repo.list_all(limit=limit, offset=offset)
            
            result = []
            for customer in customers:
                result.append({
                    'id': str(customer.id) if hasattr(customer, 'id') else None,
                    'code': str(customer.code) if hasattr(customer, 'code') else '',
                    'name': customer.name if hasattr(customer, 'name') else '',
                    'status': customer.status.value if hasattr(customer, 'status') else 'active',
                    'email': customer.contact_info.email if hasattr(customer, 'contact_info') else None,
                    'phone': customer.contact_info.phone if hasattr(customer, 'contact_info') else None,
                    'credit_limit': float(customer.credit_limit) if hasattr(customer, 'credit_limit') else 0,
                    'currency': customer.currency if hasattr(customer, 'currency') else 'USD',
                })
            
            return ApiResponse(
                success=True,
                message="تم جلب العملاء بنجاح",
                data={'items': result, 'total': len(result)}
            )
    except Exception as e:
        logger.error(f"Error listing customers: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/customers", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(request: CreateCustomerRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("customers.create_customer"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        from core.domain.customers.entities import Customer
        from core.domain.customers.value_objects import CustomerCode, ContactInfo, Address
        
        with bootstrap.uow() as uow:
            existing = uow.customers.get_by_code(CustomerCode(request.code))
            if existing:
                return ApiResponse(success=False, message=f"كود العميل '{request.code}' مستخدم مسبقاً", errors=[f"كود العميل '{request.code}' مستخدم مسبقاً"])
        
        customer = Customer.create(
            code=CustomerCode(request.code),
            name=request.name,
            contact_info=ContactInfo(
                email=request.email,
                phone=request.phone,
                mobile=request.mobile
            ),
            address=Address(
                street=request.street,
                city=request.city,
                country=request.country
            ),
            tax_number=request.tax_number,
            credit_limit=request.credit_limit,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"]
        )
        
        with bootstrap.uow() as uow:
            repo = uow.customers
            repo.save(customer)
            uow.commit()
        
        return ApiResponse(
            success=True,
            message="تم إنشاء العميل بنجاح",
            data={'id': str(customer.id), 'code': str(customer.code), 'name': customer.name}
        )
    except Exception as e:
        logger.error(f"Error creating customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/customers/aging", response_model=ApiResponse)
async def customer_aging_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        as_of = as_of_date or date.today()
        with bootstrap.uow() as uow:
            rows = uow.session.execute(text(
                "SELECT i.customer_id AS cid, COALESCE(c.name, '') AS name, "
                "COALESCE(SUM(i.total_amount), 0) AS invoiced, "
                "COALESCE((SELECT SUM(p.amount) FROM payments p "
                "          WHERE p.customer_id = i.customer_id AND p.payment_type = 'receive' "
                "            AND p.status NOT IN ('cancelled','rejected')), 0) AS paid "
                "FROM invoices i LEFT JOIN customers c ON c.id::text = i.customer_id "
                "WHERE i.status = 'posted' "
                "GROUP BY i.customer_id, c.name"
            )).mappings().all()

            items = []
            for r in rows:
                invoiced = Decimal(r['invoiced'])
                paid = Decimal(r['paid'])
                if invoiced - paid <= 0:
                    continue
                inv_rows = uow.session.execute(text(
                    "SELECT invoice_date, total_amount FROM invoices "
                    "WHERE customer_id = :cid AND status = 'posted' "
                    "ORDER BY invoice_date"
                ), {"cid": r['cid']}).mappings().all()

                remaining = [Decimal(str(i['total_amount'])) for i in inv_rows]
                to_allocate = paid
                idx = 0
                while to_allocate > 0 and idx < len(remaining):
                    if remaining[idx] > 0:
                        take = min(remaining[idx], to_allocate)
                        remaining[idx] -= take
                        to_allocate -= take
                    idx += 1

                cur_b = Decimal('0'); d30 = Decimal('0'); d60 = Decimal('0'); d90 = Decimal('0')
                for inv, rem in zip(inv_rows, remaining):
                    if rem <= 0:
                        continue
                    days = (as_of - inv['invoice_date'].date()).days
                    if days <= 30:
                        cur_b += rem
                    elif days <= 60:
                        d30 += rem
                    elif days <= 90:
                        d60 += rem
                    else:
                        d90 += rem

                items.append({
                    'customer_id': r['cid'],
                    'name': r['name'],
                    'current': float(cur_b),
                    'd30': float(d30),
                    'd60': float(d60),
                    'd90': float(d90),
                    'total': float(cur_b + d30 + d60 + d90),
                })
            return ApiResponse(success=True, message="تم جلب تقرير أعمار العملاء بنجاح",
                               data={'as_of': as_of.isoformat(), 'items': items})
    except Exception as e:
        logger.error(f"Error getting customer aging report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.put("/api/customers/{customer_id}", response_model=ApiResponse)
async def update_customer(customer_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("customers.update_customer"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        data = filter_fields(request, [
            "name", "email", "phone", "status",
        ])
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            if 'name' in data:
                customer.name = data['name']
            if 'email' in data or 'phone' in data:
                from core.domain.customers.value_objects import ContactInfo
                customer.contact_info = ContactInfo(
                    email=data.get('email', customer.contact_info.email),
                    phone=data.get('phone', customer.contact_info.phone),
                    mobile=customer.contact_info.mobile,
                )
            if 'status' in data:
                from core.domain.shared.value_objects import DomainStatus
                customer.status = DomainStatus(data['status'])
            customer.updated_by = current_user["username"]
            repo.save(customer)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث العميل بنجاح")
    except Exception as e:
        logger.error(f"Error updating customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.delete("/api/customers/{customer_id}", response_model=ApiResponse)
async def delete_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("customers.delete_customer"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
    try:
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            repo.delete(customer_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف العميل بنجاح")
    except Exception as e:
        logger.error(f"Error deleting customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/customers/{customer_id}/status", response_model=ApiResponse)
async def change_customer_status(customer_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, ["status"])
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            from core.domain.shared.value_objects import DomainStatus
            customer.status = DomainStatus(data.get('status', 'active'))
            customer.updated_by = current_user["username"]
            repo.save(customer)
            uow.commit()
            return ApiResponse(success=True, message="تم تغيير حالة العميل بنجاح")
    except Exception as e:
        logger.error(f"Error changing customer status: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/customers/{customer_id}/statement", response_model=ApiResponse)
async def customer_statement(
    customer_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            customer = uow.session.execute(text(
                "SELECT id, code, name FROM customers WHERE id::text = :cid"
            ), {"cid": customer_id}).mappings().first()
            if customer is None:
                return ApiResponse(success=False, message="العميل غير موجود")

            inv_rows = uow.session.execute(text(
                "SELECT number, invoice_date, status, total_amount FROM invoices "
                "WHERE customer_id = :cid AND invoice_date::date <= :to ORDER BY invoice_date"
            ), {"cid": customer_id, "to": to_date}).mappings().all()

            pay_rows = uow.session.execute(text(
                "SELECT code, payment_date, amount, status FROM payments "
                "WHERE customer_id = :cid AND payment_type = 'receive' AND payment_date::date <= :to "
                "ORDER BY payment_date"
            ), {"cid": customer_id, "to": to_date}).mappings().all()

            items = []
            for inv in inv_rows:
                if inv["status"] == "cancelled":
                    items.append({"date": inv["invoice_date"], "type": "cancel",
                                  "description": f"إلغاء فاتورة {inv['number']}",
                                  "debit": 0.0, "credit": float(inv["total_amount"]), "reference": inv["number"]})
                elif inv["status"] == "posted":
                    if inv["total_amount"] > 0:
                        items.append({"date": inv["invoice_date"], "type": "invoice",
                                      "description": f"فاتورة {inv['number']}",
                                      "debit": float(inv["total_amount"]), "credit": 0.0, "reference": inv["number"]})
                    else:
                        items.append({"date": inv["invoice_date"], "type": "return",
                                      "description": f"مرتجع فاتورة {inv['number']}",
                                      "debit": 0.0, "credit": abs(float(inv["total_amount"])), "reference": inv["number"]})
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

            return ApiResponse(success=True, message="تم جلب كشف حساب العميل بنجاح",
                               data={
                                   "customer_id": customer_id,
                                   "customer_name": customer["name"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": result_items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting customer statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/customers/{customer_id}/branches", response_model=ApiResponse)
async def create_customer_branch(
    customer_id: str,
    request: CreateBranchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import CreateBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateBranchCommand(
            code=request.code,
            name=request.name,
            customer_id=customer_id,
            customer_name=request.customer_name,
            customer_code=request.customer_code,
            street=request.street,
            city=request.city,
            country=request.country,
            postal_code=request.postal_code,
            email=request.email,
            phone=request.phone,
            mobile=request.mobile,
            contact_person=request.contact_person,
            latitude=request.latitude,
            longitude=request.longitude,
            tax_number=request.tax_number,
            is_default=request.is_default,
            notes=request.notes,
            working_hours=request.working_hours,
            branch_type=request.branch_type,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating customer branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
