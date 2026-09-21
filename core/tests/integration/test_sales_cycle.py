# core/tests/integration/test_sales_cycle.py
"""
M3.1 Advanced Sales Cycle - Live DB integration test
=====================================================

Covers the completed M3.1 remainder:
  1. Confirm order -> stock reserved (order_items.reserved_quantity > 0,
     sales_orders.reservation_status = 'reserved')
  2. Complete delivery -> auto draft invoice (delivery -> invoice factory),
     invoice_deliveries link, order_items.invoiced_qty, invoice_ids,
     reservation_status = 'completed'
  3. Post invoice -> balanced GL journal + single FIFO 'sale' stock movement
     (no double deduction vs the shipping dispatch)
  4. Cancel order -> reservation released

Run standalone (writes to the configured live database, cleans up after itself):

    python core/tests/integration/test_sales_cycle.py

It is intentionally NOT named with pytest `test_` functions so a normal
`pytest` collection run will not touch the live database.
"""

import asyncio
import sys
import traceback
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from api_routers.shared import bootstrap
from api_routers.sales_cycle.service import (
    create_order,
    set_auto_invoice_on_delivery,
)
from api_routers.sales_cycle.picking_service import (
    reserve_order_items,
    release_order_reservations,
    get_product_availability,
)
from api_routers.sales_cycle.deliveries_router import (
    create_delivery_record,
    complete_delivery,
)
from api_routers.sales_cycle.dtos import CompleteDeliveryRequest
from core.application.security.authorization import (
    UserContext,
    set_current_user_context,
    clear_current_user_context,
)
from core.application.invoicing.commands import PostInvoiceCommand
from core.domain.inventory.services import StockMovementService
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    Money as InventoryMoney,
)

USER = "smoke_m31_user"

RESULTS = []
CLEANUP = {
    "orders": [],
    "products": [],
    "movements": [],
    "invoices": [],
    "journal_entries": [],
    "deliveries": [],
}


def check(name, cond, extra=""):
    RESULTS.append((name, bool(cond)))
    mark = "OK  " if cond else "FAIL"
    print(f"[{mark}] {name} {extra}")


def q1(uow, sql, **params):
    return uow.session.execute(text(sql), params).mappings().first()


def _install_superuser_context():
    ctx = UserContext(
        user_id="smoke_m31",
        username=USER,
        roles={"admin"},
        permissions=set(),
        is_super_admin=True,
    )
    set_current_user_context(ctx)
    return ctx


ACCOUNTS = [
    ("1010", "الصندوق", "asset"),
    ("1020", "العملاء", "asset"),
    ("1030", "المخزون", "asset"),
    ("4010", "إيرادات المبيعات", "revenue"),
    ("5010", "تكلفة البضاعة المباعة", "expense"),
]


def ensure_accounts(uow):
    for code, name, atype in ACCOUNTS:
        uow.session.execute(
            text("""
                INSERT INTO accounts (id, code, name, account_type, is_active, currency,
                                      version, created_by, created_at, updated_at)
                VALUES (:id, :code, :name, :atype, true, 'USD', 1, 'm31_test', NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """),
            {"id": str(uuid4()), "code": code, "name": name, "atype": atype},
        )


def setup_fixtures(uow):
    ensure_accounts(uow)

    customer = q1(uow, "SELECT CAST(id AS TEXT) AS id, name FROM customers LIMIT 1")
    if not customer:
        raise RuntimeError("no customer available for the sales-cycle test")

    product_id = str(uuid4())
    code = f"M31-{uuid4().hex[:6].upper()}"
    uow.session.execute(
        text("""
            INSERT INTO products (id, code, name, unit_price, currency, tax_rate,
                                  purchase_price, wholesale_price, stock_quantity,
                                  min_stock, max_stock, base_unit,
                                  weight, weight_unit, length, width, height,
                                  is_active, is_featured, allow_backorder, batch_tracking,
                                  low_stock_alert, version, created_at, updated_at)
            VALUES (:id, :code, :name, 10, 'USD', 0,
                    5, 9, 0,
                    0, 0, 'pc',
                    0, 'kg', 0, 0, 0,
                    true, false, false, false,
                    false, 1, NOW(), NOW())
        """),
        {"id": product_id, "code": code, "name": "منتج اختبار دورة البيع"},
    )
    CLEANUP["products"].append(product_id)

    svc = StockMovementService(uow.stock_movements)
    svc.create_inbound_movement(
        entity=EntityId(product_id),
        quantity=Decimal("100"),
        unit_cost=InventoryMoney(Decimal("5"), "USD"),
        movement_type=StockMovementType.ADJUSTMENT_IN,
        reference_type="m31_seed",
        reference_id=str(uuid4()),
        notes="seed stock",
        created_by=USER,
    )
    uow.session.execute(
        text("UPDATE products SET stock_quantity = 100 WHERE id = :pid"),
        {"pid": product_id},
    )
    return customer["id"], customer["name"], product_id, code


def main():
    _install_superuser_context()

    # ------------------------------------------------------------------ #
    # 0) Schema + settings presence
    # ------------------------------------------------------------------ #
    with bootstrap.uow() as uow:
        so_cols = {r["column_name"] for r in uow.session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='sales_orders'")).mappings().all()}
        oi_cols = {r["column_name"] for r in uow.session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='order_items'")).mappings().all()}
        check("sales_orders has reservation_status", "reservation_status" in so_cols)
        check("sales_orders has invoice_ids", "invoice_ids" in so_cols)
        check("sales_orders has fully_delivered", "fully_delivered" in so_cols)
        check("order_items has picked_qty", "picked_qty" in oi_cols)
        check("order_items has invoiced_qty", "invoiced_qty" in oi_cols)
        check("invoice_deliveries table exists",
              bool(uow.session.execute(text(
                  "SELECT to_regclass('invoice_deliveries')")).scalar()))
        # enable the feature
        set_auto_invoice_on_delivery(uow, True)
        uow.commit()

    try:
        with bootstrap.uow() as uow:
            customer_id, customer_name, product_id, product_code = setup_fixtures(uow)

            # ---------------------------------------------------------- #
            # 1) Confirm + reserve
            # ---------------------------------------------------------- #
            order = create_order(
                uow,
                customer_id=customer_id,
                customer_name=customer_name,
                currency="USD",
                created_by=USER,
                lines=[{
                    "product_id": product_id,
                    "quantity": 2,
                    "unit_price": 10,
                    "discount_percent": 0,
                    "tax_percent": 0,
                    "unit": "pc",
                    "notes": "",
                }],
            )
            order_id = order["id"]
            CLEANUP["orders"].append(order_id)

            uow.session.execute(
                text("UPDATE sales_orders SET status='confirmed' WHERE id=:oid"),
                {"oid": order_id},
            )
            res = reserve_order_items(uow, order_id, USER)
            order_row = q1(uow, "SELECT reservation_status FROM sales_orders WHERE id=:oid",
                           oid=order_id)
            item_row = q1(uow, "SELECT reserved_quantity, picked_qty, invoiced_qty "
                               "FROM order_items WHERE order_id=:oid", oid=order_id)
            check("reserve_order_items reserved total = 2.0",
                  res["reserved_total"] == 2.0, str(res))
            check("order_items.reserved_quantity = 2",
                  float(item_row["reserved_quantity"] or 0) == 2.0,
                  str(item_row["reserved_quantity"]))
            check("sales_orders.reservation_status = reserved",
                  order_row["reservation_status"] == "reserved",
                  str(order_row["reservation_status"]))

            avail = get_product_availability(uow, product_id, exclude_order_id=order_id)
            check("availability excludes own reservation",
                  avail["available"] == 100.0 and avail["reserved"] == 0.0, str(avail))

            # ---------------------------------------------------------- #
            # 2) Create + complete delivery -> auto draft invoice
            # ---------------------------------------------------------- #
            delivery = create_delivery_record(
                uow, order_id=order_id,
                lines=[{"product_id": product_id, "quantity": 2}],
                created_by=USER,
            )
            delivery_id = delivery["id"]
            CLEANUP["deliveries"].append(delivery_id)
            uow.commit()

        # call the endpoint (runs in its own uow) to exercise the auto-invoice path
        result = asyncio.run(complete_delivery(
            delivery_id,
            CompleteDeliveryRequest(received_by="Tester", received_by_title="QA"),
            {"username": USER},
        ))
        check("complete_delivery succeeded", bool(result.success),
              getattr(result, "message", ""))

        with bootstrap.uow() as uow:
            delivered = q1(uow, "SELECT delivered_quantity, invoiced_qty, picked_qty "
                                "FROM order_items WHERE order_id=:oid", oid=order_id)
            ord_row = q1(uow, "SELECT invoice_id, invoice_ids, reservation_status, "
                              "fully_delivered, payment_status "
                              "FROM sales_orders WHERE id=:oid", oid=order_id)
            check("delivery marked delivered (qty=2)",
                  float(delivered["delivered_quantity"] or 0) == 2.0,
                  str(delivered["delivered_quantity"]))
            check("order.fully_delivered = true", bool(ord_row["fully_delivered"]))
            check("auto invoice linked on order", bool(ord_row["invoice_id"]),
                  str(ord_row["invoice_id"]))
            check("order_items.invoiced_qty = 2 after auto-invoice",
                  float(delivered["invoiced_qty"] or 0) == 2.0,
                  str(delivered["invoiced_qty"]))
            check("reservation_status = completed after full invoice",
                  ord_row["reservation_status"] == "completed",
                  str(ord_row["reservation_status"]))

            invoice_id = ord_row["invoice_id"]
            if invoice_id:
                invoice_id = str(invoice_id)
                CLEANUP["invoices"].append(invoice_id)
                inv = q1(uow, "SELECT status, total_amount FROM invoices WHERE id=:iid",
                         iid=invoice_id)
                check("draft invoice created with total 20",
                      inv is not None and inv["status"] == "draft"
                      and float(inv["total_amount"]) == 20.0,
                      str(dict(inv) if inv else None))
                link = q1(uow, "SELECT COUNT(*) AS c FROM invoice_deliveries "
                               "WHERE invoice_id=:iid AND delivery_id=:did",
                          iid=invoice_id, did=delivery_id)
                check("invoice_deliveries link exists", link["c"] == 1, str(link["c"]))
                inv_ids = q1(uow, "SELECT invoice_ids FROM sales_orders WHERE id=:oid",
                             oid=order_id)
                check("order invoice_ids jsonb contains invoice",
                      inv_ids["invoice_ids"] is not None
                      and invoice_id in str(inv_ids["invoice_ids"]),
                      str(inv_ids["invoice_ids"]))
            else:
                check("draft invoice created with total 20", False, "no invoice_id")
                check("invoice_deliveries link exists", False, "no invoice_id")
                check("order invoice_ids jsonb contains invoice", False, "no invoice_id")

        # ---------------------------------------------------------- #
        # 3) Post invoice -> balanced GL + single 'sale' movement
        # ---------------------------------------------------------- #
        if invoice_id:
            command_bus = bootstrap.container.resolve("command_bus")
            command_bus.dispatch(
                PostInvoiceCommand(invoice_id=invoice_id, posted_by=USER))

            with bootstrap.uow() as uow:
                inv = q1(uow, "SELECT status, journal_entry_id FROM invoices WHERE id=:iid",
                         iid=invoice_id)
                check("invoice posted", inv["status"] == "posted", str(inv["status"]))
                if inv["journal_entry_id"]:
                    CLEANUP["journal_entries"].append(str(inv["journal_entry_id"]))
                bal = q1(uow, """
                    SELECT COALESCE(SUM(debit_amount),0) AS d,
                           COALESCE(SUM(credit_amount),0) AS c
                    FROM journal_lines WHERE journal_entry_id=:je
                """, je=inv["journal_entry_id"])
                check("journal entry balanced (debit = credit > 0)",
                      Decimal(str(bal["d"])) == Decimal(str(bal["c"]))
                      and Decimal(str(bal["d"])) > 0, str(dict(bal)))

                mov = q1(uow, """
                    SELECT COUNT(*) AS c FROM stock_movements
                    WHERE reference_type='Invoice' AND reference_id=:iid
                      AND movement_type='sale'
                """, iid=invoice_id)
                check("exactly ONE FIFO sale movement for the invoice",
                      mov["c"] == 1, f"count={mov['c']}")

                prod = q1(uow, "SELECT stock_quantity FROM products WHERE id=:pid",
                          pid=product_id)
                check("stock decreased 100 -> 98 (no double deduction)",
                      float(prod["stock_quantity"]) == 98.0, str(prod["stock_quantity"]))

        # ---------------------------------------------------------- #
        # 4) Cancel flow -> reservation released
        # ---------------------------------------------------------- #
        with bootstrap.uow() as uow:
            order2 = create_order(
                uow, customer_id=customer_id, customer_name=customer_name,
                currency="USD", created_by=USER,
                lines=[{"product_id": product_id, "quantity": 1, "unit_price": 10,
                        "discount_percent": 0, "tax_percent": 0, "unit": "pc",
                        "notes": ""}],
            )
            oid2 = order2["id"]
            CLEANUP["orders"].append(oid2)
            uow.session.execute(
                text("UPDATE sales_orders SET status='confirmed' WHERE id=:oid"),
                {"oid": oid2},
            )
            reserve_order_items(uow, oid2, USER)
            released = release_order_reservations(uow, oid2)
            r2 = q1(uow, "SELECT reserved_quantity FROM order_items WHERE order_id=:oid",
                    oid=oid2)
            o2 = q1(uow, "SELECT reservation_status FROM sales_orders WHERE id=:oid",
                    oid=oid2)
            check("cancel releases reservation",
                  released == 1 and float(r2["reserved_quantity"] or 0) == 0,
                  f"released={released} reserved={r2['reserved_quantity']}")
            check("reservation_status = released",
                  o2["reservation_status"] == "released", str(o2["reservation_status"]))
            uow.commit()

    except Exception:
        traceback.print_exc()
        RESULTS.append(("unhandled exception", False))
    finally:
        _cleanup()
        clear_current_user_context()

    failed = [n for n, ok in RESULTS if not ok]
    print("=" * 60)
    print(f"RESULT: {len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("FAILED:", failed)
        return 1
    return 0


def _cleanup():
    try:
        with bootstrap.uow() as uow:
            invoice_ids = list(CLEANUP["invoices"])
            # catch any invoice linked to our orders (even if not tracked)
            for oid in CLEANUP["orders"]:
                rows = uow.session.execute(text(
                    "SELECT invoice_id FROM invoice_deliveries WHERE order_id=:o"),
                    {"o": oid}).mappings().all()
                invoice_ids += [str(r["invoice_id"]) for r in rows if r["invoice_id"]]
            invoice_ids = list(dict.fromkeys(invoice_ids))

            # journal entries linked to our invoices
            je_ids = list(CLEANUP["journal_entries"])
            for inv in invoice_ids:
                row = uow.session.execute(text(
                    "SELECT journal_entry_id FROM invoices WHERE CAST(id AS TEXT)=:i"),
                    {"i": inv}).mappings().first()
                if row and row["journal_entry_id"]:
                    je_ids.append(str(row["journal_entry_id"]))
            je_ids = list(dict.fromkeys(je_ids))

            for inv in invoice_ids:
                uow.session.execute(text(
                    "DELETE FROM payment_allocations WHERE CAST(invoice_id AS TEXT)=:i"),
                    {"i": inv})
                uow.session.execute(text(
                    "DELETE FROM invoice_deliveries WHERE invoice_id=:i"), {"i": inv})
                uow.session.execute(text(
                    "DELETE FROM invoice_lines WHERE invoice_id=:i"), {"i": inv})
                uow.session.execute(text(
                    "DELETE FROM stock_movements WHERE reference_type='Invoice' "
                    "AND reference_id=:i"), {"i": inv})
            for je in je_ids:
                uow.session.execute(text(
                    "DELETE FROM ledger_entries WHERE CAST(journal_entry_id AS TEXT)=:j"),
                    {"j": je})
                uow.session.execute(text(
                    "DELETE FROM reconciliations WHERE CAST(journal_entry_id AS TEXT)=:j"),
                    {"j": je})
                uow.session.execute(text(
                    "DELETE FROM journal_lines WHERE CAST(journal_entry_id AS TEXT)=:j"),
                    {"j": je})
                uow.session.execute(text(
                    "UPDATE journal_entries SET reversed_entry_id=NULL, "
                    "reverses_entry_id=NULL WHERE CAST(id AS TEXT)=:j"), {"j": je})
            for je in je_ids:
                uow.session.execute(text(
                    "DELETE FROM journal_entries WHERE CAST(id AS TEXT)=:j"), {"j": je})
            for inv in invoice_ids:
                uow.session.execute(text(
                    "DELETE FROM invoices WHERE CAST(id AS TEXT)=:i"), {"i": inv})

            for did in CLEANUP["deliveries"]:
                uow.session.execute(text(
                    "DELETE FROM delivery_items WHERE delivery_id=:d"), {"d": did})
                uow.session.execute(text(
                    "DELETE FROM delivery_notes WHERE id=:d"), {"d": did})
            for oid in CLEANUP["orders"]:
                uow.session.execute(text(
                    "DELETE FROM invoice_deliveries WHERE order_id=:o"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM sales_shipping_items WHERE shipping_id IN "
                    "(SELECT id FROM sales_shipping WHERE order_id=:o)"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM sales_shipping WHERE order_id=:o"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM sales_picking_items WHERE picking_list_id IN "
                    "(SELECT id FROM sales_picking_lists WHERE order_id=:o)"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM sales_picking_lists WHERE order_id=:o"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM order_items WHERE order_id=:o"), {"o": oid})
                uow.session.execute(text(
                    "DELETE FROM sales_orders WHERE id=:o"), {"o": oid})
            for pid in CLEANUP["products"]:
                uow.session.execute(text(
                    "DELETE FROM stock_movements WHERE CAST(entity_id AS TEXT)=:p"),
                    {"p": pid})
                uow.session.execute(text("DELETE FROM products WHERE id=:p"), {"p": pid})
            uow.session.execute(text(
                "DELETE FROM settings WHERE key='auto_invoice_on_delivery'"))
            uow.commit()
        print("CLEANUP_DONE")
    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    sys.exit(main())
