# api_routers/sales_cycle/quotations_router.py
"""
Sales Quotations API Router - عروض الأسعار
"""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.sales_cycle.dtos import (
    CreateQuotationRequest,
    UpdateQuotationRequest,
    RejectQuotationRequest,
    SalesLineRequest,
)
from api_routers.sales_cycle.utils import (
    item_totals,
    document_totals,
    next_document_number,
    get_customer_info,
    get_product_info,
)
from api_routers.sales_cycle.service import create_order
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["sales-quotations"])

PERM = {
    "create": "sales.create_quotation",
    "update": "sales.update_quotation",
    "convert": "sales.convert_quotation",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _serialize_quotation(row, items=None) -> dict:
    data = {
        "id": row["id"],
        "quotation_number": row["quotation_number"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "currency": row["currency"],
        "issue_date": row["issue_date"].isoformat() if row.get("issue_date") else None,
        "expiry_date": row["expiry_date"].isoformat() if row.get("expiry_date") else None,
        "status": row["status"],
        "global_discount_percent": float(row["global_discount_percent"] or 0),
        "global_discount_amount": float(row["global_discount_amount"] or 0),
        "subtotal": float(row["subtotal"] or 0),
        "total_discount": float(row["total_discount"] or 0),
        "amount_after_discount": float(row["amount_after_discount"] or 0),
        "total_tax": float(row["total_tax"] or 0),
        "grand_total": float(row["grand_total"] or 0),
        "billing_address": row.get("billing_address"),
        "shipping_address": row.get("shipping_address"),
        "notes": row.get("notes"),
        "internal_notes": row.get("internal_notes"),
        "sent_date": row["sent_date"].isoformat() if row.get("sent_date") else None,
        "accepted_date": row["accepted_date"].isoformat() if row.get("accepted_date") else None,
        "rejected_date": row["rejected_date"].isoformat() if row.get("rejected_date") else None,
        "converted_date": row["converted_date"].isoformat() if row.get("converted_date") else None,
        "order_id": row.get("order_id"),
        "branch_id": row.get("branch_id"),
        "created_by": row.get("created_by"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if items is not None:
        data["items"] = items
    return data


def _serialize_item(row) -> dict:
    return {
        "id": row["id"],
        "product_id": str(row["product_id"]),
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "quantity": float(row["quantity"]),
        "unit_price": float(row["unit_price"]),
        "discount_percent": float(row["discount_percent"] or 0),
        "tax_percent": float(row["tax_percent"] or 0),
        "unit": row["unit"],
        "notes": row["notes"],
        "subtotal": float(row["subtotal"] or 0),
        "discount_amount": float(row["discount_amount"] or 0),
        "amount_after_discount": float(row["amount_after_discount"] or 0),
        "tax_amount": float(row["tax_amount"] or 0),
        "total": float(row["total"] or 0),
    }


def _get_quotation(uow, quotation_id: str):
    row = uow.session.execute(
        text("SELECT * FROM sales_quotations WHERE id = :id"),
        {"id": quotation_id},
    ).mappings().first()
    if not row:
        return None
    items = uow.session.execute(
        text("SELECT * FROM quotation_items WHERE quotation_id = :qid ORDER BY id"),
        {"qid": quotation_id},
    ).mappings().all()
    return row, [_serialize_item(i) for i in items]


def _build_lines(uow, lines: list[SalesLineRequest]) -> list[dict]:
    serialized = []
    for raw in lines:
        info = get_product_info(uow, raw.product_id)
        if not info:
            raise ValueError(f"المنتج {raw.product_id} غير موجود")
        quantity = float(raw.quantity)
        unit_price = float(raw.unit_price if raw.unit_price is not None else info["unit_price"])
        tax_percent = float(raw.tax_percent if raw.tax_percent is not None else info["tax_rate"])
        discount_percent = float(raw.discount_percent)
        totals = item_totals(quantity, unit_price, discount_percent, tax_percent)
        serialized.append({
            "product_id": str(raw.product_id),
            "product_code": info["code"],
            "product_name": info["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_percent": discount_percent,
            "tax_percent": tax_percent,
            "unit": raw.unit or info.get("unit") or "pcs",
            "notes": raw.notes or "",
            **totals,
        })
    return serialized


@router.post("/api/sales/quotes", response_model=ApiResponse)
async def create_quotation(request: CreateQuotationRequest,
                           current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["create"])
    try:
        with bootstrap.uow() as uow:
            customer = get_customer_info(uow, request.customer_id) \
                if request.customer_id else None
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود",
                                   errors=["العميل غير موجود"])

            currency = request.currency or customer.get("currency") or "USD"
            lines = _build_lines(uow, request.lines)

            doc_totals = document_totals(
                lines,
                global_discount_amount=request.global_discount_amount,
            )
            if request.global_discount_percent:
                doc_totals["total_discount"] = float(doc_totals["subtotal"]) * \
                    float(request.global_discount_percent) / 100
                doc_totals["amount_after_discount"] = \
                    float(doc_totals["subtotal"]) - float(doc_totals["total_discount"])
                doc_totals["grand_total"] = \
                    float(doc_totals["amount_after_discount"]) + float(doc_totals["total_tax"])

            quotation_id = str(uuid4())
            quotation_number = next_document_number(
                uow, "QT", "sales_quotations", "quotation_number"
            )

            uow.session.execute(
                text("""
                    INSERT INTO sales_quotations (
                        id, quotation_number, customer_id, customer_name, currency,
                        issue_date, expiry_date, status,
                        global_discount_percent, global_discount_amount,
                        subtotal, total_discount, amount_after_discount, total_tax,
                        grand_total, billing_address, shipping_address,
                        notes, internal_notes, branch_id, created_by
                    ) VALUES (
                        :id, :quotation_number, :customer_id, :customer_name, :currency,
                        :issue_date, :expiry_date, 'draft',
                        :gdp, :gda, :subtotal, :total_discount, :amount_after_discount,
                        :total_tax, :grand_total, CAST(:billing_address AS jsonb),
                        CAST(:shipping_address AS jsonb), :notes, :internal_notes, :branch_id,
                        :created_by
                    )
                """),
                {
                    "id": quotation_id,
                    "quotation_number": quotation_number,
                    "customer_id": str(request.customer_id),
                    "customer_name": customer.get("name") or request.customer_name or "",
                    "currency": currency,
                    "issue_date": request.issue_date or datetime.now().date(),
                    "expiry_date": request.expiry_date,
                    "gdp": float(request.global_discount_percent or 0),
                    "gda": float(request.global_discount_amount or 0),
                    "subtotal": float(doc_totals["subtotal"]),
                    "total_discount": float(doc_totals["total_discount"]),
                    "amount_after_discount": float(doc_totals["amount_after_discount"]),
                    "total_tax": float(doc_totals["total_tax"]),
                    "grand_total": float(doc_totals["grand_total"]),
                    "billing_address": json.dumps(request.billing_address,
                                                  ensure_ascii=False) if request.billing_address else None,
                    "shipping_address": json.dumps(request.shipping_address,
                                                   ensure_ascii=False) if request.shipping_address else None,
                    "notes": request.notes,
                    "internal_notes": request.internal_notes,
                    "branch_id": request.branch_id,
                    "created_by": current_user.get("username", "system"),
                },
            )

            for line in lines:
                uow.session.execute(
                    text("""
                        INSERT INTO quotation_items (
                            id, quotation_id, product_id, product_code, product_name,
                            quantity, unit_price, discount_percent, tax_percent, unit,
                            notes, subtotal, discount_amount, amount_after_discount,
                            tax_amount, total
                        ) VALUES (
                            :id, :qid, :product_id, :product_code, :product_name,
                            :quantity, :unit_price, :discount_percent, :tax_percent, :unit,
                            :notes, :subtotal, :discount_amount, :amount_after_discount,
                            :tax_amount, :total
                        )
                    """),
                    {
                        "id": str(uuid4()),
                        "qid": quotation_id,
                        "product_id": line["product_id"],
                        "product_code": line["product_code"],
                        "product_name": line["product_name"],
                        "quantity": line["quantity"],
                        "unit_price": line["unit_price"],
                        "discount_percent": line["discount_percent"],
                        "tax_percent": line["tax_percent"],
                        "unit": line["unit"],
                        "notes": line["notes"],
                        "subtotal": float(line["subtotal"]),
                        "discount_amount": float(line["discount_amount"]),
                        "amount_after_discount": float(line["amount_after_discount"]),
                        "tax_amount": float(line["tax_amount"]),
                        "total": float(line["total"]),
                    },
                )

            uow.commit()
            return ApiResponse(success=True, message="تم إنشاء عرض السعر بنجاح",
                               data={"id": quotation_id,
                                     "quotation_number": quotation_number})
    except Exception as e:
        logger.error(f"Error creating quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/quotes", response_model=ApiResponse)
async def list_quotations(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            where = []
            params: dict = {}
            if customer_id:
                where.append("customer_id = :customer_id")
                params["customer_id"] = customer_id
            if status:
                where.append("status = :status")
                params["status"] = status
            if from_date:
                where.append("issue_date >= :from_date")
                params["from_date"] = from_date
            if to_date:
                where.append("issue_date <= :to_date")
                params["to_date"] = to_date
            if q:
                where.append(
                    "(customer_name ILIKE :q OR quotation_number ILIKE :q)"
                )
                params["q"] = f"%{q}%"

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            total = uow.session.execute(
                text(f"SELECT COUNT(*) AS c FROM sales_quotations{where_sql}"),
                params,
            ).mappings().first()["c"]

            params["skip"] = skip
            params["limit"] = limit
            rows = uow.session.execute(
                text(f"""
                    SELECT * FROM sales_quotations{where_sql}
                    ORDER BY created_at DESC LIMIT :limit OFFSET :skip
                """),
                params,
            ).mappings().all()

            return ApiResponse(success=True, message="تم جلب عروض الأسعار",
                               data={"items": [_serialize_quotation(r) for r in rows],
                                     "total": total, "skip": skip, "limit": limit})
    except Exception as e:
        logger.error(f"Error listing quotations: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/quotes/statistics", response_model=ApiResponse)
async def get_statistics(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            total = uow.session.execute(
                text("SELECT COUNT(*) AS c FROM sales_quotations")
            ).mappings().first()["c"]

            by_status_rows = uow.session.execute(
                text("SELECT status, COUNT(*) AS c, COALESCE(SUM(grand_total), 0) AS v "
                     "FROM sales_quotations GROUP BY status")
            ).mappings().all()

            by_status = {r["status"]: {"count": r["c"], "value": float(r["v"])}
                         for r in by_status_rows}

            accepted = by_status.get("accepted", {}).get("count", 0)
            converted = by_status.get("converted", {}).get("count", 0)
            conversion_rate = (converted / accepted * 100) if accepted else 0

            total_value = uow.session.execute(
                text("SELECT COALESCE(SUM(grand_total), 0) AS v FROM sales_quotations")
            ).mappings().first()["v"]

            return ApiResponse(
                success=True,
                data={"total": total, "by_status": by_status,
                      "total_value": float(total_value),
                      "conversion_rate": round(conversion_rate, 2)},
            )
    except Exception as e:
        logger.error(f"Error getting quotation statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/quotes/{quotation_id}", response_model=ApiResponse)
async def get_quotation(quotation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            found = _get_quotation(uow, quotation_id)
            if not found:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            row, items = found
            return ApiResponse(success=True, data=_serialize_quotation(row, items))
    except Exception as e:
        logger.error(f"Error getting quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.patch("/api/sales/quotes/{quotation_id}", response_model=ApiResponse)
async def update_quotation(quotation_id: str, request: UpdateQuotationRequest,
                           current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        with bootstrap.uow() as uow:
            found = _get_quotation(uow, quotation_id)
            if not found:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            row, _ = found
            if row["status"] not in ("draft", "sent", "viewed"):
                return ApiResponse(success=False,
                                   message="لا يمكن تعديل عرض السعر في الحالة الحالية")

            sets, params = ["updated_at = NOW()"], {"id": quotation_id}
            if request.customer_name is not None:
                sets.append("customer_name = :customer_name")
                params["customer_name"] = request.customer_name
            if request.expiry_date is not None:
                sets.append("expiry_date = :expiry_date")
                params["expiry_date"] = request.expiry_date
            if request.notes is not None:
                sets.append("notes = :notes")
                params["notes"] = request.notes
            if request.internal_notes is not None:
                sets.append("internal_notes = :internal_notes")
                params["internal_notes"] = request.internal_notes
            if request.billing_address is not None:
                sets.append("billing_address = CAST(:billing_address AS jsonb)")
                params["billing_address"] = json.dumps(request.billing_address,
                                                       ensure_ascii=False)
            if request.shipping_address is not None:
                sets.append("shipping_address = CAST(:shipping_address AS jsonb)")
                params["shipping_address"] = json.dumps(request.shipping_address,
                                                        ensure_ascii=False)

            if request.global_discount_amount is not None:
                sets.append("global_discount_amount = :gda")
                params["gda"] = float(request.global_discount_amount)
            if request.global_discount_percent is not None:
                sets.append("global_discount_percent = :gdp")
                params["gdp"] = float(request.global_discount_percent)

            if request.lines is not None:
                uow.session.execute(
                    text("DELETE FROM quotation_items WHERE quotation_id = :qid"),
                    {"qid": quotation_id},
                )
                lines = _build_lines(uow, request.lines)
                current_subtotal = float(row["subtotal"] or 0)
                current_tax = float(row["total_tax"] or 0)
                current_disc = float(row["total_discount"] or 0)
                for line in lines:
                    uow.session.execute(
                        text("""
                            INSERT INTO quotation_items (
                                id, quotation_id, product_id, product_code, product_name,
                                quantity, unit_price, discount_percent, tax_percent, unit,
                                notes, subtotal, discount_amount, amount_after_discount,
                                tax_amount, total
                            ) VALUES (
                                :id, :qid, :product_id, :product_code, :product_name,
                                :quantity, :unit_price, :discount_percent, :tax_percent, :unit,
                                :notes, :subtotal, :discount_amount, :amount_after_discount,
                                :tax_amount, :total
                            )
                        """),
                        {
                            "id": str(uuid4()),
                            "qid": quotation_id,
                            "product_id": line["product_id"],
                            "product_code": line["product_code"],
                            "product_name": line["product_name"],
                            "quantity": line["quantity"],
                            "unit_price": line["unit_price"],
                            "discount_percent": line["discount_percent"],
                            "tax_percent": line["tax_percent"],
                            "unit": line["unit"],
                            "notes": line["notes"],
                            "subtotal": float(line["subtotal"]),
                            "discount_amount": float(line["discount_amount"]),
                            "amount_after_discount": float(line["amount_after_discount"]),
                            "tax_amount": float(line["tax_amount"]),
                            "total": float(line["total"]),
                        },
                    )
                new_totals = document_totals(lines)
                gdp = float(request.global_discount_percent
                            if request.global_discount_percent is not None
                            else row.get("global_discount_percent") or 0)
                gda = float(request.global_discount_amount
                            if request.global_discount_amount is not None
                            else row.get("global_discount_amount") or 0)
                if gdp:
                    gda = float(new_totals["subtotal"]) * gdp / 100
                sets.append("subtotal = :subtotal")
                params["subtotal"] = float(new_totals["subtotal"])
                sets.append("total_discount = :total_discount")
                params["total_discount"] = float(gda)
                sets.append("amount_after_discount = :amount_after_discount")
                params["amount_after_discount"] = float(new_totals["subtotal"]) - gda
                sets.append("total_tax = :total_tax")
                params["total_tax"] = float(new_totals["total_tax"])
                sets.append("grand_total = :grand_total")
                params["grand_total"] = (float(new_totals["subtotal"]) - gda +
                                         float(new_totals["total_tax"]))

            uow.session.execute(
                text(f"UPDATE sales_quotations SET {', '.join(sets)} WHERE id = :id"),
                params,
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث عرض السعر بنجاح")
    except Exception as e:
        logger.error(f"Error updating quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/quotes/{quotation_id}/send", response_model=ApiResponse)
async def send_quotation(quotation_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_quotations WHERE id = :id"),
                {"id": quotation_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            if row["status"] not in ("draft", "viewed"):
                return ApiResponse(success=False,
                                   message="لا يمكن إرسال عرض السعر في الحالة الحالية")
            uow.session.execute(
                text("UPDATE sales_quotations SET status = 'sent', sent_date = NOW(), "
                     "updated_at = NOW() WHERE id = :id"),
                {"id": quotation_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم إرسال عرض السعر بنجاح")
    except Exception as e:
        logger.error(f"Error sending quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/quotes/{quotation_id}/accept", response_model=ApiResponse)
async def accept_quotation(quotation_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_quotations WHERE id = :id"),
                {"id": quotation_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            if row["status"] not in ("sent", "viewed"):
                return ApiResponse(success=False,
                                   message="لا يمكن قبول عرض السعر قبل إرساله")
            uow.session.execute(
                text("UPDATE sales_quotations SET status = 'accepted', accepted_date = NOW(), "
                     "updated_at = NOW() WHERE id = :id"),
                {"id": quotation_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم قبول عرض السعر بنجاح")
    except Exception as e:
        logger.error(f"Error accepting quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/quotes/{quotation_id}/reject", response_model=ApiResponse)
async def reject_quotation(quotation_id: str, request: RejectQuotationRequest,
                           current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        reason = (request.reason or "").strip() or "رفض من قبل العميل"
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_quotations WHERE id = :id"),
                {"id": quotation_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            uow.session.execute(
                text("UPDATE sales_quotations SET status = 'rejected', rejected_date = NOW(), "
                     "notes = COALESCE(NULLIF(:reason, ''), notes), updated_at = NOW() "
                     "WHERE id = :id"),
                {"id": quotation_id, "reason": reason},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم رفض عرض السعر")
    except Exception as e:
        logger.error(f"Error rejecting quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/quotes/{quotation_id}/convert", response_model=ApiResponse)
async def convert_to_order(quotation_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["convert"])
    try:
        with bootstrap.uow() as uow:
            found = _get_quotation(uow, quotation_id)
            if not found:
                return ApiResponse(success=False, message="عرض السعر غير موجود")
            row, items = found
            if row["status"] != "accepted":
                return ApiResponse(success=False,
                                   message="يجب قبول عرض السعر قبل تحويله لأمر بيع")

            lines = [{
                "product_id": it["product_id"],
                "quantity": it["quantity"],
                "unit_price": it["unit_price"],
                "discount_percent": it["discount_percent"],
                "tax_percent": it["tax_percent"],
                "unit": it["unit"],
                "notes": it["notes"],
            } for it in items]

            order = create_order(
                uow,
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                currency=row["currency"],
                created_by=current_user.get("username", "system"),
                lines=lines,
                quotation_id=quotation_id,
                priority="normal",
                global_discount_percent=row.get("global_discount_percent") or 0,
                global_discount_amount=row.get("global_discount_amount") or 0,
                billing_address=row.get("billing_address"),
                shipping_address=row.get("shipping_address"),
                notes=row.get("notes"),
                branch_id=row.get("branch_id"),
            )

            uow.session.execute(
                text("UPDATE sales_quotations SET status = 'converted', "
                     "converted_date = NOW(), order_id = :order_id, updated_at = NOW() "
                     "WHERE id = :id"),
                {"order_id": order["id"], "id": quotation_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تحويل عرض السعر لأمر بيع بنجاح",
                               data={"order_id": order["id"],
                                     "order_number": order["order_number"]})
    except Exception as e:
        logger.error(f"Error converting quotation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])