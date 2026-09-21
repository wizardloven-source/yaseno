# api_routers/pos/pos_service.py
"""
Point of Sale (POS) Service - خدمة نقطة البيع

تنفيذ المعاملة الذرية الواحدة لإيصال البيع:
  1. فحص عدم التكرار (idempotency key)
  2. حساب البنود وتسعيرها من بيانات المنتج (خادمياً)
  3. التحقق من كفاية المخزون
  4. حركات مخزون بيع (FIFO COGS)
  5. إنشاء الفاتورة وبنودها
  6. القيد المحاسبي عبر AccountingOrchestrator (commit=False)
  7. تحديث الصندوق بقفل Optimistic Locking (للتسديد النقدي)
  8. إدخال الإيصال وسجل المزامنة ثم commit واحد
"""
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, text, update

from api_routers.shared import bootstrap
from api_routers.sales_cycle.utils import next_document_number

from core.domain.inventory.services import (
    FIFOCostCalculator,
    InventoryValuationService,
    StockMovementService,
)
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    Money as InventoryMoney,
)
from core.application.accounting.orchestrator import JournalEntryRequest
from core.infrastructure.db.models.fund_model import FundModel, FundMovementModel
from core.infrastructure.db.models.settings_model import AccountingSettingsModel

logger = logging.getLogger(__name__)


class InsufficientStockError(Exception):
    def __init__(self, product_code: str, product_name: str, available: Any, requested: Any):
        self.product_code = product_code
        self.product_name = product_name
        self.available = float(available)
        self.requested = float(requested)
        super().__init__(
            f"المخزون غير كافٍ للمنتج {product_name}: متوفر {self.available} / مطلوب {self.requested}"
        )


# =============================================================================
# أدوات مساعدة
# =============================================================================

def _jsonb(value: Any) -> str:
    """تحويل قيمة إلى نص JSON (لـ CAST AS jsonb)"""
    if value is None:
        return "{}"
    return json.dumps(value, ensure_ascii=False, default=str)


def _get_accounting_settings(uow) -> Dict[str, str]:
    """قراءة إعدادات الحسابات (مع قيم افتراضية عند غيابها)"""
    try:
        s = uow.session.execute(
            select(AccountingSettingsModel).limit(1)
        ).scalar_one_or_none()
    except Exception:
        s = None
    if not s:
        return {
            "cash_account": "1010",
            "receivables_account": "1020",
            "revenue_account": "4010",
            "tax_payable_account": "2100",
            "cogs_account": "5010",
            "inventory_account": "1030",
        }
    return {
        "cash_account": s.cash_account or "1010",
        "receivables_account": s.receivables_account or "1020",
        "revenue_account": s.sales_revenue_account or "4010",
        "tax_payable_account": s.tax_account or "2100",
        "cogs_account": getattr(s, "cogs_account", None) or "5010",
        "inventory_account": getattr(s, "inventory_account", None) or "1030",
    }


def _load_stock_service(uow):
    """تحميل خدمات المخزون على مستودع حركات UoW الحالية"""
    repo = getattr(uow, "stock_movements", None)
    return StockMovementService(repo), InventoryValuationService(repo)


def _rebind_orchestrator(uow):
    """ربط AccountingOrchestrator ومحرك الترحيل بجلسة UoW الحالية"""
    orchestrator = bootstrap.container.resolve("accounting_orchestrator")
    engine = bootstrap.container.resolve("posting_engine")
    orchestrator._uow = uow
    engine._journal_repo = uow.journal_entries
    engine._ledger_repo = uow.ledger
    engine._period_repo = uow.periods
    engine._account_repo = uow.accounts
    engine._uow = uow
    return orchestrator, engine


def _get_or_create_walkin_customer(uow, created_by: str) -> Dict[str, Any]:
    """جلب أو إنشاء عميل النقدية الافتراضي (Walk-in)"""
    row = uow.session.execute(
        text(
            "SELECT id, name FROM customers "
            "WHERE code = 'WALKIN' AND is_deleted = false LIMIT 1"
        )
    ).mappings().first()
    if row:
        return {"id": str(row["id"]), "name": row["name"]}
    cid = str(uuid4())
    uow.session.execute(
        text("""
            INSERT INTO customers (
                id, code, name, status, is_deleted, is_active,
                country, credit_limit, currency,
                version, created_by, created_at, updated_by, updated_at
            ) VALUES (
                :id, 'WALKIN', 'عميل نقدي', 'active', false, true,
                'SY', 0, 'USD',
                1, :by, NOW(), :by, NOW()
            )
        """),
        {"id": cid, "by": created_by},
    )
    return {"id": cid, "name": "عميل نقدي"}


# =============================================================================
# حساب البنود والتسعير (خادمي)
# =============================================================================

def compute_pos_lines(
    uow,
    lines_data: List[Dict[str, Any]],
    currency: str,
    allow_discount: bool = False,
) -> List[Dict[str, Any]]:
    """حساب بنود الإيصال: السعر، الخصم، الضريبة، التكلفة (FIFO)، والمخزون المتاح"""
    codes = [str(l.get("product_code") or l.get("product_id")) for l in lines_data]
    products = uow.session.execute(
        text(
            "SELECT id, code, name, unit_price, tax_rate, stock_quantity "
            "FROM products WHERE code IN :codes AND is_active = true"
        ),
        {"codes": tuple(codes)},
    ).mappings().all()
    prod_map = {str(p["code"]): p for p in products}

    stock_service, valuation_service = _load_stock_service(uow)
    result = []

    for l in lines_data:
        code = str(l.get("product_code") or l.get("product_id"))
        p = prod_map.get(code)
        if not p:
            raise ValueError(f"المنتج {code} غير موجود أو غير نشط")

        qty = Decimal(str(l.get("quantity", 0)))
        unit_price = Decimal(str(p["unit_price"] or 0))
        gross = qty * unit_price

        disc_amount = Decimal(str(l.get("discount_amount", 0) or 0))
        disc_pct = Decimal(str(l.get("discount_percent", 0) or 0))
        if disc_amount <= 0 and disc_pct > 0 and allow_discount:
            disc_amount = gross * (disc_pct / Decimal(100))

        net = gross - disc_amount
        tax_rate = Decimal(str(p.get("tax_rate", 0) or 0))
        tax_amount = net * (tax_rate / Decimal(100))
        total = net + tax_amount

        entity = EntityId(str(p["id"]))
        try:
            movements = stock_service.get_movements(entity, limit=1000)
            layers = valuation_service._build_layers(movements)
            cogs, _ = FIFOCostCalculator.calculate_cogs(layers, qty, currency)
            unit_cost = cogs.amount / qty if qty > 0 else Decimal("0")
        except Exception:
            unit_cost = unit_price * Decimal("0.7")

        on_hand = stock_service.get_current_quantity(entity)

        result.append({
            "product_id": str(p["id"]),
            "product_code": str(p["code"]),
            "product_name": p["name"],
            "quantity": float(qty),
            "unit_price": float(unit_price),
            "discount_amount": float(disc_amount),
            "discount_percent": float(disc_pct) if allow_discount else 0.0,
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "subtotal": float(net),
            "total": float(total),
            "unit_cost": float(unit_cost),
            "cogs_amount": float(unit_cost * qty),
            "on_hand": float(on_hand),
        })

    return result


def check_stock(lines: List[Dict[str, Any]]) -> None:
    """رفع InsufficientStockError إذا كان المخزون غير كافٍ لأي بند"""
    for l in lines:
        if l["quantity"] > l["on_hand"] + 0.001:
            raise InsufficientStockError(l["product_code"], l["product_name"], l["on_hand"], l["quantity"])


# =============================================================================
# إنشاء إيصال البيع (معاملة ذرية واحدة)
# =============================================================================

def create_pos_receipt(
    uow,
    *,
    session_id: str,
    customer_id: Optional[str],
    currency: str,
    tender_type: str,
    lines_data: List[Dict[str, Any]],
    tenders: Optional[Dict[str, Decimal]],
    idempotency_key: Optional[str],
    client_reference: Optional[str],
    device_id: Optional[str],
    fund_id: Optional[str],
    notes: Optional[str],
    created_by: str,
) -> Dict[str, Any]:
    # 1. فحص عدم التكرار
    if idempotency_key:
        existing = uow.session.execute(
            text(
                "SELECT id, receipt_number, total_amount, invoice_id "
                "FROM pos_receipts WHERE idempotency_key = :k"
            ),
            {"k": idempotency_key},
        ).mappings().first()
        if existing:
            return {
                "success": True,
                "idempotent": True,
                "receipt_id": str(existing["id"]),
                "receipt_number": existing["receipt_number"],
                "invoice_id": existing["invoice_id"],
                "total_amount": float(existing["total_amount"]),
            }

    # 2. الجلسة مفتوحة
    if not session_id:
        raise ValueError("session_id مطلوب لعملية البيع")
    sess = uow.session.execute(
        text("SELECT * FROM pos_sessions WHERE id = :sid"),
        {"sid": session_id},
    ).mappings().first()
    if not sess:
        raise ValueError("الجلسة غير موجودة")
    if sess["status"] != "open":
        raise ValueError("الجلسة مغلقة أو ملغاة")

    # 3. العميل (عميل نقدي افتراضي عند عدم التحديد)
    if not customer_id:
        _walkin = _get_or_create_walkin_customer(uow, created_by)
        customer_id = _walkin["id"]
        customer_name = _walkin["name"]
    else:
        row = uow.session.execute(
            text("SELECT name FROM customers WHERE id = :c AND is_deleted = false LIMIT 1"),
            {"c": customer_id},
        ).mappings().first()
        if not row:
            raise ValueError("العميل غير موجود")
        customer_name = row["name"]

    # 4. حساب البنود والتحقق من المخزون
    computed_lines = compute_pos_lines(
        uow, lines_data, currency, allow_discount=(tender_type != "credit")
    )
    check_stock(computed_lines)

    subtotal = sum((Decimal(str(l["subtotal"])) for l in computed_lines), Decimal("0"))
    tax_amount = sum((Decimal(str(l["tax_amount"])) for l in computed_lines), Decimal("0"))
    discount_amount = sum((Decimal(str(l["discount_amount"])) for l in computed_lines), Decimal("0"))
    total_amount = subtotal + tax_amount
    if total_amount <= 0:
        raise ValueError("إجمالي الإيصال يجب أن يكون أكبر من صفر")

    # 5. توزيع وسائل الدفع
    tenders = tenders or {}
    cash_tendered = Decimal(str(tenders.get("cash", 0) or 0))
    card_tendered = Decimal(str(tenders.get("card", 0) or 0))
    credit_tendered = Decimal(str(tenders.get("credit", 0) or 0))
    if tender_type == "mixed":
        if abs(cash_tendered + card_tendered + credit_tendered - total_amount) > Decimal("0.01"):
            raise ValueError("المبلغ المستلم لا يطابق إجمالي الإيصال (دفع مختلط)")
    elif tender_type == "cash":
        cash_tendered = total_amount
    elif tender_type == "card":
        card_tendered = total_amount
    elif tender_type == "credit":
        credit_tendered = total_amount
    else:
        raise ValueError(f"نوع الدفع {tender_type} غير مدعوم")

    receipt_id = str(uuid4())
    receipt_number = next_document_number(uow, "POS", "pos_receipts", "receipt_number")

    # 6. حركات المخزون (بيع)
    stock_service, _ = _load_stock_service(uow)
    cogs_lines = []
    for l in computed_lines:
        entity = EntityId(l["product_id"])
        movement = stock_service.create_outbound_movement(
            entity=entity,
            quantity=Decimal(str(l["quantity"])),
            unit_cost=InventoryMoney(Decimal(str(l["unit_cost"])), currency),
            movement_type=StockMovementType.SALE,
            reference_type="pos_receipt",
            reference_id=receipt_id,
            notes=f"بيع نقطة بيع {receipt_number}",
            created_by=created_by,
        )
        new_qty = float(stock_service.get_current_quantity(entity))
        uow.session.execute(
            text("UPDATE products SET stock_quantity = :q WHERE id = :pid"),
            {"q": new_qty, "pid": l["product_id"]},
        )
        cogs_lines.append({
            "code": l["product_code"],
            "quantity": l["quantity"],
            "unit_cost": l["unit_cost"],
            "total_cost": l["cogs_amount"],
            "currency": currency,
            "movement_id": str(movement.id),
        })

    # 7. إنشاء الفاتورة وبنودها
    settings = _get_accounting_settings(uow)
    invoice_id = str(uuid4())
    invoice_number = next_document_number(uow, "INV", "invoices", "number")
    branch_id = sess["branch_id"]
    site_name = "نقطة البيع"
    if branch_id:
        site_row = uow.session.execute(
            text("SELECT name FROM sites WHERE id = :bid"),
            {"bid": branch_id},
        ).mappings().first()
        if site_row:
            site_name = site_row["name"]

    invoice_payment_type = {
        "cash": "cash",
        "card": "transfer",
        "credit": "credit",
        "mixed": "cash",
    }.get(tender_type, "cash")

    uow.session.execute(
        text("""
            INSERT INTO invoices (
                id, number, invoice_date, customer_id, customer_name,
                site_id, site_name, currency, payment_currency, payment_type,
                subtotal, tax_amount, total_amount, status, notes,
                created_by, created_at, version
            ) VALUES (
                :id, :number, :date, :cid, :cname,
                :site, :sitename, :curr, :curr, :ptype,
                :subtotal, :tax, :total, 'posted', :notes,
                :by, NOW(), 1
            )
        """),
        {
            "id": invoice_id, "number": invoice_number,
            "date": date.today(), "cid": customer_id, "cname": customer_name,
            "site": branch_id, "sitename": site_name,
            "curr": currency, "ptype": invoice_payment_type,
            "subtotal": float(subtotal), "tax": float(tax_amount), "total": float(total_amount),
            "notes": notes or "", "by": created_by,
        },
    )

    for idx, l in enumerate(computed_lines):
        uow.session.execute(
            text("""
                INSERT INTO invoice_lines (
                    id, invoice_id, product_code, product_name,
                    quantity, unit_price, total_amount, currency, line_order
                ) VALUES (
                    :id, :iid, :code, :name,
                    :qty, :price, :total, :curr, :order
                )
            """),
            {
                "id": str(uuid4()), "iid": invoice_id,
                "code": l["product_code"], "name": l["product_name"],
                "qty": l["quantity"], "price": l["unit_price"], "total": l["subtotal"],
                "curr": currency, "order": idx + 1,
            },
        )

    # 8. القيد المحاسبي عبر Orchestrator (بدون commit)
    journal_lines = []
    if cash_tendered > 0:
        journal_lines.append({
            "account_code": settings.get("cash_account", "1010"),
            "debit": float(cash_tendered), "currency": currency,
        })
    if card_tendered > 0:
        journal_lines.append({
            "account_code": "1040",
            "debit": float(card_tendered), "currency": currency,
        })
    if credit_tendered > 0:
        journal_lines.append({
            "account_code": settings.get("receivables_account", "1020"),
            "debit": float(credit_tendered), "currency": currency,
        })
    journal_lines.append({
        "account_code": settings.get("revenue_account", "4010"),
        "credit": float(subtotal), "currency": currency,
    })
    if tax_amount > 0:
        journal_lines.append({
            "account_code": settings.get("tax_payable_account", "2100"),
            "credit": float(tax_amount), "currency": currency,
        })
    for c in cogs_lines:
        journal_lines.append({
            "account_code": settings.get("cogs_account", "5010"),
            "debit": c["total_cost"], "currency": c["currency"],
        })
        journal_lines.append({
            "account_code": settings.get("inventory_account", "1030"),
            "credit": c["total_cost"], "currency": c["currency"],
        })

    orchestrator, _ = _rebind_orchestrator(uow)
    journal_request = JournalEntryRequest(
        entity_type="pos_receipt",
        entity_id=receipt_id,
        description=f"مبيعات نقطة البيع {receipt_number}",
        lines=journal_lines,
        date=datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc),
        transaction_type="sales",
        created_by=created_by,
        reference_number=receipt_number,
        metadata={
            "receipt_number": receipt_number,
            "receipt_id": receipt_id,
            "customer_id": customer_id,
            "session_id": session_id,
            "tender_type": tender_type,
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
        },
    )
    result = orchestrator.create_journal_entry(
        request=journal_request, posted_by=created_by, commit=False
    )
    if not result.success:
        raise ValueError(f"فشل ترحيل القيد المحاسبي: {result.message}")
    journal_entry_id = result.journal_entry_id

    # 9. تحديث الصندوق (استحقاق الريال الصندوق: جزء النقد فقط) مع قفل تفاؤلي
    if cash_tendered > 0 and fund_id:
        fund = uow.session.execute(
            select(FundModel)
            .where(FundModel.id == fund_id)
            .where(FundModel.status == "active")
            .with_for_update()
        ).scalar_one_or_none()
        if not fund:
            raise ValueError("الصندوق غير موجود أو غير نشط")
        old_bal = float(fund.balance or 0)
        new_bal = old_bal + float(cash_tendered)
        new_ver = fund.version + 1
        res = uow.session.execute(
            update(FundModel)
            .where(FundModel.id == fund.id, FundModel.version == fund.version)
            .values(balance=new_bal, version=new_ver, updated_at=datetime.now(timezone.utc))
        )
        if res.rowcount == 0:
            raise ValueError("تعارض في تحديث الصندوق - حاول مرة أخرى")
        uow.session.add(FundMovementModel(
            id=uuid4(),
            fund_id=fund.id,
            movement_type="deposit",
            amount=float(cash_tendered),
            currency=fund.currency,
            balance_before=old_bal,
            balance_after=new_bal,
            reason="إيداع من نقطة البيع",
            reference_id=receipt_id,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        ))

    # 10. ربط القيد بالفاتورة
    uow.session.execute(
        text("UPDATE invoices SET journal_entry_id = :jid WHERE id = :iid"),
        {"jid": journal_entry_id, "iid": invoice_id},
    )

    # 11. إدخال الإيصال
    uow.session.execute(
        text("""
            INSERT INTO pos_receipts (
                id, receipt_number, session_id, terminal_id, device_id,
                customer_id, customer_name, invoice_id, journal_entry_id, fund_id,
                tender_type, currency,
                subtotal, discount_amount, tax_amount, total_amount,
                line_items, tenders, totals,
                status, idempotency_key, client_reference, synced_at, notes,
                company_id, created_by, created_at, updated_at
            ) VALUES (
                :id, :number, :sid, :terminal, :device,
                :cid, :cname, :iid, :jid, :fund,
                :tender, :curr,
                :subtotal, :disc, :tax, :total,
                CAST(:line_items AS jsonb), CAST(:tenders AS jsonb), CAST(:totals AS jsonb),
                'completed', :idem, :client_ref, NOW(), :notes,
                'default', :by, NOW(), NOW()
            )
        """),
        {
            "id": receipt_id, "number": receipt_number,
            "sid": session_id, "terminal": sess["terminal_id"], "device": device_id,
            "cid": customer_id, "cname": customer_name,
            "iid": invoice_id, "jid": journal_entry_id, "fund": fund_id,
            "tender": tender_type, "curr": currency,
            "subtotal": float(subtotal), "disc": float(discount_amount),
            "tax": float(tax_amount), "total": float(total_amount),
            "line_items": _jsonb(computed_lines),
            "tenders": _jsonb({
                "cash": float(cash_tendered),
                "card": float(card_tendered),
                "credit": float(credit_tendered),
            }),
            "totals": _jsonb({
                "subtotal": float(subtotal),
                "tax": float(tax_amount),
                "total": float(total_amount),
            }),
            "idem": idempotency_key, "client_ref": client_reference,
            "notes": notes or "", "by": created_by,
        },
    )

    # 12. سجل المزامنة (audit)
    uow.session.execute(
        text("""
            INSERT INTO sync_operations (
                id, device_id, entity, entity_id, operation, payload, status,
                idempotency_key, client_reference, server_processed_at, created_at, company_id
            ) VALUES (
                :id, :device, 'pos_receipt', :eid, 'pos.receipt',
                CAST(:payload AS jsonb), 'synced',
                :idem, :cref, NOW(), NOW(), 'default'
            )
        """),
        {
            "id": str(uuid4()),
            "device": device_id or "",
            "eid": receipt_id,
            "payload": _jsonb({"receipt_id": receipt_id, "receipt_number": receipt_number}),
            "idem": idempotency_key,
            "cref": client_reference,
        },
    )

    return {
        "success": True,
        "receipt_id": receipt_id,
        "receipt_number": receipt_number,
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "total_amount": float(total_amount),
        "journal_entry_id": journal_entry_id,
    }


# =============================================================================
# عكس الإيصال (إرجاع / إلغاء)
# =============================================================================

def reverse_pos_receipt(
    uow,
    receipt_id: str,
    reason: Optional[str],
    refund_tender: str,
    created_by: str,
    *,
    return_line_specs: Optional[List[Dict[str, Any]]] = None,
    is_void: bool = False,
) -> Dict[str, Any]:
    """عكس إيصال: إرجاع جزئي/كامل أو إلغاء (void) مع قيد عكسي ومخزون وصندوق"""
    r = uow.session.execute(
        text("SELECT * FROM pos_receipts WHERE id = :rid"),
        {"rid": receipt_id},
    ).mappings().first()
    if not r:
        raise ValueError("الإيصال غير موجود")
    if r["status"] not in ("completed",):
        raise ValueError("لا يمكن عكس إيصال غير مكتمل")

    try:
        raw_lines = r["line_items"]
        if isinstance(raw_lines, str):
            original_lines = json.loads(raw_lines) if raw_lines else []
        else:
            original_lines = raw_lines or []
    except Exception:
        original_lines = []

    if is_void or not return_line_specs:
        return_specs = [{
            "product_code": l["product_code"],
            "product_id": l["product_id"],
            "quantity": l["quantity"],
            "subtotal": l["subtotal"],
            "tax_amount": l["tax_amount"],
            "unit_cost": l["unit_cost"],
        } for l in original_lines]
    else:
        specs_by_code = {str(s.get("product_code")): s for s in return_line_specs}
        return_specs = []
        for l in original_lines:
            spec = specs_by_code.get(str(l["product_code"]))
            if not spec:
                continue
            ret_qty = min(float(spec.get("quantity", 0)), l["quantity"])
            if ret_qty <= 0:
                continue
            ratio = ret_qty / l["quantity"] if l["quantity"] else 0
            return_specs.append({
                "product_code": l["product_code"],
                "product_id": l["product_id"],
                "quantity": ret_qty,
                "subtotal": float(l["subtotal"] * ratio),
                "tax_amount": float(l["tax_amount"] * ratio),
                "unit_cost": float(l["unit_cost"]),
            })

    if not return_specs:
        raise ValueError("لا توجد بنود للإرجاع")

    total_refund = sum((Decimal(str(s["subtotal"])) + Decimal(str(s["tax_amount"])) for s in return_specs), Decimal("0"))
    total_tax = sum((Decimal(str(s["tax_amount"])) for s in return_specs), Decimal("0"))
    total_revenue = total_refund - total_tax

    return_id = str(uuid4())
    return_number = next_document_number(uow, "POSRET", "pos_returns", "return_number")

    # حركات المخزون (مرتجع)
    stock_service, _ = _load_stock_service(uow)
    for s in return_specs:
        entity = EntityId(s["product_id"])
        stock_service.create_inbound_movement(
            entity=entity,
            quantity=Decimal(str(s["quantity"])),
            unit_cost=InventoryMoney(Decimal(str(s["unit_cost"])), r["currency"]),
            movement_type=StockMovementType.RETURN,
            reference_type="pos_return",
            reference_id=return_id,
            notes=f"{'إلغاء' if is_void else 'إرجاع'} نقطة بيع {r['receipt_number']}",
            created_by=created_by,
        )
        new_qty = float(stock_service.get_current_quantity(entity))
        uow.session.execute(
            text("UPDATE products SET stock_quantity = :q WHERE id = :pid"),
            {"q": new_qty, "pid": s["product_id"]},
        )

    # القيد العكسي
    settings = _get_accounting_settings(uow)
    journal_lines = []
    if refund_tender == "cash":
        journal_lines.append({"account_code": settings.get("cash_account", "1010"), "credit": float(total_refund), "currency": r["currency"]})
    elif refund_tender == "card":
        journal_lines.append({"account_code": "1040", "credit": float(total_refund), "currency": r["currency"]})
    else:
        journal_lines.append({"account_code": settings.get("receivables_account", "1020"), "credit": float(total_refund), "currency": r["currency"]})
    journal_lines.append({"account_code": settings.get("revenue_account", "4010"), "debit": float(total_revenue), "currency": r["currency"]})
    if total_tax > 0:
        journal_lines.append({"account_code": settings.get("tax_payable_account", "2100"), "debit": float(total_tax), "currency": r["currency"]})
    for s in return_specs:
        cost = Decimal(str(s["unit_cost"])) * Decimal(str(s["quantity"]))
        journal_lines.append({"account_code": settings.get("inventory_account", "1030"), "debit": float(cost), "currency": r["currency"]})
        journal_lines.append({"account_code": settings.get("cogs_account", "5010"), "credit": float(cost), "currency": r["currency"]})

    orchestrator, _ = _rebind_orchestrator(uow)
    journal_request = JournalEntryRequest(
        entity_type="pos_return",
        entity_id=return_id,
        description=f"{'إلغاء' if is_void else 'إرجاع'} عملية نقطة بيع {r['receipt_number']}",
        lines=journal_lines,
        date=datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc),
        transaction_type="sales_return",
        created_by=created_by,
        reference_number=return_number,
        metadata={
            "return_number": return_number,
            "receipt_id": receipt_id,
            "is_void": is_void,
            "reason": reason,
        },
    )
    result = orchestrator.create_journal_entry(
        request=journal_request, posted_by=created_by, commit=False
    )
    if not result.success:
        raise ValueError(f"فشل ترحيل القيد العكسي: {result.message}")

    # سحب من الصندوق عند الاسترداد النقدي
    if refund_tender == "cash" and r["fund_id"]:
        fund = uow.session.execute(
            select(FundModel)
            .where(FundModel.id == r["fund_id"])
            .where(FundModel.status == "active")
            .with_for_update()
        ).scalar_one_or_none()
        if fund:
            old_bal = float(fund.balance or 0)
            new_bal = old_bal - float(total_refund)
            new_ver = fund.version + 1
            res = uow.session.execute(
                update(FundModel)
                .where(FundModel.id == fund.id, FundModel.version == fund.version)
                .values(balance=new_bal, version=new_ver, updated_at=datetime.now(timezone.utc))
            )
            if res.rowcount == 0:
                raise ValueError("تعارض في تحديث الصندوق - حاول مرة أخرى")
            uow.session.add(FundMovementModel(
                id=uuid4(),
                fund_id=fund.id,
                movement_type="withdraw",
                amount=float(total_refund),
                currency=fund.currency,
                balance_before=old_bal,
                balance_after=new_bal,
                reason=f"{'إلغاء' if is_void else 'إرجاع'} من نقطة البيع",
                reference_id=return_id,
                created_by=created_by,
                created_at=datetime.now(timezone.utc),
            ))

    # إلغاء الفاتورة عند الاسترداد الكامل
    if is_void or (abs(float(r["total_amount"]) - float(total_refund)) < 0.01 and r["invoice_id"]):
        uow.session.execute(
            text("UPDATE invoices SET status = 'cancelled' WHERE id = :iid AND status = 'posted'"),
            {"iid": r["invoice_id"]},
        )

    # إدخال المرتجع
    uow.session.execute(
        text("""
            INSERT INTO pos_returns (
                id, return_number, receipt_id, customer_id, return_lines, reason,
                refund_tender, refund_amount, refund_currency,
                reversal_journal_entry_id, status,
                company_id, created_by, created_at, updated_at
            ) VALUES (
                :id, :rnum, :rid, :cid, CAST(:lines AS jsonb), :reason,
                :ftender, :famount, :curr,
                :jid, 'completed',
                'default', :by, NOW(), NOW()
            )
        """),
        {
            "id": return_id, "rnum": return_number,
            "rid": receipt_id, "cid": r["customer_id"],
            "lines": _jsonb(return_specs),
            "reason": reason or "",
            "ftender": refund_tender, "famount": float(total_refund),
            "curr": r["currency"], "jid": result.journal_entry_id,
            "by": created_by,
        },
    )

    # تحديث حالة الإيصال
    new_status = "voided" if is_void else "returned"
    uow.session.execute(
        text("UPDATE pos_receipts SET status = :st, updated_at = NOW() WHERE id = :rid"),
        {"st": new_status, "rid": receipt_id},
    )

    uow.session.execute(
        text("""
            INSERT INTO sync_operations (
                id, device_id, entity, entity_id, operation, payload, status,
                server_processed_at, created_at, company_id
            ) VALUES (
                :id, '', 'pos_return', :eid, 'pos.return',
                CAST(:payload AS jsonb), 'synced', NOW(), NOW(), 'default'
            )
        """),
        {
            "id": str(uuid4()),
            "eid": return_id,
            "payload": _jsonb({"return_id": return_id, "receipt_id": receipt_id}),
        },
    )

    return {
        "success": True,
        "return_id": return_id,
        "return_number": return_number,
        "refund_amount": float(total_refund),
        "journal_entry_id": result.journal_entry_id,
    }


# =============================================================================
# جلسات البيع
# =============================================================================

def open_pos_session(
    uow,
    *,
    opening_cash: Decimal,
    terminal_id: Optional[str],
    device_id: Optional[str],
    warehouse_id: Optional[str],
    branch_id: Optional[str],
    notes: Optional[str],
    created_by: str,
) -> Dict[str, Any]:
    existing = uow.session.execute(
        text("SELECT id, session_number FROM pos_sessions WHERE user_id = :uid AND status = 'open' LIMIT 1"),
        {"uid": created_by},
    ).mappings().first()
    if existing:
        raise ValueError(f"لديك جلسة مفتوحة بالفعل: {existing['session_number']}")

    sess_id = str(uuid4())
    sess_number = next_document_number(uow, "SESS", "pos_sessions", "session_number")

    uow.session.execute(
        text("""
            INSERT INTO pos_sessions (
                id, session_number, terminal_id, user_id,
                branch_id, warehouse_id, opening_cash, status, notes,
                company_id, created_by, opened_at, created_at, updated_at
            ) VALUES (
                :id, :num, :terminal, :uid,
                :branch, :wh, :opening, 'open', :notes,
                'default', :by, NOW(), NOW(), NOW()
            )
        """),
        {
            "id": sess_id, "num": sess_number,
            "terminal": terminal_id, "uid": created_by,
            "branch": branch_id, "wh": warehouse_id,
            "opening": float(opening_cash), "notes": notes or "",
            "by": created_by,
        },
    )

    if terminal_id or device_id:
        term_id = device_id or terminal_id
        uow.session.execute(
            text("""
                INSERT INTO pos_terminals (
                    id, device_id, terminal_name, default_warehouse_id,
                    branch_id, status, last_seen_at, company_id,
                    created_by, created_at, updated_at
                ) VALUES (
                    :id, :did, :tname, :wh, :branch, 'active', NOW(), 'default',
                    :by, NOW(), NOW()
                )
                ON CONFLICT (device_id) DO UPDATE SET
                    last_seen_at = NOW(), updated_at = NOW()
            """),
            {
                "id": str(uuid4()), "did": term_id,
                "tname": terminal_id or term_id,
                "wh": warehouse_id, "branch": branch_id, "by": created_by,
            },
        )

    return {
        "success": True,
        "session_id": sess_id,
        "session_number": sess_number,
        "opening_cash": float(opening_cash),
    }


def close_pos_session(
    uow,
    *,
    session_id: str,
    declared_cash: Decimal,
    tolerance: Decimal,
    notes: Optional[str],
    created_by: str,
    notify_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    sess = uow.session.execute(
        text("SELECT * FROM pos_sessions WHERE id = :sid"),
        {"sid": session_id},
    ).mappings().first()
    if not sess:
        raise ValueError("الجلسة غير موجودة")
    if sess["status"] != "open":
        raise ValueError("الجلسة مغلقة أو ملغاة")

    opening = Decimal(str(sess["opening_cash"] or 0))
    cash_sold = Decimal(str(
        uow.session.execute(
            text(
                "SELECT COALESCE(SUM((tenders->>'cash')::numeric), 0) c "
                "FROM pos_receipts WHERE session_id = :sid AND status IN ('completed', 'returned', 'voided')"
            ),
            {"sid": session_id},
        ).mappings().first()["c"] or 0
    ))
    cash_refunded = Decimal(str(
        uow.session.execute(
            text(
                "SELECT COALESCE(SUM(pr.refund_amount), 0) c "
                "FROM pos_returns pr JOIN pos_receipts rr ON pr.receipt_id = rr.id "
                "WHERE rr.session_id = :sid AND pr.refund_tender = 'cash' AND pr.status = 'completed'"
            ),
            {"sid": session_id},
        ).mappings().first()["c"] or 0
    ))

    expected = opening + cash_sold - cash_refunded
    declared = Decimal(str(declared_cash))
    shortage = expected - declared
    tol = Decimal(str(tolerance or 0))
    mismatch = abs(shortage) > tol

    uow.session.execute(
        text("""
            UPDATE pos_sessions SET
                status = 'closed',
                expected_cash = :ec,
                declared_cash = :dc,
                closing_cash = :dc,
                cash_shortage = :shortage,
                tolerance = :tol,
                notes = COALESCE(:notes, notes),
                closed_at = NOW(),
                updated_at = NOW()
            WHERE id = :sid
        """),
        {
            "ec": float(expected), "dc": float(declared),
            "shortage": float(shortage), "tol": float(tol),
            "notes": notes, "sid": session_id,
        },
    )

    if mismatch:
        recipient = notify_user_id or sess["user_id"]
        uow.session.execute(
            text("""
                INSERT INTO notifications (
                    id, user_id, title, message, notification_type, data, is_read, created_at
                ) VALUES (
                    :id, :uid, 'فرق الصندوق', :msg, 'pos', CAST(:data AS jsonb), false, NOW()
                )
            """),
            {
                "id": str(uuid4()),
                "uid": recipient,
                "msg": (
                    f"فرق الصندوق في جلسة {sess['session_number']}: "
                    f"متوقع {expected}، مُصرّح {declared}، فرق {shortage}"
                ),
                "data": _jsonb({
                    "session_id": session_id,
                    "expected": float(expected),
                    "declared": float(declared),
                    "shortage": float(shortage),
                    "tolerance": float(tol),
                }),
            },
        )

    return {
        "success": True,
        "session_id": session_id,
        "expected_cash": float(expected),
        "declared_cash": float(declared),
        "shortage": float(shortage),
        "mismatch": mismatch,
    }


def list_pos_sessions(uow, *, status: Optional[str] = None, terminal_id: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    where, params = [], {}
    if status:
        where.append("status = :st")
        params["st"] = status
    if terminal_id:
        where.append("terminal_id = :tid")
        params["tid"] = terminal_id
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = uow.session.execute(
        text(f"SELECT COUNT(*) c FROM pos_sessions{w}"), params
    ).mappings().first()["c"]
    params["skip"] = skip
    params["limit"] = limit
    rows = uow.session.execute(
        text(f"SELECT * FROM pos_sessions{w} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        params,
    ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "skip": skip, "limit": limit}


def get_pos_session(uow, session_id: str) -> Dict[str, Any]:
    r = uow.session.execute(
        text("SELECT * FROM pos_sessions WHERE id = :sid"), {"sid": session_id}
    ).mappings().first()
    if not r:
        raise ValueError("الجلسة غير موجودة")
    agg = uow.session.execute(
        text(
            "SELECT COUNT(*) c, COALESCE(SUM(total_amount), 0) t "
            "FROM pos_receipts WHERE session_id = :sid AND status = 'completed'"
        ),
        {"sid": session_id},
    ).mappings().first()
    return {
        "session": dict(r),
        "receipts_count": agg["c"],
        "total_sales": float(agg["t"]),
    }


def list_pos_receipts(uow, *, session_id: Optional[str] = None, customer_id: Optional[str] = None,
                      status: Optional[str] = None, q: Optional[str] = None,
                      skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    where, params = [], {}
    if session_id:
        where.append("session_id = :sid")
        params["sid"] = session_id
    if customer_id:
        where.append("customer_id = :cid")
        params["cid"] = customer_id
    if status:
        where.append("status = :st")
        params["st"] = status
    if q:
        where.append("(receipt_number ILIKE :q OR customer_name ILIKE :q)")
        params["q"] = f"%{q}%"
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = uow.session.execute(
        text(f"SELECT COUNT(*) c FROM pos_receipts{w}"), params
    ).mappings().first()["c"]
    params["skip"] = skip
    params["limit"] = limit
    rows = uow.session.execute(
        text(f"SELECT * FROM pos_receipts{w} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        params,
    ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "skip": skip, "limit": limit}


def get_pos_receipt(uow, receipt_id: str) -> Dict[str, Any]:
    r = uow.session.execute(
        text("SELECT * FROM pos_receipts WHERE id = :rid"), {"rid": receipt_id}
    ).mappings().first()
    if not r:
        raise ValueError("الإيصال غير موجود")
    return dict(r)


def list_sync_operations(uow, *, status: Optional[str] = None, device_id: Optional[str] = None,
                         skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    where, params = [], {}
    if status:
        where.append("status = :st")
        params["st"] = status
    if device_id:
        where.append("device_id = :did")
        params["did"] = device_id
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = uow.session.execute(
        text(f"SELECT COUNT(*) c FROM sync_operations{w}"), params
    ).mappings().first()["c"]
    params["skip"] = skip
    params["limit"] = limit
    rows = uow.session.execute(
        text(f"SELECT * FROM sync_operations{w} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        params,
    ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "skip": skip, "limit": limit}


# =============================================================================
# مزامنة الأجهزة (batch)
# =============================================================================

def sync_pos_receipts(uow, receipts: List[Dict[str, Any]], device_id: Optional[str], created_by: str) -> List[Dict[str, Any]]:
    """معالجة دفعة إيصالات من جهاز: لكل عنصر تحقق عدم التكرار أو راقع متعارض"""
    results = []
    for rec in receipts:
        idem = rec.get("idempotency_key") or (
            f"{device_id}:{rec.get('client_reference')}" if device_id else None
        )
        try:
            res = create_pos_receipt(
                uow,
                session_id=rec.get("session_id"),
                customer_id=rec.get("customer_id"),
                currency=rec.get("currency", "USD"),
                tender_type=rec["tender_type"],
                lines_data=rec.get("lines", []),
                tenders=rec.get("tenders"),
                idempotency_key=idem,
                client_reference=rec.get("client_reference"),
                device_id=device_id or rec.get("device_id"),
                fund_id=rec.get("fund_id"),
                notes=rec.get("notes"),
                created_by=created_by,
            )
            res["item_status"] = "synced"
            results.append(res)
        except InsufficientStockError as e:
            results.append({
                "item_status": "conflict",
                "conflict_code": "conflict_stock",
                "product_code": e.product_code,
                "product_name": e.product_name,
                "on_hand": e.available,
                "requested": e.requested,
            })
            uow.session.execute(
                text("""
                    INSERT INTO sync_operations (
                        id, device_id, entity, operation, payload, status,
                        conflict_code, idempotency_key, created_at, company_id
                    ) VALUES (
                        :id, :dev, 'pos_receipt', 'pos.receipt',
                        CAST(:payload AS jsonb), 'conflict', 'conflict_stock', :idem, NOW(), 'default'
                    )
                """),
                {
                    "id": str(uuid4()),
                    "dev": device_id or "",
                    "payload": _jsonb(rec),
                    "idem": idem,
                },
            )
        except Exception as e:
            results.append({"item_status": "failed", "error": str(e)})
            uow.session.execute(
                text("""
                    INSERT INTO sync_operations (
                        id, device_id, entity, operation, payload, status,
                        last_error, idempotency_key, created_at, company_id
                    ) VALUES (
                        :id, :dev, 'pos_receipt', 'pos.receipt',
                        CAST(:payload AS jsonb), 'failed', :err, :idem, NOW(), 'default'
                    )
                """),
                {
                    "id": str(uuid4()),
                    "dev": device_id or "",
                    "payload": _jsonb(rec),
                    "err": str(e)[:1000],
                    "idem": idem,
                },
            )
    return results


def retry_sync_operation(uow, operation_id: str, created_by: str) -> Dict[str, Any]:
    op = uow.session.execute(
        text("SELECT * FROM sync_operations WHERE id = :oid"), {"oid": operation_id}
    ).mappings().first()
    if not op:
        raise ValueError("عملية المزامنة غير موجودة")
    if op["status"] == "synced":
        return {"success": True, "message": "تمت المزامنة مسبقاً"}

    try:
        payload = json.loads(op["payload"]) if isinstance(op["payload"], str) else (op["payload"] or {})
    except Exception:
        payload = {}
    if not payload.get("lines"):
        raise ValueError("بيانات المزامنة فارغة")

    idem = op.get("idempotency_key") or (
        f"{op['device_id']}:{payload.get('client_reference')}" if op["device_id"] else None
    )
    try:
        res = create_pos_receipt(
            uow,
            session_id=payload.get("session_id"),
            customer_id=payload.get("customer_id"),
            currency=payload.get("currency", "USD"),
            tender_type=payload["tender_type"],
            lines_data=payload.get("lines", []),
            tenders=payload.get("tenders"),
            idempotency_key=idem,
            client_reference=payload.get("client_reference"),
            device_id=op["device_id"],
            fund_id=payload.get("fund_id"),
            notes=payload.get("notes"),
            created_by=created_by,
        )
        uow.session.execute(
            text("""
                UPDATE sync_operations SET
                    status = 'synced', conflict_code = NULL, last_error = NULL,
                    server_processed_at = NOW()
                WHERE id = :oid
            """),
            {"oid": operation_id},
        )
        return {"success": True, **res}
    except InsufficientStockError as e:
        uow.session.execute(
            text("""
                UPDATE sync_operations SET
                    status = 'conflict', conflict_code = 'conflict_stock',
                    last_error = :err, retry_count = retry_count + 1
                WHERE id = :oid
            """),
            {"oid": operation_id, "err": str(e)[:1000]},
        )
        return {"success": False, "conflict_code": "conflict_stock", "error": str(e)}
    except Exception as e:
        uow.session.execute(
            text("""
                UPDATE sync_operations SET
                    status = 'failed', last_error = :err, retry_count = retry_count + 1
                WHERE id = :oid
            """),
            {"oid": operation_id, "err": str(e)[:1000]},
        )
        return {"success": False, "error": str(e)}


def list_terminals(uow, *, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    where, params = [], {}
    if status:
        where.append("status = :st")
        params["st"] = status
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = uow.session.execute(
        text(f"SELECT COUNT(*) c FROM pos_terminals{w}"), params
    ).mappings().first()["c"]
    params["skip"] = skip
    params["limit"] = limit
    rows = uow.session.execute(
        text(f"SELECT * FROM pos_terminals{w} ORDER BY created_at DESC LIMIT :limit OFFSET :skip"),
        params,
    ).mappings().all()
    return {"items": [dict(r) for r in rows], "total": total, "skip": skip, "limit": limit}