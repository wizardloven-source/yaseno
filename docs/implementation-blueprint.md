# YAseen ERP — Implementation Blueprint: 13 Missing Feature Sets

**Scope:** Advanced Sales Cycle, POS, Expense Management, Budgeting & Control, Manufacturing (MRP), HR, Project Accounting, E-commerce & Portals, DMS/OCR, Advanced Data Interop, Multi-Company & Consolidation, Advanced CRM, Executive Dashboard.

**Grounded in the actual codebase (verified):** the current architecture is:

- **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL + Pydantic v2, CQRS (`CommandBus`/`QueryBus`), DDD layering (`core/domain` → `core/application` → `core/infrastructure`), DI container (`core/bootstrap/container.py`), per-module registration in `core/bootstrap/modules/*.py` via the `Module` base class (`name`, `dependencies`, `register()`, `configure()`).
- **Events:** domain events per module (`core/domain/*/events.py`), dispatched through `core/infrastructure/bus/in_memory_event_bus.py`; handlers resolved in fresh scopes via `lazy_event_handler(container, handler_name)`.
- **Accounting core:** `AccountingOrchestrator` (`core/application/accounting/orchestrator.py`) is the single source of truth for building journal entries (`JournalEntryRequest` carries `entity_type` / `entity_id` for source traceability); `PostingEngine` (`core/domain/accounting/posting_engine.py`) validates balance per currency, fiscal periods, optimistic locking, UoW, and reversal.
- **RBAC:** `PermissionManager` / `UserContext.has_permission` / `@require_permission` in `core/application/security/authorization.py`; permissions loaded from DB (roles/permissions tables) via `get_user_permissions_from_db`.
- **Existing modules:** accounting, invoicing, inventory, purchasing, payments, funds, customers, suppliers, products, sites (branches), centers (cost/profit), tax, fiscal (periods), currency, workflow, fixed_assets, financial_statements, notifications, reports, settings, reconciliation, security, sales_cycle (partial), sales.
- **Sales cycle (PARTIAL, existing):** `core/domain/sales_cycle/`, `core/infrastructure/sales_cycle/models.py` (tables `sales_quotations`, `quotation_items`, `sales_orders`, `order_items`, `delivery_notes`, `delivery_items`), `api_routers/sales_cycle/` (quotations/orders/deliveries routers). Events exist (`QuotationConvertedEvent`, `OrderConfirmedEvent`, `DeliveryCompletedEvent`, ...). No shipping entity; delivery already has `carrier`, `driver_*`, `vehicle_*` columns.
- **Frontend:** Flutter (Provider, dio, go_router, `shared_preferences` + `flutter_secure_storage`, fl_chart + syncfusion charts, data_table_2, pdf/printing, excel, decimal, uuid). Offline storage is NOT yet implemented (no SQLite/IndexedDB layer) — this matters for POS. An import engine exists at `frontend/lib/services/import/excel_import_engine.dart`.
- **Multi-company:** no `companies` table yet; `company_id` exists only as an unconstrained `String(36)` column in the sales-cycle tables.

---

# Table of Contents

1. [Global Integration Conventions](#1-global-integration-conventions)
2. [Inter-Dependency Analysis & Delivery Order](#2-inter-dependency-analysis--delivery-order)
3. [Module Blueprints](#3-module-blueprints)
   - M3.1 Advanced Sales Cycle
   - M3.2 Point of Sale (POS)
   - M3.3 Expense Management
   - M3.4 Budgeting & Control
   - M3.5 Manufacturing (MRP)
   - M3.6 Human Resources (HR)
   - M3.7 Project Accounting
   - M3.8 E-commerce & Portals
   - M3.9 Document Management (DMS/OCR)
   - M3.10 Advanced Data Interop
   - M3.11 Multi-Company & Consolidation
   - M3.12 Advanced CRM
   - M3.13 Executive Dashboard
4. [Cross-Cutting Security Model](#4-cross-cutting-security-model)
5. [Hardened Phase Plan](#5-hardened-phase-plan)

---

# 1. Global Integration Conventions

These rules apply to **every** module below. Follow them or the module will corrupt the core accounting engine.

### G1 — All financial movements must pass through `AccountingOrchestrator`
No module writes `JournalEntry` or ledger rows directly. Every module builds a `JournalEntryRequest` and calls `AccountingOrchestrator.create_from_request(...)` → `PostingEngine.post(...)` (balanced check, fiscal-period validation, UoW, optimistic locking, per-currency balance). All free-form entry handling stays in `accounting`.

### G2 — Source traceability
`JournalEntryRequest(entity_type=<module.document>, entity_id=<doc.uuid>)` must be set on **every** auto-generated entry. This is what makes Invoice → Journal → GL drill-downs possible. `PostingValidator` should reject requests with missing `entity_type`/`entity_id`.

### G3 — Idempotency on every event-driven posting
Events can be re-delivered (offline sync retries, bus replays). Each new posting pipeline must carry an `idempotency_key` (e.g. `f"{entity_type}:{entity_id}:{action}"`), stored on the derived document (e.g. `gl_posting_status` JSON column, or a dedicated `posting_log` table). If the key exists → skip. Without this, one offline POS session can double-post GL.

### G4 — Decimal discipline
`Numeric(18,2)` at rest, `Decimal` in domain code, never `float` for money, `round(mode=ROUND_HALF_UP)` at system boundaries.

### G5 — Transactions: one UoW per business operation
Even if a module uses its own handlers, the command must join the existing `uow` (injected as `"uow"` in the container) so inventory movement + journal posting + document status change commit atomically or roll back together.

### G6 — Modular enable/disable per tenant
Each new feature = one bootstrap `Module` (e.g. `core/bootstrap/modules/pos.py`) with `name`, `dependencies`, and registration gated by the existing **MODULE SETTINGS** toggle (documented in `design_doc.txt` §36.7). When disabled: no routers, no scheduled jobs, no menu entries. Permissions for a disabled module resolve to `False`.

### G7 — Company scoping (anticipate Multi-Company)
Even before M3.11 ships, all **new** tables must include `company_id = Column(String(36), nullable=False, index=True)` and all **new** queries must filter by it. Existing loose `company_id` columns in sales-cycle tables get a real FK in M3.11 Phase 1.

### G8 — Event naming convention
Events keep a dotted name via `get_event_name()`: `"pos.receipt.created"`, `"manufacturing.work_order.completed"`, etc. Registered listeners follow `"on_<event>_<action>"` patterns in the module's `configure()`.

---

# 2. Inter-Dependency Analysis & Delivery Order

## 2.1 Dependency graph

```
                          ┌──────────────────────────┐
                          │ Core: accounting, fiscal, │
                          │ GL posting (Orchestrator + │
                          │ PostingEngine), RBAC, UoW  │
                          └────────────┬───────────────┘
        ┌───────────┬────────────┬─────┴────┬──────────────┬──────────────┐
        │           │            │          │              │              │
   Advanced    Budgeting    Expenses     Project       HR/Payroll    Multi-Company
   Sales Cycle  & Control   Management   Accounting     (needs       (touches
        │       (needs GL     (needs     (needs GL,     GL, funds,     ALL tables;
        │        actuals,     GL, funds,  inventory,     users)        company_id
        │        fiscal,      payments,   timesheets                 everywhere)
        │        centers)     workflow,      │                             │
        │                     DMS/OCR)       └── WIP from Manufacturing    │
        │                          │                                      │
   ┌────┴─────────┐   ┌────────────┴──────────┐                            │
   │  POS         │   │  Manufacturing (MRP)   │                            │
   │ (needs sales,│   │ (needs products,        │                            │
   │  inventory,  │   │  inventory, purchasing, │                            │
   │  products,   │   │  accounting for WIP)    │                            │
   │  funds)      │   └────────────┬────────────┘                            │
   └────┬─────────┘                │                                          │
        │                          │                                          │
   ┌────┴───────────┐   ┌──────────┴───────────┐                               │
   │ E-commerce     │   │ Advanced CRM           │                             │
   │ (needs products│   │ (needs customers,      │                             │
   │  customers,    │   │  sales, users,         │                             │
   │  orders,       │   │  notifications)        │                             │
   │  inventory)    │   └──────────┬─────────────┘                             │
   └────┬───────────┘              │                                            │
        │                          │                                            │
   ┌────┴──────────────────────────┴───────────────┐                            │
   │  Executive Dashboard (consumes KPIs from ALL modules + reports)           │
   └───────────────┬────────────────────────────────┘                          │
                   │                                                           │
      Advanced Data Interop (import/export/GraphQL over ALL read/write APIs)   │
                   │                                                           │
      Documents & OCR (cross-cutting: attaches to inv, purch, exp, pay, JE)    │
```

## 2.2 Delivery order (highest business value first, respects the DAG)

| # | Module | Rationale (value + dependency readiness) |
|---|--------|-----------------------------------------|
| 1 | **Advanced Sales Cycle** | Completes an existing partial module; closes the cash cycle (quote→order→deliver→ship→invoice). Immediate revenue impact, lowest cost. |
| 2 | **POS** | Direct extension of sales cycle + inventory + funds; high daily-use frequency, big UX win. Unlocks offline-first infrastructure reused by the whole app. |
| 3 | **Expense Management** | Cost-control; rides existing GL, funds, payments, workflow, notifications. High document volume. |
| 4 | **Budgeting & Control** | Pure GL-actual anchor (already exists); compliance value; zero new infra. |
| 5 | **Advanced CRM** | Revenue growth; depends only on customers + sales + users (all exist). |
| 6 | **Project Accounting** | High value for services/construction; needs only GL + inventory + a minimal labor-cost source (can read HR timesheets via a narrow interface before full HR ships). |
| 7 | **Manufacturing (MRP)** | Production value; needs products, inventory (batches/movements), purchasing, accounting. |
| 8 | **HR & Payroll** | Large scope; needs GL + funds + users + workflow. Payroll runs "after" most financial modules so payrun posting is well tested. |
| 9 | **DMS & OCR** | Cross-cutting accelerator; pairs with Expense + Purchasing (receipt/invoice OCR); ship after #3 to consume its attachment points. |
| 10 | **E-commerce & Portals** | Needs products/customers/orders/inventory; extends sales; lower urgency than CRM. |
| 11 | **Advanced Data Interop** | Platform capability; bulk-import stubs can start in the first phase (Products/Customers) and grow. |
| 12 | **Executive Dashboard** | Consumes KPIs from everything; build the widget framework early but finish last. |
| 13 | **Multi-Company & Consolidation** | Cross-cutting: the `companies` table + `company_id` FKs are a **Phase-1 schema migration** (G7), but the elimination/consolidation engine is delivered last, when group statements can be validated against real multi-company data. |

---

# 3. Module Blueprints

---

## M3.1 Advanced Sales Cycle (Quotation → Order → Picking → Shipping → Invoice)

*Status: quotations, orders, delivery notes already exist. This module completes the chain and adds Shipping + invoice linkage + inventory reservation.*

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/sales_cycle/shipping.py` (aggregate + events), `core/application/sales_cycle/shipping_service.py`, `core/infrastructure/sales_cycle/models.py` (add models), `api_routers/sales_cycle/shipping_router.py`.
- Extend existing: `core/application/sales_cycle/service.py`, `orders_router.py`, `deliveries_router.py`.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `sales_shipping` | `id`, `shipping_number`, `delivery_id`, `shipping_status` (draft/packed/shipped/delivered/failed), `carrier`, `tracking_number`, `shipped_at`, `estimated_arrival`, `cost_amount`, `warehouse_id`, `branch_id`, `company_id` | `delivery_id → delivery_notes.id`, `warehouse_id → warehouses.id` (or `stock_locations`), `company_id → companies.id` |
| `sales_shipping_items` | `id`, `shipping_id`, `item_id`, `packed_qty`, `shipped_qty` | `shipping_id → sales_shipping.id`, `item_id → delivery_items.id` |
| `sales_picking_lists` | `id`, `picking_number`, `order_id`, `status` (pending/picking/packed), `warehouse_id`, `picked_by` | `order_id → sales_orders.id` |
| `sales_picking_items` | `id`, `picking_list_id`, `order_item_id`, `requested_qty`, `picked_qty` | `picking_list_id → sales_picking_lists.id`, `order_item_id → order_items.id` |
| `invoice_deliveries` (link table) | `id`, `invoice_id`, `delivery_id` | `invoice_id → invoices.id`, `delivery_id → delivery_notes.id` |

**Existing table additions**
- `sales_orders`: add `reservation_status` enum column, `invoice_ids` (JSON, cached), `fully_delivered` bool.
- `order_items`: add `reserved_qty`, `picked_qty`, `delivered_qty`, `invoiced_qty`.

**Event-driven hooks (all already-defined events reused + new ones)**
- `OrderConfirmedEvent` → `ReserveInventoryHandler` (decrement **available**, increment **reserved**; uses `core/application/inventory/services.py` reservation API) → raise `StockReservationCreated`.
- `OrderConfirmedEvent` → `CreatePickingListHandler` (one picking list per warehouse).
- `DeliveryCompletedEvent` → `ReleaseReservationHandler` (move reserved→sold), → `CreateInvoiceDraftHandler` (generate draft invoice from delivery when `auto_invoice_on_delivery` setting is on).
- `ShippingItemShipped` → `InventoryDispatchHandler` (stock movement `sale` against the warehouse).
- Invoice posted (existing `PostInvoiceCommand`) → mark `order_items.invoiced_qty`; when all invoiced → `OrderCompletedEvent`.
- On **order cancel**: `OrderCancelledEvent` → `ReleaseReservationHandler` (restore available).

### 2) Core Logic & Algorithms

- **Reservation algorithm:** `ReservationService.reserve(order)` — for each `order_item`: `available = on_hand - reserved`; if `available < requested` → throw `InsufficientStockError` (return requested vs available, per the Arabic error convention in `design_doc.txt` §50); else increment reserved. All inside one UoW.
- **Partial delivery matrix:** each order item tracks `requested / reserved / picked / delivered / invoiced`. Statuses on the order: `partially_delivered` when `sum(delivered_qty) < sum(requested_qty)`.
- **Shipping cost allocation:** `cost_amount` is either flat-per-shipping or per-item (weight/volume); expose as a field that flows into the invoice as a non-taxable line.
- **Invoice linkage rule:** an invoice line's `quantity_invoiced` cannot exceed `delivered_qty` unless the `can_invoice_undelivered` setting is enabled and the user holds `can_invoice_undelivered` permission. Prevent double-billing via `invoice_deliveries`.
- **GL posting:** the existing invoice posting path already generates the Sales / COGS / AR entries. This module only adds the *timing* guarantee: invoice is created from a completed delivery so COGS is always costed by existing FIFO/batch valuation.

### 3) Security & Permissions (RBAC)

New permission codes (seeded via `security` module):
- `sales_cycle.quote_convert`, `sales_cycle.order_confirm`, `sales_cycle.order_cancel`
- `sales_cycle.picking_create`, `sales_cycle.picking_pick`, `sales_cycle.picking_pack`
- `sales_cycle.shipping_create`, `sales_cycle.shipping_mark_delivered`, `sales_cycle.shipping_edit_cost`
- `sales_cycle.invoice_link_undelivered` (overrides the undelivered rule above)

New roles: `order_planner` (view/confirm orders, create picking), `shipping_clerk` (pack/ship/deliver). Both are read-only over accounting.

### 4) UI/UX Implementation Strategy

- **Quote → Order landing:** "Convert" action on quotation detail (existing lifecycle buttons). Confirm dialog explains consequences (creates order, triggers reservation).
- **Picking screen (warehouse):** `data_table_2` grid grouped by warehouse; inline quantity editor for `picked_qty`; batch/serial picker per row (reuses existing StockBatch picker widget); `Flutter Beep` not required — visual progress := packed/total.
- **Shipping board:** card list or kanban-ish column by status; each card shows carrier/tracking/ETA; quick status transitions with required fields (tracking number on ship).
- **Invoice linkage tab** on delivery detail: lists generated invoices and outstanding quantity. State: Provider `OrderProvider` + `ShippingProvider`; derive `syncedQuantities` from server DTO (no client-side arithmetic for money).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — `sales_shipping*`, `sales_picking*`, `invoice_deliveries`, order/order_items columns; seed new permissions/roles.
- **Phase 2:** Backend — `ReservationService` + handlers (`OrderConfirmedEvent` → reserve → picking list), shipping service + router, delivery→invoice factory. All handlers registered in the bootstrap `sales_cycle` module wiring.
- **Phase 3:** Frontend — picking grid, shipping board, invoice-linkage tab, order lifecycle actions.
- **Phase 4:** Integration tests — `test_sales_cycle.py`: confirm order → assert reserved>0; deliver → assert draft invoice; post invoice → assert GL balanced + inventory movement exists; cancel → assert reservation released.

---

## M3.2 Point of Sale (POS)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/pos/` (`entities.py`, `events.py`, `value_objects.py`), `core/application/pos/` (session, cart, tender, sync), `core/infrastructure/pos/models.py`, `api_routers/pos/` (`sessions_router.py`, `receipts_router.py`, `sync_router.py`), `core/bootstrap/modules/pos.py`.
- Frontend: `frontend/lib/presentation/screens/pos/` (cart screen, session screen, tender screen, "held orders" screen), `frontend/lib/services/pos/` (offline queue, sync service).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `pos_sessions` | `id`, `session_number`, `user_id`, `terminal_id`, `opened_at`, `closed_at`, `opening_cash`, `closing_cash`, `expected_cash`, `status` (open/closed/voided) | `user_id → users.id`, `branch_id → sites.id`, `company_id → companies.id` |
| `pos_receipts` | `id`, `receipt_number`, `session_id`, `customer_id`, `tender_type` (cash/card/credit/mixed), `line_items` (JSON), `totals` (JSON), `status` (draft/completed/returned/queued_sync), `idempotency_key unique`, `server_offset_ms`, `synced_at` | `session_id → pos_sessions.id`, `customer_id → customers.id` |
| `pos_terminals` | `id`, `device_id`, `terminal_name`, `default_warehouse_id`, `last_seen_at` | `default_warehouse_id → warehouses.id` |
| `pos_returns` | `id`, `receipt_id`, `qty_returned`, `reason`, `refund_tender` | `receipt_id → pos_receipts.id` |
| `sync_operations` | `id`, `device_id`, `entity`, `entity_id`, `operation`, `payload` (JSON), `status` (pending/syncing/synced/failed/conflict), `retry_count`, `last_error`, `created_at`, `server_processed_at` | — (cross-entity outbox, `company_id` col) |

**Event-driven hooks**
- `PosReceiptCompleted` → `CreateInvoiceHandler` (reuse invoicing; posts through AccountingOrchestrator) → `InventorySaleHandler` (stock movement) → `PaymentReceivedHandler` (funds).
- `PosSessionClosed` → `CashCountMismatchHandler` (notify supervisor if `|closing - expected| > tolerance`).
- `PosReceiptReturned` → `ReversePostingHandler` (existing `PostingEngine.reverse` path via orchestrator) + inventory in.
- `SyncConflictDetected` → `ConflictNotificationHandler`.

### 2) Core Logic & Algorithms

- **Offline-first, not offline-only.** The client is a Flutter terminal: the cart, tender, and receipt creation run 100% local. Payments post to the server through a FIFO outbox (`sync_operations`), and POS-derived GL is generated **server-side only** (client never builds journal entries).
- **Local storage strategy (equivalent of IndexedDB in Flutter):** use `drift` (SQLite) for the POS schema (carts, held orders, receipts, sync queue, product snapshot cache) + `flutter_secure_storage` for the TLS/API token. `shared_preferences` is insufficient (no relational querying). Product/customer price data is mirrored via a light snapshot table refreshed at session open.
- **Sync protocol & conflict resolution:**
  1. Every receipt carries a client-generated `idempotency_key` (`"{device_id}:{receipt_uuid}"`). Server upserts on that key — replay never double-posts (G3).
  2. Two-phase sync: `POST /pos/sync/receipts` → server validates → returns `receipt_id` + `journal_entry_id` → client marks receipt `synced`.
  3. Conflicts:
     - *Stock conflict* (e.g. sold more than stock): server rejects with `"conflict_stock"`, returns current `on_hand`; client marks receipt `failed` and surfaces a manual-resolve screen (sale, partial sale, or void). Resolution produces a compensating receipt (not silent deletion).
     - *Sequence conflict* (offline receipt numbers colliding): clients use client-scoped numbers (`T-A1-000123`) that are remapped server-side on sync into the global sequence — *never* renumber a posted receipt.
  4. `retry_count` with exponential backoff; after N failures the sync screen shows the failed queue rather than auto-retrying.
- **Barcode/hardware:** search by scanned EAN/UPC/SKU or product QR; use Flutter `mobile_scanner` (already anticipated in pubspec's commented `barcode_scan2`). Keyboard-wedge terminals are supported by feeding scans into the same `addByBarcode(productCode)` entry point. No GL knowledge in the UI (per product philosophy).

### 3) Security & Permissions (RBAC)

New permissions:
- `pos.open_session`, `pos.close_session`, `pos.sell`, `pos.credit_sale`, `pos.apply_discount` (above standard), `pos.return`, `pos.void_receipt`, `pos.view_sales`, `pos.manage_holds`
- `pos.reconcile_cash` (supervisor-only, closes sessions with mismatch tolerance override)

Roles: `cashier` (already proposed in design doc) extended with `pos.*`; new `store_manager` role for session close + cash reconciliation.

POS is also the first real consumer of **scoped permissions** (`Scope: Own Branch` from design doc §34.1): a cashier can only open sessions / see revenue for their own terminal's branch.

### 4) UI/UX Implementation Strategy

- **POS shell:** single full-view layout — left: search + product grid (category tabs, barcode field always focused on desktop), right: sticky cart with line-level discount/hold; bottom: tender bar (Cash/Card/Credit/mixed) and total. State: `PosCartProvider` (single source of truth), `HoldProvider` (held carts), `SessionProvider`.
- **Tender screen:** on-screen numeric keypad with large type; cash tendering computes change instantly (`Decimal`); split tender UI.
- **Offline indicator** (reuses the global sync indicator concept from `design_doc.txt` §6.4): dot color + pending count; tapping opens the sync queue with per-item retry.
- **Mobile:** cards instead of grid; sticky "Charge" button (design doc §54).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — POS tables + `sync_operations` + permissions; add `drift` dependency + schema generation.
- **Phase 2:** Backend — receipts endpoint (idempotent post + invoice + inventory + funds orchestration in one UoW), sessions (open/close with cash reconciliation), returns (reverse), sync endpoint (batch + per-item conflict codes).
- **Phase 3:** Frontend — drift data layer, cart/tender/hold UI, outbox writer, two-phase sync client, barcode scanner.
- **Phase 4:** Integration tests — `test_pos_flow.py`: offline receipt created client-side, synced twice → exactly one invoice + one balanced GL entry + one inventory movement; conflict path raises `conflict_stock`; session close mismatch triggers notification.

---

## M3.3 Expense Management (Petty Cash, Advances, Corporate Cards, Receipt OCR)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/expenses/` (expense, advance, petty_cash, card_transaction), `core/application/expenses/`, `core/infrastructure/expenses/models.py`, `api_routers/expenses/`, `core/bootstrap/modules/expenses.py`.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `expense_requests` | `id`, `requester_id`, `category_id`, `expense_date`, `amount`, `currency`, `description`, `status` (draft/submitted/approved/rejected/posted), `payment_method`, `cost_center_id`, `project_id`, `receipt_doc_id`, `ledger_ref` | `requester_id → users.id`, `cost_center_id → cost_centers.id`, `project_id → projects.id` (M3.7) |
| `expense_approvals` | `id`, `expense_id`, `approver_id`, `decision` (approved/rejected), `comment`, `step_order` | `expense_id → expense_requests.id`, `approver_id → users.id` |
| `expense_advances` | `id`, `employee_id`, `requested_amount`, `approved_amount`, `spent_amount`, `returned_amount`, `status`, `settlement_deadline` | `employee_id → users.id` (employees in M3.6) |
| `advance_settlements` | `id`, `advance_id`, `expense_id`, `allocated_amount` | `advance_id → expense_advances.id`, `expense_id → expense_requests.id` |
| `petty_cash_funds` | `id`, `fund_name`, `custodian_id`, `impress_amount`, `current_balance` | `custodian_id → users.id` |
| `petty_cash_transactions` | `id`, `fund_id`, `type` (in/out), `amount`, `expense_id`, `receipt_doc_id`, `status` | `fund_id → petty_cash_funds.id` |
| `corporate_card_transactions` | `id`, `card_id`, `merchant`, `amount`, `statement_date`, `matched_expense_id`, `status` (unmatched/matched/flagged) | `matched_expense_id → expense_requests.id` |

**Event-driven hooks**
- `ExpenseApproved` → `PostExpenseEntryHandler` → `AccountingOrchestrator` (Dr: Expense account `{category.account_code}`, Cr: Petty cash / Bank / Card liability / Employee advance, depending on payment method) + `PaymentAllocationHandler` if paid via funds.
- `ExpensePosted` → if `payment_method = advance` → `AdvanceSettlementHandler` (reduce advance balance; block settlement > approved).
- `PettyCashTopUp` (`topup`) → GL entry Dr Petty Cash / Cr Bank (reuse existing funds transfer posting).
- `CardStatementMatch` (reconciliation) → `CardExpenseMatchHandler` (creates/links expense if missing; marks `matched`).

### 2) Core Logic & Algorithms

- **Approval workflow:** plug into existing `workflow` module (`core/domain/workflow`). Define workflow template `expense_approval` with conditions (e.g. `amount > 10,000 → Manager → Finance`), matching design doc §33. The workflow API stays generic; expense just registers approval steps and consumes the verdict event.
- **Advance settlement math:** `returned = approved - Σ(settlements)`; on final settlement, Dr Employee advance / Cr Cash for the unspent remainder. Validate `Σ allocations + returned ≤ approved` base currency.
- **Corporate-card matching:** match on `merchant + amount + statement_date`; auto-flag near-matches (amount ± small tolerance) for a human reconcile screen, connected to the existing `reconciliation` module.
- **Receipt scanning:** document upload triggers OCR pipeline (M3.9): Tesseract/PaddleOCR (Arabic+English) → extract merchant, date, total, tax → pre-fill expense draft (`auto_fill_confidence` stored). Human confirms; never auto-post an OCR draft.
- **GL posting rules:** every expense must deduct a mapped GL account (`expense categories` table with `account_code` FK → `accounts.code`). Batch expense uploads to the GL are always grouped per period.

### 3) Security & Permissions (RBAC)

New permissions: `expense.create`, `expense.submit`, `expense.approve`, `expense.post`, `expense.view_all`, `expense.manage_categories`, `petty_cash.manage`, `petty_cash.topup`, `card.view_matches`, `card.confirm_matches`, `expense.export`.

Roles: `expense_clerk` (create/view), `expense_approver` (approve queue), `finance_manager` (post), distinct from generic `accountant`.

Data isolation: `View All` vs `Own`: `scope = own_department` enforced server-side in service layer (list filter by requester's cost center), not in UI.

### 4) UI/UX Implementation Strategy

- **Expense screens:** list (filters: status, date, category, cost center, payment method); detail with tabs *Details / Approval History / Receipt / GL Entry*; create form uses the standard *Common Create Form* (§48) progressive disclosure: visible fields = date/category/amount/description; advanced = cost center/project/currency.
- **Receipt upload widget:** drag-and-drop image/PDF → immediate OCR preview panel (extracted fields with editable input + confidence badges); companion app photo-capture path.
- **Approval inbox:** reuse the existing workflows approval inbox; add expense-specific quick-approve cards (amount, category, requester, photo thumbnail).
- **Card matching screen:** split-pane — unmatched statement transactions vs detected expenses; highlight auto-matches; manual link drag between rows. Provider-based state: `ExpenseProvider`, `ApprovalProvider`, `MatchProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — expense/advance/petty cash/card tables, expense categories + GL mapping, permissions; seed default categories.
- **Phase 2:** Backend — expense CRUD + submit/approve/post commands (workflow integration), advance settlement service, petty-cash top-up posting, card-match service, upload endpoint (returns OCR result, stores doc reference).
- **Phase 3:** Frontend — request/receipt/approval/card-match screens + providers; NFC/photo capture for receipts.
- **Phase 4:** Integration tests — `test_expenses.py`: submit→approve→post asserts balanced GL (Dr Expense / Cr Cash), advance cap enforcement, topup GL entry, OCR failure path (no auto-post without confirmation).

---

## M3.4 Budgeting & Control

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/budgets/` (budget aggregate, budget_line, control), `core/application/budgets/`, `core/infrastructure/budgets/models.py`, `api_routers/budgets.py`, `core/bootstrap/modules/budgets.py`.
- Tight coupling: GL actuals (`core/domain/accounting` ledger queries), fiscal periods (`core/domain/fiscal`), cost/profit centers (`core/domain/centers`), sites.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `budgets` | `id`, `name`, `fiscal_year`, `period_from`, `period_to`, `currency`, `branch_id`, `cost_center_id`, `status` (draft/active/closed), `control_type` (hard/soft/none), `warning_threshold` (default .8), `approved_by`, `approved_at` | `branch_id → sites.id`, `cost_center_id → cost_centers.id` |
| `budget_lines` | `id`, `budget_id`, `account_code`, `period_amounts` (JSON per month/key), `planned_total`, `actual_total` (denormalized), | `budget_id → budgets.id`, `account_code → accounts.code` |
| `budget_movements` (audit log) | `id`, `budget_id`, `line_id`, `journal_entry_id`, `amount`, `direction`, `occurred_at` | `budget_id → budgets.id`, `journal_entry_id → journal_entries.id` |
| `budget_alerts` | `id`, `budget_id`, `line_id`, `level` (warning/exceeded), `threshold`, `actual`, `created_at`, `resolved_at` | `budget_id → budgets.id` |

**Event-driven hooks**
- **Budget enforcement is a pre-posting guard, not a post-posting listener** (must block the money). Hook into the **`AccountingOrchestrator`** `create_from_request` pipeline for posted (not draft) entries: `ValidateBudgetHook` runs after balance validation, before `PostingEngine.post`:
  - Group request lines by `account_code` (and optional `cost_center_code`).
  - For each line hitting a budgeted (account, center, period) → compute `projected = actual_to_date + line_amount`.
  - `control_type=hard` and `projected > planned` → raise `BudgetExceededError` (transaction aborts).
  - `soft` → if `projected/planned ≥ threshold` (default 80%) → raise warning event `BudgetWarningRaised` → notification (design doc §30.4); post proceeds.
- `BudgetActivated` → `BudgetBaselineHandler` (preload `actual_total` from GL ledger for lines with pre-existing activity).
- `JournalEntryPosted` (existing event) → `BudgetMovementLogger` (append `budget_movements`, update `actual_total`).
- `BudgetExceeded` → `BudgetExceededNotificationHandler` + blocking detail in API error body (Arabic message per §50).

### 2) Core Logic & Algorithms

- **Actuals computation:** never sum journal entries on read. Maintain `budget_lines.actual_total` via `BudgetMovementLogger` (event→column update) so variance queries are O(1). Rebuild from GL on activation for safety.
- **Variance analysis:** `variance = planned - actual; usage = actual/planned`. Display buckets: OK (<80%), Warning (80–100%), Exceeded (>100%) with the exact text from design doc §30.3.
- **Hard vs soft:** hard blocks posting (transaction middleware, atomic); soft posts + alert. Configuration per budget (`control_type`), not global — centers/departments may switch policy per fiscal year.
- **Period spreading:** budgets support monthly/quarterly allocation; posting guard compares against the *period bucket* (e.g. October) *and* the year-to-date cumulative, configurable.
- **Overrides:** `can_override_budget` permission lets senior finance post through a hard-block (must record `override_reason`, audited in `budget_movements`).

### 3) Security & Permissions (RBAC)

New permissions: `budget.create`, `budget.edit`, `budget.approve`, `budget.activate`, `budget.view`, `budget.override` (unlock hard block), `budget.configure_control`.

Roles: `budget_owner` (center dept head: view own + request), `budget_manager` (create/approve/activate), `finance_controller` (override, close budgets).

### 4) UI/UX Implementation Strategy

- **Budget list:** cards with usage progress bar + status chip (mirrors design doc §30.1).
- **Budget editor:** editable grid `[Account | Planned/monthly JSON | Total]` with inline validation; bulk paste helper (pairs with M3.10 Excel import); cost-center picker.
- **Budget vs Actual:** line chart (fl_chart / syncfusion) per account — grouped bars Plan vs Actual by month; variance table below. **Drill-down:** clicking a period bucket opens the underlying journal entries (GL drill, reused by M3.13).
- **Alert feed:** in-app notifications reusing `core/domain/notifications`; actionable → opens account statement.
- State: `BudgetProvider` (list + detail), `BudgetEditorState` (row edits staged, then one save command).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — budgets/budget_lines/budget_movements/budget_alerts + permissions.
- **Phase 2:** Backend — CRUD + activate (baseline rebuild), `ValidateBudgetHook` registered in the orchestrator pipeline behind a feature flag, variance service, alert service.
- **Phase 3:** Frontend — editor grid, variance chart, alert feed wiring.
- **Phase 4:** Integration tests — `test_budgets.py`: hard budget blocks a journal entry (assert `BudgetExceededError` + no ledger rows), soft budget allows with warning event, usage/variance math, override permission path.

---

## M3.5 Manufacturing (MRP) — BOMs, Work Orders, Production Planning

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/manufacturing/` (bom, work_order, production_plan, explosion), `core/application/manufacturing/`, `core/infrastructure/manufacturing/models.py`, `api_routers/manufacturing/` (`boms.py`, `work_orders.py`, `planning.py`), `core/bootstrap/modules/manufacturing.py`.
- Depends on: products, inventory (batch/movement/valuation), purchasing (replenishment suggestions), accounting (WIP/COGS).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `boms` | `id`, `product_id`, `bom_code`, `version`, `is_active`, `output_unit`, `scrap_percent`, `status`, `effective_from`, `effective_to` | `product_id → products.id` |
| `bom_lines` | `id`, `bom_id`, `component_product_id`, `quantity_per_unit` (Decimal), `waste_percent`, `unit` | `bom_id → boms.id`, `component_product_id → products.id` |
| `work_orders` | `id`, `work_order_number`, `product_id`, `bom_id`, `planned_qty`, `produced_qty`, `scrap_qty`, `status` (planned/released/in_progress/completed/cancelled), `warehouse_id`, `scheduled_start`, `scheduled_end`, `actual_start`, `actual_end`, `priority`, `company_id` | `product_id → products.id`, `bom_id → boms.id`, `warehouse_id → warehouses.id` |
| `work_order_material_issues` | `id`, `work_order_id`, `component_product_id`, `issued_qty`, `batch_number`, `unit_cost`, `issued_at`, `reversal_of` | `work_order_id → work_orders.id` |
| `work_order_outputs` | `id`, `work_order_id`, `product_id`, `produced_qty`, `batch_number`, `unit_cost`, `produced_at` | `work_order_id → work_orders.id` |
| `production_plans` | `id`, `plan_name`, `horizon_start`, `horizon_end`, `status`, `days_of_cover` | — |
| `production_plan_lines` | `id`, `plan_id`, `product_id`, `demand_qty`, `suggested_wo_qty`, `safety_stock_qty` | `plan_id → production_plans.id`, `product_id → products.id` |

**Event-driven hooks**
- `WorkOrderReleased` → `MaterialReservationHandler` (reserve components via inventory reservation API) → `BackflushProfileHandler` (configure auto-post for `completed`).
- `WorkOrderCompleted` → **single UoW**:
  1. `MaterialIssueHandler` — if "backflush on completion": issue components per BOM × output (respecting standard- or actual-qty), create `StockBatchConsumed` movements.
  2. `OutputReceiptHandler` — receive finished goods into warehouse as a new batch (`StockBatchCreated`).
  3. `WIPPostingHandler` → `AccountingOrchestrator`: Cr Raw-Material inventory / Dr WIP; then Dr WIP / Cr WIP-absorption for overheads; then on completion Dr Finished-Goods / Cr WIP at standard cost.
  4. `VariancePostingHandler` — standard vs actual cost variance → `manufacturing_variance` GL account (configurable).
- `MaterialShortageDetected` (during issue) → `PurchaseSuggestionHandler` → existing purchasing (creates PO draft), + notification.
- `ProductionPlanApproved` → `PlanExplosionHandler` (run MRP explosion, produce suggested work orders).

### 2) Core Logic & Algorithms

- **Multi-level BOM explosion (recursive):**
  ```
  explode(product, qty):
      for line in product.bom(bom_version=active):
          req = line.quantity_per_unit * qty * (1 + waste%)
          if line.component.has_active_bom:
              child_reqs += explode(component, req)     # recurse to lowest level
          else:
              net_req = req - available_consolidated(component)   # on-hand + incoming - reserved - safety
              if net_req > 0: purchase_or_wo_suggestion[component] += net_req
      return aggregate
  ```
  - Cycle detection with a DFS stack (`visited` BOM ids) → raise `BomCycleError`, prevents infinite recursion.
  - Set-based SQL (single CTE) is preferred for depth-first expansion using a `bom_closure` materialized table: `(ancestor, descendant, path[], depth)` maintained on BOM save — explosion becomes one indexed query rather than N+1 recursion for deep BOMs. This is the recommended approach for large trees; the recursive code above is the correctness reference (*explosion logic*).
- **Backflushing:** on completion, consumption automatically posts using latest cost layer (existing FIFO/batch valuation). If components run short → partial issue + material shortage event + variance accounting.
- **Production planning:** netting = demand (from sales orders/forecast) − qty on hand − planned receipts + safety stock, over the horizon; plan suggests work orders respecting BOM lead times.
- **Cost rollup:** `std_cost(product) = Σ(bom_lines.qty × component.cost) + routing/overhead`, computed at BOM save to feed WIP variance and product costing.

### 3) Security & Permissions (RBAC)

New permissions: `manufacturing.bom_view`, `manufacturing.bom_edit`, `manufacturing.bom_version`, `manufacturing.wo_create`, `manufacturing.wo_release`, `manufacturing.wo_complete`, `manufacturing.plan_view`, `manufacturing.plan_approve`, `manufacturing.variance_view`, `manufacturing.cost_override`.

Roles: `production_planner` (BOM + plans), `production_operator` (WO execution), `production_manager` (release/complete), plant controller = `accountant`-adjacent for variances.

### 4) UI/UX Implementation Strategy

- **BOM editor:** tree/grid of levels; indented table with expand/collapse per component; child-BOM drill; side panel shows rolled-up cost per level; validation chip on cycle detection. State: `BomEditorProvider` (staged nested lines, single save).
- **Work order board:** kanban columns by status (planned→released→in_progress→completed→cancelled); drag between columns = status transition with confirm dialog (design doc §49). Detail shows: BOM material list with reserved vs issued, progressive issue UI, produced output entry.
- **MRP planning screen:** exploded net-requirement grid (product, gross req, on-hand, net req, suggested action: release WO / PO draft) — bulk-select actions.
- **Variance report:** actual vs standard cost by WO; drill-down to component unit costs.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — BOM, work order, material issue/output, plan tables; `bom_closure`; permissions.
- **Phase 2:** Backend — BOM CRUD + explosion engine (CTE), plan netting, WO lifecycle, completion orchestration (inventory + WIP GL + variance in one UoW), purchasing suggestion.
- **Phase 3:** Frontend — BOM editor, WO board, planning grid, variance report.
- **Phase 4:** Integration tests — `test_manufacturing.py`: 3-level BOM explosion math (incl. waste% and cycle detection), WO complete → raw-material consumption movements + balanced WIP/finished-goods/variance GL, shortage → PO draft created.

---

## M3.6 Human Resources (HR) — Employees, Attendance, Payroll, Leave

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/hr/` (employee, attendance, leave, payroll), `core/application/hr/`, `core/infrastructure/hr/models.py`, `api_routers/hr/` (`employees.py`, `attendance.py`, `leave.py`, `payroll.py`), `core/bootstrap/modules/hr.py`.
- Depends on: users/security (employee↔user linkage), accounting (payroll GL), funds (bank transfers), workflow (leave/expense approval), notifications.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `employees` | `id`, `employee_code`, `user_id`, `department_id`, `job_title`, `hire_date`, `termination_date`, `status`, `salary_amount`, `salary_currency`, `payment_bank_account`, `cost_center_id`, `manager_id`, `company_id` | `user_id → users.id`, `cost_center_id → cost_centers.id`, `manager_id → employees.id` |
| `departments` | `id`, `name`, `cost_center_id`, `head_employee_id` | `cost_center_id → cost_centers.id` |
| `attendance_records` | `id`, `employee_id`, `work_date`, `clock_in`, `clock_out`, `status` (present/absent/late/leave/remote), `source` (device/app/manual) | `employee_id → employees.id` |
| `leave_requests` | `id`, `employee_id`, `leave_type_id`, `from_date`, `to_date`, `days` (calc), `status`, `approved_by`, `balance_snapshot` | `employee_id → employees.id`, `leave_type_id → leave_types.id` |
| `leave_types` | `id`, `code`, `name`, `days_per_year`, `carryover_limit`, `encashable`, `gl_accrual_account_code` | `gl_accrual_account_code → accounts.code` |
| `leave_balances` | `id`, `employee_id`, `leave_type_id`, `year`, `entitled`, `used`, `remaining` | composite FK (employee, leave_type) |
| `payslips` | `id`, `employee_id`, `payrun_id`, `period_start`, `period_end`, `gross`, `deductions` (JSON), `net`, `currency` | `employee_id → employees.id` |
| `payruns` | `id`, `payrun_number`, `period`, `status` (prepared/approved/posted), `total_net`, `total_debit`, `total_credit`, `journal_entry_id`, `processed_by` | `journal_entry_id → journal_entries.id` |
| `payroll_items` | `id`, `payrun_id`, `employee_id`, `component_code`, `amount`, `payable` (gross/deduction/employer) | `payrun_id → payruns.id`, `employee_id → employees.id` |
| `attendance_devices` | `id`, `device_code`, `type` (biometric/geofence/manual), `sync_endpoint`, `last_sync_at` | — |

**Event-driven hooks**
- `EmployeeCreated` → `UserProvisionHandler` (optional: create/attach system user with default role `employee`).
- `PayRunPrepared` → `PayrollValidationHandler` (net = Σ gross − Σ deductions; every payslip non-negative; totals match) → status `prepared`.
- `PayRunApproved` → `PayrollPostingHandler` (single UoW): build **one consolidated** journal entry via `AccountingOrchestrator`:
  - Dr each expense account (per department cost-center GL mapping of gross components), Dr employer-social contributions, Cr Salary-payable; then separate disbursement entry Dr Salary-payable / Cr Bank (per currency) when funds disbursement runs.
  - Lines carry `cost_center_id` = employee's department cost center → automatic budget linkage (M3.4) and project-cost linkage (M3.7, optional per timesheet).
- `LeaveApproved` → `LeaveBalanceHandler` (reserve days, enforce remaining ≥ 0) → optional `LeaveAccrualHandler` (Dr expense / Cr accrual, configurable per leave type).
- `AttendanceRosterClosed` (daily) → `AttendanceExceptionHandler` (absent/late → notifications) and `TimesheetExportHandler` (feeds M3.7 labor cost).

### 2) Core Logic & Algorithms

- **Payroll computation pipeline (per employee):**
  1. Base salary; prorated by working days in period.
  2. Variable additions (from approved expenses advances, overtime from attendance) and statutory deductions (tax/social) via a configurable rule registry — reuse `core/domain/rules` (existing `RuleEngine`).
  3. Leave encashment from `leave_balances` where `encashable`.
  4. Compute net, round to currency decimals (G4).
  5. Write `payroll_items` lines; **net zero-drift invariant** enforced at payrun level (sum of payslips = reported totals).
- **One journal entry per payrun** (not per employee) — keeps GL manageable; per-employee drill-down is by `payroll_items.payslip_id` reference in the entry memo/source.
- **Attendance:** device/webhook ingestion → normalized `attendance_records` (dedupe by (employee, work_date, clock_in) with `source` precedence: device > app > manual); late threshold config per department.
- **Leave balance wheel:** `remaining = entitled + carryover − used − pending`; pending reservations are included to block over-booking, matching design-doc workflow philosophy.
- **Employee-Cost linkage:** `employees.cost_center_id` powers GL expense routing AND enables Project Accounting labor allocation (M3.7 reads timesheets).

### 3) Security & Permissions (RBAC)

New permissions: `hr.employee_view`, `hr.employee_edit`, `hr.attendance_view`, `hr.attendance_edit`, `hr.leave_request`, `hr.leave_approve`, `hr.payslip_view_own`, `hr.payslip_view_all`, `hr.payroll_prepare`, `hr.payroll_approve`, `hr.payroll_post`, `hr.employee_self_service`.

Roles: `hr_specialist` (employee/attendance), `hr_manager` (leave approval + payroll prepare), `payroll_accountant` (post payrun to GL), `employee` (self-service: own payslips, leave requests, own attendance).

### 4) UI/UX Implementation Strategy

- **Employee directory:** list with photo/status/time filters; detail with tabs *Profile / Salary / Leave / Attendance / Payslips / Documents*.
- **Attendance view:** week/month grid heat-map (present/late/absent/leave colors); clock-in/out timer widget; manual correction dialog (permission-gated).
- **Leave screen (self-service):** balance chips per type + request form with live `days` computation respecting holidays; approval inbox reuses workflow components.
- **Payroll screen:** payrun card with gross/net/deductions summary; payslip grid editable before `prepared`; approval banner; "Post to GL" action that surfaces the generated journal entry (drill-down to lines).
- State: `EmployeeProvider`, `AttendanceProvider`, `LeaveProvider`, `PayrollProvider` (payrun staging kept immutable until prepared).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — departments, employees (with user linkage), attendance, leave (types/balances/requests), payroll (items/payslips/payruns), permissions.
- **Phase 2:** Backend — employee CRUD, attendance ingestion (device + app), leave service + workflow integration, payrun prepare/approve/post pipeline with single consolidated GL entry, payroll rule registry.
- **Phase 3:** Frontend — directory, attendance heat-map, leave self-service, payroll screen with GL drill, PDF payslip (existing `pdf`/`printing`).
- **Phase 4:** Integration tests — `test_payroll.py`: prepared payrun posts one balanced GL entry (Dr expenses sum == Cr payable/bank), leave balance cannot go negative, attendance dedupe, net = gross − deductions identity.

---

## M3.7 Project Accounting (Cost Tracking, WIP, Progress Billing)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/projects/` (project, project_cost, progress, billing), `core/application/projects/`, `core/infrastructure/projects/models.py`, `api_routers/projects.py`, `core/bootstrap/modules/projects.py`.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `projects` | `id`, `project_code`, `name`, `customer_id`, `type` (fixed_price/tandm), `contract_amount`, `currency`, `start_date`, `end_date`, `status` (draft/active/on_hold/completed/closed), `wip_gl_account`, `revenue_gl_account`, `cost_center_id`, `manager_id`, `company_id` | `customer_id → customers.id`, `cost_center_id → cost_centers.id`, `manager_id → employees.id` (M3.6) |
| `project_budgets` | `id`, `project_id`, `category`, `amount`, `type` (budget/revised) | `project_id → projects.id` |
| `project_cost_entries` | `id`, `project_id`, `source_type` (purchase/expense/payroll/inventory/misc), `source_id`, `amount`, `cost_category`, `transaction_date`, `actual_total` | `project_id → projects.id`, `source_id` polymorphic → source table uuid |
| `project_timesheets` | `id`, `project_id`, `employee_id`, `work_date`, `hours`, `hourly_rate`, `amount` | `project_id → projects.id`, `employee_id → employees.id` |
| `project_milestones` | `id`, `project_id`, `name`, `billing_percent`, `billing_amount`, `status` | `project_id → projects.id` |
| `project_progress` | `id`, `project_id`, `period`, `recognized_revenue`, `incurred_cost`, `status` (draft/approved/posted) | `project_id → projects.id` |

**Event-driven hooks**
- `PurchaseOrder` / `ExpensePosted` / `PayrollPosted` / `InventoryIssued` where `cost_center_id` or explicit `project_id` is set → `ProjectCostCaptureHandler` writes `project_cost_entries` (this is the append-only cost feed for WIP).
- `ProgressApproved` → `WIPPostingHandler` → `AccountingOrchestrator`:
  - Percentage-of-completion: Dr WIP (asset) / Cr revenue recognition, then Dr COGS / Cr WIP for incurred cost; recognized revenue = `contract_amount × completed% − previously_recognized`.
  - Completed-contract method alternates simply (revenue recognized at milestone).
- `ProgressInvoiceGenerated` → reuse invoicing to bill client (invoice linked to milestone).

### 2) Core Logic & Algorithms

- **Cost capture (labour + material):** a single polymorphic `project_cost_entries` feed aggregates:
  - labour: from HR timesheets (`project_timesheets` amount = hours × (loaded rate or salary-based rate));
  - material: from inventory issues with the `project_id` in the movement reference; purchase invoices with project department;
  - expense: expenses tagged with `project_id` (M3.3 already has the column).
  - Duplicate prevention: `(source_type, source_id)` unique on `project_cost_entries`.
- **WIP arithmetic (per period):** `WIP = Σ incurred_cost − Σ recognized_cogs`; on the GL, WIP asset balance must equal this difference — reconcile with a periodic `WIPReconciliation` job comparing ledger balance vs `project_cost_entries` (alert on mismatch).
- **Progress billing:** milestone schedule → eligible invoice amount; `billed_to_date` vs `contract_amount` cap; percentage complete = `incurred_cost / project_budget` (guard division-by-zero) or alternate progress metric configured per project.
- **Forecast/completion:** `EAC = incurred + remaining_budget`; `ETC = EAC − incurred`; profitability = contract − EAC (computed at query time in the dashboard).

### 3) Security & Permissions (RBAC)

New permissions: `project.view`, `project.create`, `project.edit`, `project.budget_edit`, `project.enter_timesheets`, `project.approve_timesheets`, `project.recognize_revenue`, `project.generate_invoice`, `project.view_costs`, `project.close`.

Roles: `project_manager` (edit, budgets, approvals), `project_accountant` (WIP/revenue recognition/posting), `consultant` (own timesheets). Data isolation: timesheet self-service only sees own rows.

### 4) UI/UX Implementation Strategy

- **Project dashboard (list → detail):** KPI header (contract, incurred, billed, recognized revenue, EAC/ETC, margin); tabs *Overview / Costs / Timesheets / Milestones / WIP / Invoices / GL*.
- **Cost breakdown tree:** cost category → source documents (purchase/expense/payroll) with drill-through, hyperlinked from `project_cost_entries`.
- **WIP screen:** period table (incurred, recognized revenue, recognized COGS, WIP delta) with "Post Period" action → shows generated journal entry.
- **Gantt-lite milestone chart** (fl_chart timeline) for billing schedule.
- State: `ProjectProvider`, `TimesheetProvider` (weekly grid entry with validation), `WipProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — projects, budgets, cost entries, timesheets, milestones, progress; add `project_id` to expenses/purchasing/inventory issue references; permissions.
- **Phase 2:** Backend — project CRUD, cost-capture listeners (purchase/expense/payroll/inventory), timesheet service, WIP post engine + reconciliation job, milestone billing → invoice.
- **Phase 3:** Frontend — project dashboard, cost tree, timesheet grid, WIP posting screen, milestone billing.
- **Phase 4:** Integration tests — `test_project_accounting.py`: post expenses+purchase+payroll tagged to project → assert `project_cost_entries` dedupe; progress post → balanced WIP GL; WIP ledger balance == computed WIP; billed caps enforced.

---

## M3.8 E-commerce & Portals (Shopify/WooCommerce connectors, Customer Portal)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/integrations/ecommerce/` (`shopify.py`, `woocommerce.py`, `channel.py`, `map_products.py`, `map_orders.py`), `api_routers/ecommerce.py` (webhook ingress + connector config), `core/application/ecommerce/` (sync service, order importer), `core/domain/ecommerce/` (channel_config, sync_run, imported_order), `api_routers/portal.py` (customer portal), `core/bootstrap/modules/ecommerce.py`, `core/bootstrap/modules/portal.py`.
- Frontend: `screens/ecommerce/` (connection config UI, sync monitor), `screens/portal/` (self-service consumer).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `channel_configs` | `id`, `channel_type` (shopify/woocommerce), `store_url`, `api_credentials_encrypted`, `currency`, `inventory_sync` (bool), `price_sync` (bool), `order_sync` (bool), `default_warehouse_id`, `status` | `default_warehouse_id → warehouses.id`, `company_id → companies.id` |
| `ecommerce_product_maps` | `id`, `channel_id`, `channel_product_id`, `product_id`, `last_price_sync_at`, `last_stock_sync_at`, `version` (optimistic lock) | `channel_id → channel_configs.id`, `product_id → products.id` |
| `imported_orders` | `id`, `channel_id`, `channel_order_id unique`, `payload` (JSON), `customer_id`, `status` (new/matched/created/error), `error` | `channel_id → channel_configs.id`, `customer_id → customers.id` |
| `portal_users` | `id`, `customer_id`, `user_id`, `status` | `customer_id → customers.id`, `user_id → users.id` |
| `sync_runs` | `id`, `channel_id`, `entity`, `started_at`, `finished_at`, `items_processed`, `items_failed`, `log` (JSON) | `channel_id → channel_configs.id` |

**Event-driven hooks**
- `ImportedOrderMatched` → `CreateSalesOrderHandler` (reuse sales cycle: create order + reservation; status created) → `WebhookAckHandler` (return channel order number to store).
- `ProductPriceChanged` (product module) → `PushPriceHandler(Channel)`.
- `StockMoved` → `PushStockHandler(Channel)` (delta sync; respects `inventory_sync` flag).
- `OrderShipped` (M3.1) → `PushFulfillmentHandler` (mark shipped + tracking in channel).
- Customer-portal actions: `PortalCreateReturnRequest` → existing `ReturnInvoiceHandler` flow.

### 2) Core Logic & Algorithms

- **Channel adapter pattern:** one `ChannelAdapter` interface (`ping / pull_products / push_inventory / push_price / pull_orders / push_fulfillment / ack`) implemented per channel; business logic lives in `EcommerceSyncService` so adding Magento/Amazon = one new adapter class, zero core changes.
- **Order import pipeline:** pull orders → normalize → **customer matching** (email/phone/tax-no against `customers`) with auto-create when `auto_create_customer` enabled → create a draft sales order per *mapped product* (unmapped SKUs land in `imported_orders.error` with SKU list) → on confirm, normal reservation flow applies.
- **Idempotent pulls:** `channel_order_id` unique; webhooks and pollers both safe (duplicate pull = no-op).
- **Rate limiting & back-off:** per-channel queue with retry caps on 429s; `sync_runs` gives observability.
- **Portal auth:** portal users authenticate via the same RBAC with role `portal_customer` and **row-level scope** (`portal_users.customer_id`) so a portal account can only see its own invoices/orders/statements — enforced server-side.
- **Portal data exposure:** read-only views of invoice list/detail, orders + tracking, customer statement, returns; actions limited to `create_return`, `download_pdf`.

### 3) Security & Permissions (RBAC)

New permissions: `ecommerce.manage_channels`, `ecommerce.run_sync`, `ecommerce.import_orders`, `ecommerce.force_reimport`, `portal.enable_for_customer`, `portal.view_invoices`, `portal.submit_return`.

Roles: `ecommerce_manager`. Credentials encrypted at rest (`AESGCM` with key from the same `.jwt_secret`/secret-store pattern already used); never returned by API (masked).

### 4) UI/UX Implementation Strategy

- **Connections screen:** list of channels with status LEDs (connected/error/last sync), OAuth/key setup forms, toggle per entity (products/price/stock/orders).
- **Sync monitor:** `sync_runs` feed with counts + error rows; manual "Sync now" + "Re-import failed orders".
- **Mapping editor:** pulls list of unmapped SKUs with inline product lookup to create `ecommerce_product_maps`.
- **Portal (consumer-facing):** simple responsive screens (dashboard, invoices with PDF, orders with tracking, returns) — separate Flutter build target with a light theme, no ERP chrome. State: `PortalProvider` (scoped to token's customer).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — channel configs, product maps, imported orders, portal users, sync runs; permissions; hidden secret-management helper.
- **Phase 2:** Backend — adapter interface + Shopify and WooCommerce adapters, sync service + scheduler, order import→sales-order pipeline, portal query/action APIs (scoped).
- **Phase 3:** Frontend — connections + mapping + monitor UI; portal app screens.
- **Phase 4:** Integration tests — `test_ecommerce.py`: mock adapter — order pull twice → one sales order (idempotent), price change → push called, portal user cannot read another customer's invoice, unmapped SKU recorded not crashed.

---

## M3.9 Document Management (DMS + OCR pipeline)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/documents/` (document, document_link, ocr_job), `core/application/documents/` (attachment service, ocr_service), `core/infrastructure/documents/models.py`, `api_routers/documents.py` (upload/download/preview + OCR webhooks), `core/bootstrap/modules/documents.py`.
- Extend existing attachments concept (`design_doc.txt` §40, formally `PLANNED`).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `documents` | `id`, `file_name`, `mime_type`, `size_bytes`, `storage_key` (object key or fs path), `checksum`, `status` (uploaded/indexed/ocr_pending/ocr_done/ocr_failed), `uploaded_by`, `company_id`, `deleted_at` | `uploaded_by → users.id` |
| `document_links` | `id`, `document_id`, `entity_type`, `entity_id`, `category` (receipt/invoice/contract/other) | `document_id → documents.id` (entity polymorphic) |
| `ocr_jobs` | `id`, `document_id`, `engine` (tesseract/paddle/vision), `status`, `extracted_json`, `confidence`, `error`, `started_at`, `finished_at` | `document_id → documents.id` |
| `document_versions` | `id`, `document_id`, `version_no`, `storage_key`, `checksum`, `created_at`, `created_by` | `document_id → documents.id` |

**Event-driven hooks**
- `DocumentUploaded` → `OcrQueuedHandler` (if file is image/PDF) → `OcrCompleted` → `ExpensePrefillHandler` (M3.3) or `SupplierInvoicePrefillHandler` (purchasing): creates a draft with extracted fields at `confidence` level.
- `DocumentLinked` → (optional) `ArchivalPolicyHandler` (apply retention).
- `ExpensePosted` (M3.3) → attach receipt link if `receipt_doc_id` set.

### 2) Core Logic & Algorithms

- **Storage abstraction:** `StorageBackend` interface with local-filesystem and S3 implementations; `storage_key` never exposed raw — API returns signed/temporary URLs for download/preview (expiry short).
- **OCR pipeline:**
  1. Preprocessor: PDF→image (`pdf2image`/poppler) or image re-scale/denoise.
  2. Engine selection: **PaddleOCR** (strong Arabic + English, used as primary) or Tesseract (`pytesseract`) fallback; optional cloud Vision/Textract adapter.
  3. Field extraction: regex + configurable templates per document type (invoice fields: number, date, supplier, total, tax). Returns `extracted_json` + per-field `confidence`.
  4. Guardrails: whenever `confidence < threshold` (default .7), prefill still shows but the draft is flagged `requires_review`; **no auto-post ever** (source of truth stays human).
- **Digital archiving:** versioning (`document_versions`), soft delete (`deleted_at`), retention policy service, checksum dedupe on upload (`checksum` unique per company).
- **Bandwidth:** chunked upload endpoint; thumbnails/previews generated server-side.

### 3) Security & Permissions (RBAC)

New permissions: `documents.upload`, `documents.view`, `documents.download`, `documents.delete`, `documents.manage_policies`, `documents.run_ocr`.

Row-level access: a document is visible only if the viewer can access its linked entity (checked via entity_type + permission of that module). Company scoping via G7.

### 4) UI/UX Implementation Strategy

- **Unified upload widget** (drop zone in Flutter `file_picker` exists; add camera capture) reused across expense/purchase/invoice screens: upload → thumbnails → link-to-entity picker.
- **Document library screen:** filter/search by entity, type, status; grid of thumbs; preview panel (PDF/image); OCR results side bar with editable fields + confidence chips.
- **OCR quality review queue:** list of low-confidence docs awaiting confirmation.
- State: `DocumentProvider` (upload progress streams), `OcrReviewProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — documents, links, versions, ocr_jobs; storage config in settings; permissions.
- **Phase 2:** Backend — upload/download/preview, link service, OCR queue (Celery/arq worker or in-process background task with DB job state), extraction templates.
- **Phase 3:** Frontend — upload widget, library, preview, OCR review.
- **Phase 4:** Integration tests — `test_dms.py`: upload → checksum dedupe, OCR job on PDF/image → field extraction fixture assert, low-confidence flagged not auto-posted, S3/local backend parity, delete = soft delete + version retained.

---

## M3.10 Advanced Data Interop (Bulk Excel import/export, REST/GraphQL)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/interop/` (mapping, batch_job), `core/application/interop/` (import_engine, validation, export_service), `api_routers/interop.py`, `api_routers/graphql.py`, `core/bootstrap/modules/interop.py`.
- Frontend: extend `services/import/` (exists: `excel_import_engine.dart`, `import_definitions.dart`).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `import_batches` | `id`, `import_type` (products/customers/suppliers/accounts/opening_balances/inventory/chart_of_accounts), `file_name`, `row_count`, `status` (uploaded/validating/validated_failed/importing/completed/failed), `mapping_json`, `summary` (JSON), `created_by` | `created_by → users.id`, `company_id → companies.id` |
| `import_errors` | `id`, `batch_id`, `row_no`, `column`, `error_code`, `message` | `batch_id → import_batches.id` |

**Event-driven hooks**
- `ImportBatchUploaded` → `ValidateBatchHandler` (synchronous validation map; produce errors; NO writes).
- `ValidateBatchPassed` → `ImportBatchHandler` (idempotent inserts under one UoW; on failure → rollback batch + write `import_errors`).
- `ImportCompleted` → `PostImportHookRegistry` (e.g. after opening balances → auto-create opening journal entry draft for accounting, and rebuild inventory valuation layers).

### 2) Core Logic & Algorithms

- **Import pipeline (never direct):** Upload → Column-Map (per-import `mapping_json`: template header → internal field) → Validate (required, types, referential integrity: `customer_id`/`account_code`/`product_sku` exists, currency valid, unique keys) → Preview (frontend grid of validated/error rows) → Confirm → Import (transactional). Exactly the flow in `design_doc.txt` §44.
- **Export:** streaming writers (`openpyxl` in a worker thread; existing `excel` Flutter package for client-side export); chunked rows (e.g. 5k/worksheet) to bound memory; include template download.
- **Idempotent imports:** natural keys (SKU, customer tax no, account code) with `upsert-or-error` policy configurable per import type; duplicates in the file are errors, not silent overwrites.
- **REST API hardening:** current routers get: pagination meta, `ETag`+`If-Match` via existing optimistic-lock versions where present, `?fields=`, bulk endpoints `POST /bulk/{entity}` (reuse import engine), and an OpenAPI-first contract.
- **GraphQL:** `strawberry-graphql` mounted on `/graphql`; thin resolver layer over the **query bus** (never direct DB); mutations limited to a curated set (create customer/supplier/product/order) wired through the **command bus** so RBAC + validation + GL rules hold. Read model via existing DTOs; `DataLoader` pattern to avoid N+1 on relational lists.

### 3) Security & Permissions (RBAC)

New permissions: `interop.import`, `interop.export`, `interop.manage_mappings`, `api.manage_tokens` (built-in API token issuance with scopes), and the existing per-entity permissions gate bulk endpoints. GraphQL must run the same token/scope auth — never a separate auth path.

Rate limiting on import + API token usage; audit entries on every import batch and API token creation (design doc §45).

### 4) UI/UX Implementation Strategy

- **Import wizard:** a stepper component (Upload → Map → Validate → Preview → Import) reusing the existing `excel_import_engine.dart`; progress bar with row counters; error panel with "jump to row".
- **Template library:** downloadable `.xlsx` templates per import type with dropdown enums, matching export columns.
- **Mapping screen:** header→field dropdown with fuzzy header suggestion; remember last mapping per import type.
- **API console:** token generation UI, scope checkboxes, OpenAPI browser link, rate-limit display.
- State: `ImportProvider` (streaming job status via polling/SSE), `ExportProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — import batches/errors; token tables; permissions; `openpyxl` + `strawberry` deps.
- **Phase 2:** Backend — import engine (validate/import phases), exporters, API tokens + scopes; GraphQL mount with query-bus resolvers and command-bus mutations; bulk endpoints.
- **Phase 3:** Frontend — wizard, templates, mapping UI, API console; upgrade existing import screens to the new wizard.
- **Phase 4:** Integration tests — `test_interop.py`: invalid row blocked before any write; duplicate natural key is error; opening-balance import produces balanced opening journal draft; export round-trips (import exported file == no new errors); GraphQL mutation honors RBAC.

---

## M3.11 Multi-Company & Consolidation

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/consolidation/` (group, company, eliminations), `core/application/consolidation/`, `core/infrastructure/consolidation/models.py`, `api_routers/consolidation.py`.
- **Cross-cutting schema job (Phase 1 of this module):** add `companies` table; add `company_id` FK to every financial/inventory/master table (G7). A migration script walks existing tables, backfills `company_id` from defaults (single default company), then applies the FK constraint.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `companies` | `id`, `company_code`, `name`, `base_currency`, `fiscal_year_start`, `is_group` (bool), `parent_company_id`, `consolidation_depth` | `parent_company_id → companies.id` |
| `company_periods` | `id`, `company_id`, `fiscal_year`, `open_from`, `closed_at` | `company_id → companies.id` |
| `intercompany_accounts` | `id`, `company_id`, `counterparty_company_id`, `receivable_account`, `payable_account` (auto-created per pair) | to `accounts.code` |
| `intercompany_transactions` | `id`, `from_company`, `to_company`, `document_source`, `amount`, `fx_rate`, `created_at`, `counterpart_txn_id` | counterpart links the mirror record |
| `elimination_entries` | `id`, `group_id`, `period`, `status` (draft/posted), `component` (equity/intercompany/balances), `journal_entry_id` | `journal_entry_id → journal_entries.id` |
| `consolidation_runs` | `id`, `group_id`, `period_from`, `period_to`, `status`, `report_payload` (JSON), `errors` (JSON) | — |

**Event-driven hooks**
- `InterCompanyTransactionCreated` → `MirrorEntryHandler`: posts a structurally balanced pair (Dr IC-Receivable in A / Cr IC-Payable in B) inside **one** UoW; both legs carry `counterpart_txn_id`. Automatic FX difference handling posts to 5900-style account within each company (Per PostingEngine conventions).
- `ConsolidationRunScheduled` → `EliminationEngine`: for each intercompany $(ic)$ pair balance → generate elimination entry (Dr IC-Payable / Cr IC-Receivable) across the group ledger; equity eliminations (Dr Subsidiary investment / Cr Equity) per mapping.
- `PeriodClosed` (fiscal) → `ConsolidationGuard` (block consolidation before all member periods close).

### 2) Core Logic & Algorithms

- **Data isolation (critical):** every repository/query gains `company_id` scope injected from `UserContext` contextvars (the pattern already used for `_current_user_context_var` in `authorization.py`). Users are mapped to companies; cross-company access is explicit (role or per-user company assignment), never implicit.
- **Consolidation algorithm:**
  1. Convert each member's period totals to group base currency (per-period avg/close fx, documented choice).
  2. Sum by account code in a *consolidation ledger table* (`consolidation_runs.report_payload` + a normalized `consolidated_balances` view).
  3. Apply eliminations in order: intercompany balances → intercompany revenue/expense → equity/investment → dividend. Each elimination is a real posted entry tagged `elimination_entries` so auditors can inspect.
  4. Verify identity: consolidated Assets = Liabilities + Equity after eliminations; otherwise run fails with a detailed mismatch report.
- **IC pricing/rounding:** mirror entries must net to zero at *group* level in base currency; doc-specific fx diffs post within the source company so group eliminations still zero.

### 3) Security & Permissions (RBAC)

New permissions: `company.manage`, `company.assign_users`, `consolidation.view_member`, `consolidation.run`, `consolidation.post_eliminations`, `consolidation.view_group_reports`.

Roles: `group_finance` (consolidation only), `company_admin` (already proposed) extended with company-scope management.

This module is the testbed for the design doc's **Scope** dimension (`Module / Resource / Action / Scope`): all existing permissions become `company-scoped`.

### 4) UI/UX Implementation Strategy

- **Company switcher** in the global header (design doc §6) — scope-aware, drives every query.
- **Consolidation screen:** run wizard (period, fx method, members); result page = group Income Statement / Balance Sheet with a drill-down per member and eliminations column visible.
- **IC transactions screen:** inbound/outbound IC documents with mirror status, fx breakdown, unbalanced pair alerts.
- **Companies admin:** tree view `parent_company_id`, default accounts provisioning, member-of-group mapping. State: `CompanyProvider`, `ConsolidationProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1 (schema foundation):** `companies` + migration adding `company_id` FKs across tables; scoped query middleware; company switcher; `company.assign_users`.
- **Phase 2:** IC transactions with mirror posting + fx; account pair auto-creation; API coverage.
- **Phase 3:** Elimination engine + consolidation runs; reconciliation job (GL vs computed); UI wizard + statements.
- **Phase 4:** Integration tests — `test_consolidation.py`: IC mirror posts balanced; elimination zeroes group IC balances; consolidated balance sheet identity holds; fx diff lands in source company; company scope blocks cross-company reads.

---

## M3.12 Advanced CRM (Campaigns, Pipeline, Email Logging)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/crm/` (lead, opportunity, stage, campaign, activity), `core/application/crm/`, `core/infrastructure/crm/models.py`, `api_routers/crm.py`, `core/bootstrap/modules/crm.py`.
- Reuse: existing `customers` and `sales_cycle`; `notifications`; `users` (salespersons); `workflow` (stage approvals optional).

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `crm_leads` | `id`, `lead_code`, `contact_name`, `email`, `phone`, `source`, `score`, `status` (new/contacted/qualified/lost) | `company_id → companies.id` |
| `crm_opportunities` | `id`, `opportunity_code`, `customer_id` (nullable until convert), `lead_id`, `owner_id`, `stage_id`, `expected_amount`, `expected_close_date`, `win_probability`, `status` | `customer_id → customers.id`, `owner_id → users.id`, `stage_id → crm_stages.id` |
| `crm_stages` | `id`, `pipeline_id`, `name`, `sort_order`, `probabilities` (win prob default) | `pipeline_id → crm_pipelines.id` |
| `crm_pipelines` | `id`, `name`, `is_default`, `company_id` | — |
| `crm_campaigns` | `id`, `name`, `type` (email/sms), `audience_filter` (JSON/query), `start_date`, `end_date`, `status` (draft/running/completed) | — |
| `crm_campaign_messages` | `id`, `campaign_id`, `customer_id`, `channel`, `subject`, `body`, `status` (queued/sent/failed/opened/clicked), `opened_at`, `sent_at` | `campaign_id → crm_campaigns.id`, `customer_id → customers.id` |
| `crm_activities` | `id`, `entity_type` (lead/opportunity/customer), `entity_id`, `activity_type` (call/email/meeting/note), `details` (JSON), `performed_by`, `due_at`, `done_at` | `performed_by → users.id` |
| `crm_email_log` | `id`, `direction` (in/out), `from`, `to`, `subject`, `body` (truncated), `related_entity_type`, `related_entity_id`, `provider_id`, `thread_id` | — |

**Event-driven hooks**
- `LeadQualified` → `OpportunityCreated` (auto-fill expected amount stage 1) → `ActivityScheduled` (next follow-up).
- `OpportunityWon` → `QuotationCreatedHandler` (reuse M3.1: quote pre-filled from opportunity) → optional `CustomerCreditCheckHandler`.
- `OpportunityConverted` → link/merge customer: `customer_id` set, dedupe check by email/tax-no.
- `OpportunityLost` → `WinLossAnalysisHandler` (capture reason) + re-score pipeline.
- `CampaignMessageSent`/`Opened`/`Clicked` → engagement counters for the campaign report + notification to assigned rep.

### 2) Core Logic & Algorithms

- **Pipeline math:** `probability = stage.win_probability`; `weighted = expected_amount × probability`; totals per stage = sum(weighted). Recompute on any stage change (event-driven, cached column `crm_opportunities.weighted_amount`).
- **Lead scoring:** configurable rule set (`score = Σ weighted signals` from source, engagement count, email opens, segment) via existing `core/domain/rules` RuleEngine.
- **Email integration/logging:** provider adapter (SMTP or Microsoft Graph/Gmail API) with a unified `crm_email_log`; inbound webhooks insert logged threads and attach to the matched entity (email→customer by address match). Logged, never scraped wholesale — retention truncated body per policy.
- **Campaign audience:** audience is a stored SQL filter (JSON predicate) evaluated at send; batching with per-message status rows so resends/opens are trackable; unsubscribes honored (opt-out flag on customer).

### 3) Security & Permissions (RBAC)

New permissions: `crm.lead_view`, `crm.lead_edit`, `crm.lead_convert`, `crm.opp_view`, `crm.opp_edit`, `crm.opp_win`, `crm.campaign_create`, `crm.campaign_send`, `crm.campaign_report`, `crm.email_view`, `crm.activity_log`.

Roles: `sales_rep` (own pipeline), `sales_manager` (all stages, campaigns, reports). **Team/ownership scope:** `crm_opportunities.owner_id` limits view/update to owner + manager (server-side), matching design doc §34 Scope.

### 4) UI/UX Implementation Strategy

- **Drag-and-drop Kanban** for the pipeline — stage columns, cards with amount/probability/owner; drag updates `stage_id` → weighted recompute + activity log; designed for desktop (design doc §55) and collapses to a list on mobile.
- **Opportunity detail:** header with win/lose/quote actions; tabs *Details / Activities / Emails / Docs*.
- **Campaign builder:** audience-filter builder (chips), message composer with template variables, send-as-draft preview; report = open/click funnel per campaign.
- **Activity timeline** on customer detail (extend existing customer detail with CRM tab).
- State: `PipelineProvider` (drag state, optimistic updates with server rollback), `CampaignProvider`.

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — pipelines/stages/leads/opportunities/activities/campaigns/email_log + permissions.
- **Phase 2:** Backend — pipeline service + weighted math, lead convert, campaign service (audience eval + batching), email adapter + inbound webhook, activity feed; wire events.
- **Phase 3:** Frontend — kanban, campaign builder/report, lead/opp forms, activity timeline, email panel.
- **Phase 4:** Integration tests — `test_crm.py`: stage change updates weighted totals; convert dedupes customer; campaign send count == audience size (no double-send), unsubscribed excluded; owner-scope enforced.

---

## M3.13 Executive Dashboard (Widgets, KPIs, Drill-down)

### 1) Architectural Integration & Hierarchy

**Placement**
- New: `core/domain/dashboard/` (widget, layout, kpi_definition), `core/application/dashboard/` (registry, kpi_service), `api_routers/dashboard.py`, `core/bootstrap/modules/dashboard.py`.
- Depends on: reports/financial_statements services, inventory, funds, workflow (approvals), notifications, budgets (alerts) and module KPI endpoints from everything above.

**Database schema extensions**

| New table | Key columns | Foreign keys |
|---|---|---|
| `dashboard_widgets` | `id`, `user_id`, `widget_type`, `title`, `config` (JSON), `row`, `col`, `w`, `h`, `hidden`, `company_scope` | `user_id → users.id` |
| `kpi_definitions` | `id`, `code`, `name`, `source` (sql/endpoint), `refresh_mode` (realtime/cron/cached), `cache_ttl`, `params_schema` (JSON), `company_id` | — |
| `kpi_cache` | `id`, `kpi_id`, `scope_key`, `value` (JSON), `computed_at`, `expires_at` | `kpi_id → kpi_definitions.id` |

**Event-driven hooks**
- Generic `KpiInvalidated` events raised by module postings (e.g. `OrderConfirmed` → invalidate `sales_yesterday`, `ExpensePosted` → invalidate `expense_mtd`). The `kpi_cache` layer recomputes on demand-top-up (reads hit cache; staleness bounded by `cache_ttl` + push invalidation).
- `BudgetWarning` (M3.4) → dashboard alert card + notification (reuse existing alert feed).

### 2) Core Logic & Algorithms

- **KPI registry:** declarative `KpiDefinition`s (code, label, unit, source query/endpoint, refresh mode). Widgets reference a KPI code; the registry **validates the code exists** at save time — no arbitrary client SQL.
- **Real-time vs near-real-time:** WebSocket/SSE for high-frequency widgets (phone: `listening` → new order ticker via existing event bus); otherwise cache with `cache_ttl` (default 60s) to keep dashboards cheap.
- **Drill-down contract:** every KPI widget must return `{value, breakdown: [{key, value}], drill_target: {entity, params}}`. The UI renders `drill_target` as a deep link (e.g. dashboard KPI → GL statement; → invoice list). This is the single mechanism enabling "click a number, see the ledger".
- **Server-side aggregation:** all chart series computed server-side (never ship all raw rows to the client); client charts only render.

### 3) Security & Permissions (RBAC)

New permissions: `dashboard.view`, `dashboard.customize`, `dashboard.share`, `dashboard.manage_kpis`.

Widget data follows the user's existing permissions: renderer checks each widget's underlying KPI datasource against the user context (a cashier's dashboard never shows consolidated P&L even if the widget is present).

### 4) UI/UX Implementation Strategy

- **Customizable grid:** drag/resize/reorder widgets (desktop), saved per user (`dashboard_widgets`). Mobile: card stack (top summary pins + list, per design doc §54).
- **Widget gallery:** picker of registered KPIs with preview chart type (fl_chart / syncfusion freedom already in pubspec).
- **Top summary cards** (Sales today, Purchases today, Receivables, Payables, Cash, Inventory value) — see design doc §8.1; each is a widget with a drill target.
- **Business alerts panel** — "Needs your attention" list (design doc §8.2) driven by the notifications module.
- State: `DashboardProvider` (layout persistence), `KpiProvider` (poll/SSE hydration per widget).

### 5) Step-by-Step Implementation Roadmap

- **Phase 1:** Migrations — widget layouts, KPI definitions (seed from existing reports), kpi_cache; permissions.
- **Phase 2:** Backend — registry, kpi_service with cache+invalidation, SSE endpoint (event-bus → dashboards), drill-target metadata.
- **Phase 3:** Frontend — widget framework (drag grid, gallery, renderers for bar/line/pie/kpi cards), alert panel wiring.
- **Phase 4:** Integration tests — `test_dashboard.py`: KPI cache invalidated on OrderConfirmed; drill target opens invoice list; cashier widget lacks P&L data (RBAC); widget save validates KPI code.

---

# 4. Cross-Cutting Security Model

- **Default-deny:** new APIs ship with `require_permission` decorators from day one; module-off = permission-off (G6).
- **Server-side scoping always** (design doc §35): UI hiding is cosmetic; services re-validate `UserContext` scope (branch/company/ownership) on every query/mutation.
- **Company/tenant isolation:** `company_id` filter middleware applied at the repository layer so a module can't leak cross-company rows even with a buggy query (M3.11 Phase 1).
- **Audit:** every posting/approval/import/grant writes to the audit trail (existing audit repo) with before/after values (design doc §45).
- **Secrets:** channel API credentials and API tokens encrypted at rest; never returned by endpoints (masked).

# 5. Hardened Phase Plan

This consolidates all 13 module roadmaps into a program schedule. Each horizontal row = a release milestone.

| Sprint block | Modules/Work | Key deliverable / exit criterion |
|---|---|---|
| 0 | Foundation: `companies` migration (M3.11 Ph1), company-scoped query middleware (G7), import-batch schema + KPI schema stubs (M3.10/M3.13 Ph1), secret helper | All existing tests green with schema additions; company switcher in header |
| 1 | **M3.1 Sales Cycle completion** (picking, shipping, invoice linkage, reservation) | Order→Ship→Invoice with balanced GL + reservation invariants (`test_sales_cycle.py` green) |
| 2 | **M3.2 POS** (offline stack, sync, sessions) | Offline receipt syncs idempotently; POS GL balanced (`test_pos_flow.py` green) |
| 3 | **M3.3 Expenses** + **M3.9 DMS/OCR** core (upload + attach; OCR queue) | Expense approve→post→GL + receipt OCR prefill (`test_expenses.py`, `test_dms.py`) |
| 4 | **M3.4 Budgeting** (guard middleware in orchestrator, alerts) | Hard block aborts posting; soft posts+alerts (`test_budgets.py`) |
| 5 | **M3.12 CRM** | Kanban + campaigns + email log; weighted pipeline correct (`test_crm.py`) |
| 6 | **M3.7 Project Accounting** (labor via narrow timesheet interface) | WIP posts balanced; billed caps hold (`test_project_accounting.py`) |
| 7 | **M3.5 Manufacturing** (BOM explosion, WOs, backflush, WIP) | Multi-level BOM + WO completion GL verified (`test_manufacturing.py`) |
| 8 | **M3.6 HR & Payroll** | Payrun GL balanced; leave balance invariant (`test_payroll.py`) |
| 9 | **M3.10 Interop full** (wizard, templates, export, GraphQL) | Import→validate→preview→import; GraphQL RBAC (`test_interop.py`) |
| 10 | **M3.8 E-commerce & Portals** | Idempotent order import; portal scoping (`test_ecommerce.py`) |
| 11 | **M3.13 Dashboard** full build | Widget framework + KPIs + drill-downs (`test_dashboard.py`) |
| 12 | **M3.11 Consolidation engine** | Consolidated statements + eliminations + identity check (`test_consolidation.py`) |

**Hard rule for every sprint:** money movements only via `AccountingOrchestrator` → balanced, reversible, source-traced, idempotent, company-scoped. Data integrity over speed, always.